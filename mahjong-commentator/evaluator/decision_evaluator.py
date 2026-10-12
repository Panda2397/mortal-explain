from evaluator.ukeire import evaluate_discards
from evaluator.shanten import tile_to_index


def evaluate_decision(decision: dict) -> dict:
    """
    Compare the actual discard against all candidate discards.
    """

    results = evaluate_discards(
        hand=decision["hand"],
        visible_tiles=decision["visible_tiles"],
        open_melds=decision["open_melds"],
    )

    actual_discard = decision["actual_discard"]

    # Normalize red fives when matching the chosen discard.
    actual_index = tile_to_index(actual_discard)

    actual_result = next(
        (
            result for result in results
            if tile_to_index(result["discard"]) == actual_index
        ),
        None,
    )

    if actual_result is None:
        raise ValueError(
            f"Actual discard {actual_discard} not found in candidates"
        )

    best_result = results[0]

    return {
        "player": decision["player"],
        "turn": decision["turn"],
        "actual_discard": actual_discard,
        "actual_evaluation": actual_result,
        "best_efficiency_discard": best_result["discard"],
        "best_evaluation": best_result,
        "shanten_difference": (
            actual_result["shanten"]
            - best_result["shanten"]
        ),
        "ukeire_difference": (
            best_result["ukeire"]
            - actual_result["ukeire"]
        ),
        "all_candidates": results,
    }