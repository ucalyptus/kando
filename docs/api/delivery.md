# Delivery Bus

The delivery bus lets external subscribers receive events from a run without being part of the responder chain.

## DeliveryBus

::: kando.responders.delivery.DeliveryBus
    options:
      show_source: true
      heading_level: 3

## create_delivery_responder

::: kando.responders.delivery.create_delivery_responder
    options:
      show_source: true
      heading_level: 3

---

## Usage

```python
from kando.responders.delivery import DeliveryBus, create_delivery_responder
from kando.runtime import Runtime

bus = DeliveryBus()

# Log all events
bus.subscribe(lambda e: print(f"[event] {e.type} {e.id}"), name="logger")

# Webhook on budget.exhausted only
def notify_slack(event):
    requests.post(SLACK_URL, json={"text": f"Budget exhausted: {event.data['reasons']}"})

bus.subscribe(notify_slack, name="slack-alert", pattern={"budget.exhausted"})

# Plug into the runtime
runtime = Runtime(
    ledger=store,
    responders=[*create_kit(), create_delivery_responder(bus)],
)
world = runtime.run(seed)
```

## Pattern matching

| `pattern` value | Matches |
|---|---|
| `None` or empty `frozenset()` | All event types (wildcard) |
| `frozenset({"object.created"})` | Only `object.created` events |
| `frozenset({"budget.exhausted", "branch.created"})` | Either type |

## Notes

- Callbacks fire **synchronously** during the event loop — keep them fast.
- Callbacks that raise exceptions will propagate and halt the run. Wrap in `try/except` if needed.
- The delivery responder itself emits **no new events** — it cannot create feedback loops.
- For async delivery (webhooks, queues), use `threading.Thread` inside the callback.
