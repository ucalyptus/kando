# Kando Tutorials

Each tutorial follows the **BLUF (Bottom Line Up Front)** format:
the key takeaway is stated first, followed by supporting context and
step-by-step instructions.

## Tutorials

| # | Tutorial | You will learn |
|---|----------|----------------|
| 1 | [Your First Run](01-your-first-run.md) | Run a kit, read the output, understand what just happened |
| 2 | [The Ledger Is the Agent](02-ledger-is-the-agent.md) | Why the append-only log replaces "memory" and "state" |
| 3 | [Responders and Reactive Chains](03-responders.md) | Write a responder, subscribe to events, emit new events |
| 4 | [Branching and Diffing](04-branching-and-diffing.md) | Fork a run, explore alternatives, compare outcomes |
| 5 | [Tracing Causality](05-tracing-causality.md) | Follow any artifact back to the goal that created it |
| 6 | [Building a Kit](06-building-a-kit.md) | Package domain types, responders, and seeds into a reusable kit |
| 7 | [MCP Integration](07-mcp-integration.md) | Expose Kando as a tool server for Claude, Cursor, or any MCP host |

## Prerequisites

- Python 3.12+
- A cloned copy of this repo (`git clone https://github.com/ucalyptus/kando.git`)
- `make setup` completed (creates `.venv`)
- Docker (optional — needed for durable EventStoreDB runs)
