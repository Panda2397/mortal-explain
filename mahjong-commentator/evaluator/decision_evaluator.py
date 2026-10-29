
from evaluator.ukeire import evaluate_discards
from evaluator.shanten import tile_to_index
from evaluator.blocks import analyze_blocks
from evaluator.yaku import analyze_honor_tile
from evaluator.dora import analyze_discard_dora

def candidate_rank(result):
    yaku = result["discarded_tile_yaku_potential"]

    # Don't use incomplete wind information as a tie-break.
    potential_han = (
        yaku["potential_han"]
        if yaku["context_complete"]
        else 0
    )

    return (
        result["shanten"],
        -result["ukeire"],
        potential_han,
    )



def evaluate_decision(decision: dict) -> dict:
    """
    Compare actual discard against candidate discards.

    Include:
    - Tile efficiency
    - Basic block structure
    - Honor tile yaku potential
    """

    hand = decision["hand"]
    visible_tiles = decision["visible_tiles"]
    open_melds = decision["open_melds"]

    round_info = decision.get("round") or {}
    bakaze = round_info["bakaze"]
    jikaze = round_info["jikaze"]

    results = evaluate_discards(
        hand=hand,
        visible_tiles=visible_tiles,
        open_melds=open_melds,
    )

    # Enrich each candidate with structural and yaku evidence.
    for result in results:
        discard = result["discard"]

        remaining_hand = hand.copy()
        remaining_hand.remove(discard)

        result["blocks"] = analyze_blocks(
            hand=remaining_hand,
            open_melds=open_melds,
            max_results=1,
        )

        result["discarded_tile_yaku_potential"] = (
            analyze_honor_tile(
                tile=discard,
                bakaze=bakaze,
                jikaze=jikaze,
            )
        )

        result["discarded_tile_dora"] = analyze_discard_dora(
        tile=discard,
        dora_indicators=decision.get("dora_indicators", []),
    )

    actual_discard = decision["actual_discard"]
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
            f"Actual discard {actual_discard} "
            "not found in candidates"
        )


    best_result = min(
        results,
        key=lambda r: (
            r["shanten"],
            -r["ukeire"],
            r["discarded_tile_yaku_potential"]["potential_yakuhai_han"],
        )
    )

    # Identify all candidates with equal immediate efficiency.
    equally_efficient = [
        result["discard"]
        for result in results
        if (
            result["shanten"] == best_result["shanten"]
            and result["ukeire"] == best_result["ukeire"]
        )
    ]

    return {
        "player": decision["player"],
        "round": round_info,
        "turn": decision["turn"],

        # Preserve game state for future commentary.
        "hand": hand.copy(),
        "visible_tiles": visible_tiles.copy(),
        "open_melds": open_melds,
        "dora_indicators": decision.get(
            "dora_indicators", []
        ),

        "actual_discard": actual_discard,
        "actual_evaluation": actual_result,

        "best_efficiency_discard": best_result["discard"],
        "best_evaluation": best_result,
        "equally_efficient_discards": equally_efficient,

        "actual_shanten_minus_alternative": (
            actual_result["shanten"]
            - best_result["shanten"]
        ),

        "actual_ukeire_minus_alternative": (
            actual_result["ukeire"]
            - best_result["ukeire"]
        ),

        "all_candidates": results,
    }
