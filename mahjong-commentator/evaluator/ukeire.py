from collections import Counter
from evaluator.shanten import index_to_tile

from evaluator.shanten import (
    calculate_shanten_by_type,
    tile_to_index,
)




def calculate_ukeire(
    hand: list[str],
    visible_tiles: list[str] | None = None,
    open_melds: int = 0,
) -> dict:
    """
    Calculate effective draws for a 13-tile-equivalent hand.

    hand:
        Concealed tiles AFTER a discard.

    visible_tiles:
        Publicly visible tiles outside the player's concealed hand:
        discards, open melds, dora indicators, etc.

    open_melds:
        Number of completed open melds.

    Returns:
        {
            "shanten": int,
            "ukeire": int,
            "effective_tiles": {
                "3m": 3,
                "6p": 2
            }
        }
    """

    if visible_tiles is None:
        visible_tiles = []

    route_state = calculate_shanten_by_type(hand, open_melds)
    current_shanten = route_state["minimum"]

    # Count tiles known to be unavailable.
    # This includes our own hand and public visible tiles.
    known_tiles = Counter()

    for tile in hand + visible_tiles:
        known_tiles[tile_to_index(tile)] += 1

    effective_tiles = {}
    route_effective = {name: {} for name in ("regular", "chiitoitsu", "kokushi")}

    for index in range(34):

        remaining = 4 - known_tiles[index]

        if remaining <= 0:
            continue

        candidate = index_to_tile(index)

        # Simulate drawing the tile
        new_hand = hand + [candidate]

        new_state = calculate_shanten_by_type(new_hand, open_melds)
        for route in route_effective:
            before = route_state[route]
            after = new_state[route]
            if before["available"] and after["available"] and after["shanten"] < before["shanten"]:
                route_effective[route][candidate] = remaining

        if new_state["minimum"] < current_shanten:
            effective_tiles[candidate] = remaining

    return {
        "shanten": current_shanten,
        "ukeire": sum(effective_tiles.values()),
        "effective_tiles": effective_tiles,
        "shanten_by_type": route_state,
        "ukeire_by_type": {
            route: {
                "shanten": route_state[route]["shanten"],
                "available": route_state[route]["available"],
                "ukeire": sum(tiles.values()),
                "effective_tiles": tiles,
            }
            for route, tiles in route_effective.items()
        },
    }


def evaluate_discards(
    hand: list[str],
    visible_tiles: list[str] | None = None,
    open_melds: int = 0,
) -> list[dict]:
    """
    Evaluate all unique candidate discards from a
    14-tile-equivalent hand.

    Returns a list sorted by:
        1. Lower shanten
        2. Higher ukeire
    """

    if visible_tiles is None:
        visible_tiles = []

    results = []

    for discard in sorted(set(hand)):

        remaining_hand = hand.copy()
        remaining_hand.remove(discard)

        evaluation = calculate_ukeire(
            remaining_hand,
            visible_tiles=visible_tiles + [discard],
            open_melds=open_melds,
        )

        results.append({
            "discard": discard,
            **evaluation
        })

    return sorted(
        results,
        key=lambda x: (
            x["shanten"],
            -x["ukeire"]
        )
    )
