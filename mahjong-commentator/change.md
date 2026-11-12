# Mahjong Commentator Change Log

## Phase 1: Shanten by winning type

Updated `evaluator/shanten.py`.

Added `calculate_shanten_by_type(hand, open_melds=0)`, which reports
shanten independently for:

- Regular hands
- Chiitoitsu (七對子)
- Kokushi (國士無雙)

The result also includes:

- `minimum`: the lowest available shanten value
- `best_routes`: every winning type tied at the minimum
- `available`: whether the route is legal for the current hand state

Chiitoitsu and Kokushi are marked unavailable when `open_melds > 0`.

The existing `calculate_shanten()` function is preserved. It now delegates
to the detailed calculation and still returns only the overall minimum, so
existing callers remain compatible.

## Phase 2: Ukeire by winning type

Updated `evaluator/ukeire.py`.

`calculate_ukeire()` still returns the existing top-level fields:

- `shanten`
- `ukeire`
- `effective_tiles`

It now also returns:

- `shanten_by_type`: the current shanten for each legal winning type
- `ukeire_by_type`: route-specific shanten, ukeire count, and effective tiles

Each simulated draw is evaluated independently for regular, Chiitoitsu, and
Kokushi routes. A tile can therefore be identified as improving one route or
multiple routes.

The top-level values remain based on the best available route, preserving the
existing discard-ranking behavior in `evaluate_discards()` and
`decision_evaluator.py`.

## Phase 3: Route-aware block analysis

Updated `evaluator/blocks.py`.

Block analysis now emits a `route` field and includes a natural Chiitoitsu
decomposition for closed hands. Regular and Chiitoitsu structures are ranked
by their own structural shanten before `max_results` is applied, so a regular
decomposition cannot hide a better seven-pairs explanation. This fixes cases
such as `44m 55m 89m 33s 55s 6s 88s`, where a regular decomposition may use
`68s` and leave one `8s` isolated while the minimum route is Chiitoitsu.

## Verification status

- `evaluator/shanten.py` and `evaluator/ukeire.py` pass Python syntax
  compilation.
- Phase 3 route-aware block analysis has been implemented.
- AST syntax validation passes for all evaluator modules. Full numerical
  execution still requires the `mahjong` Python dependency.
