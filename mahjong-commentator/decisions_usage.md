# Using `decisions.json`

The file is a JSON array. Each item is one decision and contains nested round
data such as `round.kyoku`, `round.honba`, `round.bakaze`, and `turn`.

## Selecting one decision

```python
import json

with open("data/processed/decisions.json", encoding="utf-8") as f:
    decisions = json.load(f)

matches = [d for d in decisions
           if d.get("player") == 0
           and d.get("round", {}).get("kyoku") == 1
           and d.get("round", {}).get("honba") == 1
           and d.get("turn") == 6]

decision = next(iter(matches), None)
if decision is not None:
    commentary = commentator.generate(decision)
```

Nested values can be read directly with `decision["round"]["kyoku"]` and
`decision["round"]["honba"]`; use `get()` when a field may be absent.

If multiple games are stored, also filter by `game_id` when available. A useful
logical key is `game_id + player + kyoku + honba + turn`.

## LLM workflow

Loading the complete JSON file into Python does not send the complete file to
the LLM. The intended workflow is:

```text
decisions.json → load → select one decision → build compact evidence → LLM
```

Send only the selected hand, discard evaluations, route information, and the
few alternatives needed for commentary. Do not send the complete dataset.

For route-aware evaluation, provide explicit fields such as `best_route` and
`selected_route_analysis`. The LLM should treat those fields as authoritative
and should not compare ukeire values from routes with different shanten values.

