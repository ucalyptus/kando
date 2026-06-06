# Kando

**কাণ্ড** — Bengali for *event*, *incident*, *episode*.

A production runtime for long-running agents where the event log is the
agent, not a debugging artifact. Append-only log in, projected world out,
reactive responders in between.

Kando builds on two foundational projects and combines them into a single
opinionated runtime:

- [ActiveGraph](https://github.com/yoheinakajima/activegraph) (Yohei
  Nakajima) — the event-sourced reactive graph model for agents, described
  in [arXiv:2605.21997](https://arxiv.org/abs/2605.21997). Provides the
  agent-native abstractions: projected world state, reactive responders,
  typed edges with semantic logic, fork-and-diff, causal lineage.
- [KurrentDB](https://github.com/kurrent-io/KurrentDB) (formerly
  EventStoreDB) — the event-native database. Provides the production
  substrate: native append-only streams, server-side views, persistent
  delivery, cluster consensus, and a decade of operational hardening.

Neither is modified upstream. Kando is the layer that wires the
architecture to the infrastructure.

-----

## Core Vocabulary

Kando uses its own terms. The mapping to underlying primitives is noted
once here and not repeated elsewhere.

|Kando term    |What it is                                                                                                                                                                                 |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|**Ledger**    |The append-only event log for a single agent run. One ledger per run. The source of truth. *(Backed by a KurrentDB stream.)*                                                               |
|**World**     |The live projected state: all objects, relations, and their current data. Deterministically derived from the ledger. Never stored directly — always reconstructable.                       |
|**Responder** |A function (plain, LLM-backed, or tool-calling) that subscribes to event patterns, reads the world, and emits new events back to the ledger. Responders do not call each other.            |
|**Edge logic**|Semantic behavior attached to a typed relation (`contradicts`, `depends_on`, `supports`, `blocks`). When the relation is created, its edge logic fires. Coordination without orchestration.|
|**Snapshot**  |A materialized checkpoint of the world at a ledger position. Optimization for fast startup — the ledger remains authoritative. *(Backed by a KurrentDB server-side view.)*                 |
|**Branch**    |A fork of a ledger at a specific position. The prefix before the branch point is shared (zero-copy, no re-execution). Each branch diverges independently.                                  |
|**Diff**      |A structural comparison of two worlds (typically parent vs. branch) showing which objects, relations, and responder outputs diverged.                                                      |
|**Cache**     |Content-addressed store of LLM responses keyed by normalized request hash. On replay or branch, cached responses are served instead of making new API calls.                               |
|**Kit**       |A domain bundle: object types, responders, tools, prompts, and policies packaged for a specific use case (diligence, research, planning).                                                  |
|**Trace**     |The causal chain from any event back to the originating goal. Every event records its parent event and the responder that emitted it.                                                      |
|**Budget**    |Per-run resource limits: max events, max LLM cost, max wall-clock seconds, max recursion depth. Enforced by the runtime, not by individual responders.                                     |

-----

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         Kando Runtime                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                    Agent Layer                         │  │
│  │                                                        │  │
│  │  Kits ─── Responders ─── Edge Logic ─── LLM Cache     │  │
│  │                                                        │  │
│  │  World (projected state: objects + typed relations)     │  │
│  │  Branch engine (fork, replay shared prefix, diff)      │  │
│  │  Trace engine (causal lineage queries)                 │  │
│  │  Budget enforcement (event/cost/time caps)             │  │
│  └──────────┬─────────────────────────┬───────────────────┘  │
│             │ append events           │ read events / views   │
│             ▼                         ▼                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                   Event Substrate                      │  │
│  │                                                        │  │
│  │  Ledgers:    run:{id}         (per-run event log)      │  │
│  │              branch:{id}      (forked runs)            │  │
│  │              cache:llm        (content-addressed)      │  │
│  │                                                        │  │
│  │  Views:      world-state      (live object graph)      │  │
│  │              lineage-index    (causal chain lookups)    │  │
│  │              run-metrics      (cost, timing, counts)   │  │
│  │                                                        │  │
│  │  Delivery:   responder groups (persistent, competing)  │  │
│  │  Consensus:  cluster mode (multi-node)                 │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

-----

## Design Principles

**The ledger is the agent.** There is no separate “memory,” no mutable
state store, no conversation context that outlives its events. If it
didn’t happen in the ledger, it didn’t happen.

**The world is derived, never stored.** Object data, relation graphs,
responder state — all of it is a deterministic function of the ledger.
Snapshots are a performance optimization. The ledger can always
reconstruct the world from scratch.

**Responders are physics, not control flow.** A responder subscribes
to a pattern. When the pattern matches, the responder fires. There is
no orchestrator deciding what runs next. Chaining happens because one
responder’s output event matches another responder’s subscription.
The execution order is an emergent property of the event stream.

**Edge logic carries meaning.** A `contradicts` relation is not just
data — it’s a trigger. When evidence contradicts a belief, the
contradiction-resolution responder fires automatically. Logic lives
where the semantic meaning is, not in a central router.

**Branches are cheap.** Forking a 500-event run at position 250 replays
the first 250 events from cache (zero LLM calls, sub-second) and
executes only the divergent tail. This makes hypothesis testing,
A/B comparison, and self-improvement loops economically viable.

**Traces are not observability.** The causal chain from goal to artifact
is not a debugging tool bolted on after the fact. It is the
structural output of every run, queryable at any time, and it falls
out of the architecture for free.

-----

## Event Schema

Every event in a ledger carries:

```python
@dataclass
class KandoEvent:
    id: str               # unique, monotonic within the ledger
    type: str             # e.g. "object.created", "responder.fired", "llm.response"
    source: str           # ledger identity (run:{id} or branch:{id})
    actor: str            # which responder emitted this event
    cause: list[str]      # parent event IDs — the causal chain
    timestamp: datetime   # wall-clock time of emission
    data: dict            # event-specific payload
```

Fixed event types (the verbs):

|Type                 |Emitted when                                         |
|---------------------|-----------------------------------------------------|
|`object.created`     |A new object enters the world                        |
|`object.patched`     |An existing object’s data changes                    |
|`relation.created`   |A typed edge connects two objects                    |
|`relation.removed`   |A typed edge is dissolved                            |
|`responder.fired`    |A responder begins execution                         |
|`responder.completed`|A responder finishes successfully                    |
|`responder.failed`   |A responder fails (failure is data, not an exception)|
|`llm.request`        |An LLM call is initiated                             |
|`llm.response`       |An LLM response is received (or served from cache)   |
|`tool.called`        |An external tool is invoked                          |
|`tool.returned`      |A tool returns its result                            |
|`branch.created`     |A ledger is forked at a position                     |
|`budget.exhausted`   |A run-level resource limit is hit                    |
|`kit.loaded`         |A domain kit is loaded into the runtime              |

The nouns (object types, relation types) are defined by the kit.
Kando has no opinion about what a “task” or “belief” or “claim” is —
that’s domain vocabulary. The runtime only knows events.

-----

## Determinism Contract

Responders must not:

- Call `random()` — use entropy recorded in the triggering event
- Read wall-clock time — use the event’s `timestamp`
- Generate UUIDs — obtain from the runtime’s deterministic ID generator
- Perform I/O outside Kando primitives — all external calls go through
  `tool.called` / `tool.returned` events
- Depend on mutable global state

Violations are not caught statically. They surface at replay as a
divergence: strict replay re-fires every responder and fails on the
first event that doesn’t match the original ledger. Permissive replay
reconstructs the world from events without re-firing responders.

LLM calls are inherently non-deterministic. On replay, the cache
serves the original response. On a branch past the fork point, new
LLM calls are made and cached in the branch’s scope.

-----

## Implementation Plan

### Phase 1 — Ledger (weeks 1–3)

Replace the in-process event table with a native event stream.

- Implement the `LedgerStore` interface: `append(events)`,
  `read(from_position)`, `read_all()`, `stream_name()`.
- One stream per run, named `run:{run_id}`.
- Events serialized as CloudEvents with Kando-specific extensions
  (`kando:cause`, `kando:actor`, `kando:run`).
- Optimistic concurrency via expected stream version on append.
- LLM cache as a dedicated `cache:llm` stream, keyed by request hash.
- Replay = `read(from_position=0)` + apply to empty world.

**Exit criteria:** Existing test suite passes against the new store.
Strict replay produces identical world state. Diligence kit quickstart
runs end-to-end.

-----

### Phase 2 — Snapshots (weeks 4–6)

Move world projection server-side so the world is queryable without
loading the runtime.

- Write a server-side view that consumes `run:*` streams and maintains
  a materialized world: current objects, latest patches, all relations.
- Write a lineage index view: for any event ID, return the full causal
  chain to root.
- Write a metrics view: event counts by type, cumulative LLM cost,
  wall-clock duration per responder.
- Modify `Runtime.load()` to optionally hydrate from the snapshot
  rather than replaying the full ledger. Fall back to full replay if
  the snapshot is stale.

**Exit criteria:** Snapshot-hydrated world matches replay-hydrated world
for all test runs. 10k-event run loads in < 500ms from snapshot vs.
full replay baseline.

-----

### Phase 3 — Distributed Responders (weeks 7–9)

Decouple responders from the in-process event loop.

- Each responder group subscribes to the ledger via persistent delivery.
  The substrate handles acknowledgment, retry, and parking (dead-letter).
- Competing consumers: multiple instances of the same responder
  process events in parallel for horizontal scaling.
- Responder isolation: a crash in one responder does not affect others.
  The subscription resumes from the last acknowledged position.
- Edge logic responders filter on `relation.created` events with
  specific relation types.
- Budget enforcement moves from in-process check to a dedicated
  budget responder that subscribes to all events, tracks cumulative
  usage, and emits `budget.exhausted` when limits are hit.

**Exit criteria:** Kill a responder process mid-run. Restart it. Run
completes with identical world state. Two competing consumers produce
deterministic results when partitioned by object ID.

-----

### Phase 4 — Branching (weeks 10–12)

Implement zero-copy forking on native streams.

- A branch creates a new stream `branch:{branch_id}` with a metadata
  event recording the parent ledger and fork position.
- Reading a branch: events 0 through fork position are read from the
  parent stream (shared prefix, no duplication). Events after fork
  position are read from the branch stream.
- Cache scoping: branch replays serve LLM responses from the parent’s
  cache for the shared prefix. New LLM calls after the fork point are
  cached in the branch’s scope.
- Structural diff: compare two world snapshots (parent at position N
  vs. branch at position N) and report which objects, relations, and
  responder outputs differ.
- Cost accounting: the branch metadata records the parent’s cumulative
  LLM cost at fork point. Branch cost = delta from that baseline.

**Exit criteria:** Fork a 500-event run at position 250. Shared prefix
replays in < 1 second with zero LLM calls. Diff correctly identifies
all divergent objects and relations. Cost accounting is accurate.

-----

### Phase 5 — Multi-Agent and Interface (weeks 13–16)

Enable coordination across multiple Kando runtimes and external tooling.

- **Shared world streams.** Multiple runtimes subscribe to a shared
  category stream. Runtime A’s output events are visible to Runtime B’s
  responders without explicit messaging. Coordination is implicit —
  responders react to world state changes, not to messages from other
  agents.
- **Cross-run supervision.** A supervisory responder subscribes to all
  runs in a category and detects patterns across runs (e.g., three
  runs producing contradictory claims about the same entity triggers
  a reconciliation responder).
- **MCP interface.** Expose Kando operations as MCP tools: `start_run`,
  `query_world`, `fork_run`, `diff_branches`, `explain_trace`. This
  lets external agents (Claude, GPT, etc.) interact with Kando runs
  as a tool rather than as a framework.
- **CLI.** `kando run <kit>`, `kando replay <run_id>`,
  `kando fork <run_id> --at <position>`, `kando diff <run_a> <run_b>`,
  `kando trace <event_id>`, `kando status <run_id>`.

**Exit criteria:** Two runtimes coordinate through a shared stream
without direct communication. Causal lineage is maintained across
agents. MCP tools work from Claude Code. CLI covers all core operations.

-----

## Open Questions

**1. View language mismatch.** Server-side views run JavaScript. The
world projection has domain-specific semantics (typed edges, relation
triggers) that live in Python today. Decision needed: port projection
logic to JS for server-side execution, or keep projections client-side
and use server-side views only for simple indexes (lineage, metrics).

**2. Competing consumer ordering.** If two responder instances process
events from the same run concurrently, their emission order may differ
from a single-threaded run. This could break the determinism contract.
Likely mitigation: partition delivery by object ID so a given object’s
events are always processed by the same consumer. Needs testing.

**3. Cache lifecycle.** The LLM cache stream grows without bound. Stream
truncation and max-count limits are available, but eviction must respect
active branch prefixes that reference cached responses. Need a
reference-counting or tombstone mechanism.

**4. Event versioning.** Kando’s event types will evolve. The substrate
does not have built-in event upcasting. Options: (a) client-side
upcaster middleware that transforms old events on read, (b) a
server-side view that projects old events into current schema,
(c) append-only versioning where old and new event types coexist.

**5. Cold start at scale.** A 100k-event ledger takes meaningful time
to replay from position 0. Snapshots mitigate this, but snapshot
freshness, consistency, and invalidation need design. Akka Persistence
snapshots every N events — similar cadence likely appropriate here.

**6. Python client gaps.** The Python client for the underlying event
store is less mature than the .NET and Node clients. Persistent
delivery and view management may need upstream contributions or a
thin wrapper.

-----

## Repository Structure

```
kando/
├── kando/
│   ├── runtime.py             # Core runtime: load, run, replay
│   ├── ledger/
│   │   ├── interface.py       # LedgerStore protocol
│   │   ├── memory.py          # In-memory store (testing)
│   │   └── stream.py          # Event stream backend
│   ├── world/
│   │   ├── graph.py           # World state: objects + relations
│   │   ├── projection.py      # Deterministic projection from ledger
│   │   └── snapshot.py        # Snapshot hydration + fallback
│   ├── responders/
│   │   ├── base.py            # Responder protocol + decorator
│   │   ├── edge.py            # Edge logic (relation-triggered)
│   │   ├── delivery.py        # Persistent subscriber integration
│   │   └── budget.py          # Budget enforcement responder
│   ├── branch/
│   │   ├── fork.py            # Create branch, link to parent
│   │   ├── replay.py          # Prefix-sharing replay
│   │   └── diff.py            # Structural world comparison
│   ├── cache/
│   │   └── llm.py             # Content-addressed LLM cache
│   ├── trace/
│   │   └── lineage.py         # Causal chain queries
│   ├── schema/
│   │   └── events.py          # KandoEvent dataclass + type registry
│   └── cli/
│       └── main.py            # kando run | replay | fork | diff | trace
├── kits/
│   ├── diligence/             # Reference kit (ported from ActiveGraph)
│   ├── research/              # Research & synthesis kit
│   └── README.md
├── mcp/
│   └── server.py              # MCP tool interface
├── views/
│   ├── world_state.js         # Server-side world projection
│   ├── lineage_index.js       # Causal chain index
│   └── run_metrics.js         # Cost, timing, event counts
├── tests/
│   ├── test_ledger.py         # Store parity: memory vs stream
│   ├── test_replay.py         # Strict + permissive replay
│   ├── test_branch.py         # Fork, prefix cache, diff
│   ├── test_determinism.py    # Contract violation detection
│   ├── test_crash.py          # Kill responder, verify recovery
│   └── test_multi_agent.py    # Cross-runtime coordination
├── docker-compose.yml         # Event substrate + Kando runtime
├── pyproject.toml
├── Plan.md                    # This document
├── LICENSE
└── README.md
```

-----

## References

- [ActiveGraph](https://github.com/yoheinakajima/activegraph) — event-sourced reactive graph runtime (agent abstractions)
- [“The Log is the Agent”](https://arxiv.org/abs/2605.21997) — Nakajima, May 2026 (foundational paper)
- [KurrentDB](https://github.com/kurrent-io/KurrentDB) — event-native database (production substrate)
- [ESAA](https://arxiv.org/abs/2602.23193) — Event Sourcing for Autonomous Agents, Feb 2026 (related work)
- [Log-Centric Agent Architecture](https://blog.ucalyptus.me/p/log-centric-agent-architecture) — the architectural thesis this project implements