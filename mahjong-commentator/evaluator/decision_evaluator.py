
from evaluator.ukeire import evaluate_discards
from evaluator.shanten import tile_to_index
from evaluator.blocks import analyze_blocks
from evaluator.dora import analyze_hand_dora
from evaluator.discard_options import build_discard_options
from evaluator.yaku_detector import (
    compare_yaku_analyses,
    detect_yaku_opportunities,
    detect_yaku_routes,
    normalize_yaku_context,
)
from evaluator.yaku_detector.inventory import YAKU_INVENTORY, supported_structural_yaku
from evaluator.yaku_detector.tenpai import analyze_tenpai_legality
from copy import deepcopy


YAKU_DETECTOR_VERSION = "0.5.0"

def candidate_rank(result):
    """Rank candidates using tile efficiency only."""
    return (
        result["shanten"],
        -result["ukeire"],
    )


def best_discards_by_yaku(results: list[dict]) -> dict[str, dict]:
    """Select the current-hand discard with the strongest route per yaku.

    This is distinct from a route witness's later ``draw -> discard``
    transition: every item here is a discard available in the current
    fourteen-tile hand.
    """
    feasibility_rank = {"possible": 0, "unknown": 1, "impossible": 2}
    state_rank = {"complete": 0, "yaku_tenpai": 1, "component_present": 2, "none": 3}
    measurement_rank = {"exact": 0, "lower_bound": 1, "upper_bound": 2, "heuristic": 3}
    choices: dict[str, list[tuple[tuple, dict]]] = {}
    for candidate in results:
        routes = candidate.get("yaku_analysis", {}).get("yaku", {})
        for name, route in routes.items():
            metric = route.get("shanten", {})
            value = metric.get("value")
            if (
                value is None
                or route.get("feasibility") == "impossible"
                or route.get("availability") == "dead"
            ):
                continue
            proven = route.get("ukeire", {})
            estimated = route.get("estimated_improving_draws", {})
            rank = (
                feasibility_rank.get(route.get("feasibility"), 9),
                state_rank.get(route.get("route_state", "none"), 9),
                measurement_rank.get(metric.get("measurement"), 9),
                value,
                -route.get("tenpai_quality", {}).get("tenpai_endpoint_count", 0),
                -route.get("tenpai_quality", {}).get("best_live_wait_copies", 0),
                -sum(proven.values()),
                -sum(estimated.values()),
                candidate.get("shanten", 99),
                -(candidate.get("ukeire") or 0),
                candidate.get("discard", ""),
            )
            evidence = {
                "discard": candidate.get("discard"),
                "yaku_shanten": value,
                "measurement": metric.get("measurement"),
                "route_state": route.get("route_state", "none"),
                "feasibility": route.get("feasibility"),
                "yaku_blockers": route.get("yaku_blockers", []),
                "ukeire": proven,
                "estimated_improving_draws": estimated,
                "ordinary_shanten": candidate.get("shanten"),
                "ordinary_ukeire": candidate.get("ukeire"),
                "tenpai_quality": route.get("tenpai_quality", {}),
            }
            choices.setdefault(name, []).append((rank, evidence))
    return {
        name: min(options, key=lambda item: item[0])[1]
        for name, options in choices.items()
    }


def player_discards(decision: dict) -> list[str]:
    """Read a player's river from live (int keys) or JSON (string keys)."""
    rivers = decision.get("discards_by_player", {})
    if not isinstance(rivers, dict):
        return []
    player = decision["player"]
    return rivers.get(player, rivers.get(str(player), []))


def analyze_yaku_safely(*, include_transitions=True, **context_args) -> dict:
    """Return unknown/error evidence without aborting decision evaluation."""
    try:
        context = normalize_yaku_context(**context_args)
        result = detect_yaku_opportunities(context).to_dict()
        result.update(detect_yaku_routes(
            context,
            include_transitions=include_transitions,
            max_extra_shanten=1,
        ))
        return result
    except (TypeError, ValueError) as error:
        return {
            "menzen": None,
            "input_complete": False,
            "has_established_yaku": None,
            "opportunities": {},
            "errors": [f"INVALID_YAKU_CONTEXT: {error}"],
        }


def analyze_tenpai_safely(
    *, own_discards=(), player_score=None, remaining_wall_tiles=None, **context_args
) -> dict:
    """Return explicit unknown evidence when tenpai validation cannot run."""
    try:
        context = normalize_yaku_context(**context_args)
        return analyze_tenpai_legality(
            context,
            own_discards=own_discards,
            player_score=player_score,
            remaining_wall_tiles=remaining_wall_tiles,
        )
    except (TypeError, ValueError) as error:
        return {
            "structural_tenpai": None,
            "status": "invalid_context",
            "errors": [f"INVALID_TENPAI_CONTEXT: {error}"],
        }



def evaluate_decision(decision: dict) -> dict:
    """
    Compare actual discard against candidate discards.

    Include:
    - Tile efficiency
    - Basic block structure
    - Honor tile yaku potential
    """

    hand = decision["hand"]
    visible_tiles = decision.get(
        "visible_tiles",
        decision.get("_known_public_tiles", []),
    )
    raw_open_melds = decision.get("open_melds", [])
    if isinstance(raw_open_melds, list):
        open_melds = deepcopy(raw_open_melds)
        # Structured melds are authoritative.  A stale serialized count must
        # not change shanten calculations or downstream detector context.
        open_meld_count = len(open_melds)
    else:
        # Compatibility with older processed/custom fixtures.
        open_melds = []
        open_meld_count = decision.get("open_meld_count", int(raw_open_melds))

    round_info = decision.get("round") or {}

    results = evaluate_discards(
        hand=hand,
        visible_tiles=visible_tiles,
        open_melds=open_meld_count,
    )

    current_yaku_analysis = analyze_yaku_safely(
        hand=hand,
        open_melds=raw_open_melds,
        visible_tiles=visible_tiles,
        round_info=round_info,
    )

    # Enrich each candidate with structural and yaku evidence.
    prior_own_discard_tiles = player_discards(decision)
    scores = decision.get("scores") or round_info.get("scores") or []
    player_score = (
        scores[decision["player"]]
        if isinstance(scores, list) and len(scores) > decision["player"] else None
    )
    for result in results:
        discard = result["discard"]

        remaining_hand = hand.copy()
        remaining_hand.remove(discard)

        result["blocks"] = analyze_blocks(
            hand=remaining_hand,
            open_melds=open_meld_count,
            max_results=1,
        )

        result["hand_dora"] = analyze_hand_dora(
            concealed_tiles=remaining_hand,
            melds=open_melds,
            dora_indicators=decision.get("dora_indicators", []),
        )
        result["own_discard_tiles_after_candidate"] = (
            prior_own_discard_tiles + [discard]
        )
        result["yaku_analysis"] = analyze_yaku_safely(
            hand=remaining_hand,
            open_melds=raw_open_melds,
            visible_tiles=visible_tiles + [discard],
            round_info=round_info,
            include_transitions=False,
        )
        result["tenpai_legality"] = analyze_tenpai_safely(
            hand=remaining_hand,
            open_melds=raw_open_melds,
            visible_tiles=visible_tiles + [discard],
            round_info=round_info,
            own_discards=result["own_discard_tiles_after_candidate"],
            player_score=player_score,
            remaining_wall_tiles=decision.get("remaining_wall_tiles"),
        )

    # Expensive draw-discard transition searches are needed only for the
    # current-hand discards selected by nearby yaku routes. All candidates
    # already have route distance/feasibility and zero-shanten scorer waits.
    preliminary = best_discards_by_yaku(results)
    transition_discards = {
        recommendation["discard"]
        for recommendation in preliminary.values()
        if recommendation["yaku_shanten"] - recommendation["ordinary_shanten"] <= 1
    }
    for result in results:
        if result["discard"] not in transition_discards:
            continue
        remaining_hand = hand.copy()
        remaining_hand.remove(result["discard"])
        result["yaku_analysis"] = analyze_yaku_safely(
            hand=remaining_hand,
            open_melds=raw_open_melds,
            visible_tiles=visible_tiles + [result["discard"]],
            round_info=round_info,
            include_transitions=True,
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


    best_result = min(results, key=candidate_rank)

    # Identify all candidates with equal immediate efficiency.
    equally_efficient = [
        result["discard"]
        for result in results
        if (
            result["shanten"] == best_result["shanten"]
            and result["ukeire"] == best_result["ukeire"]
        )
    ]

    yaku_comparison = {
        "actual_discard": actual_discard,
        "alternative_discard": best_result["discard"],
        "deltas": compare_yaku_analyses(
            actual_result["yaku_analysis"],
            best_result["yaku_analysis"],
        ),
    }
    yaku_discard_recommendations = best_discards_by_yaku(results)

    return {
        "schema_version": "1.4",
        "yaku_detector": {
            "version": YAKU_DETECTOR_VERSION,
            "ruleset": "riichi_4p_kuitan_aka",
            "supported_yaku": supported_structural_yaku(),
            "inventory": YAKU_INVENTORY,
            "contract": {
            "legacy_confirmed": "deprecated_union_of_component_and_yaku_tenpai",
                "route_state": ["none", "component_present", "yaku_tenpai", "complete"],
                "ukeire_kinds": [
                    "none", "estimated_metric_improvement",
                    "exact_transition", "scorer_validated",
                ],
                "ukeire_witnesses": (
                    "grouped_by_validation_discard_target_and_methods"
                ),
                "tenpai_quality": (
                    "one-draw live scorer-validated endpoints for yaku-shanten "
                    "0-1; yaku-shanten 2 remains projected"
                ),
                "processed_route_filter": (
                    "yaku_shanten - ordinary_shanten <= 1; established and "
                    "impossible blocker routes are preserved"
                ),
            },
        },
        "player": decision["player"],
        "round": round_info,
        "turn": decision["turn"],

        # Preserve game state for future commentary.
        "drawn_tile": decision["drawn_tile"],
        "preceding_action": deepcopy(decision.get("preceding_action")),
        "hand": hand.copy(),
        "visible_tiles": visible_tiles.copy(),
        "discards_by_player": deepcopy(decision.get("discards_by_player", {})),
        "own_discards": deepcopy(player_discards(decision)),
        "open_melds": open_melds,
        "open_meld_count": open_meld_count,
        "dora_indicators": decision.get(
            "dora_indicators", []
        ),
        "current_yaku_analysis": current_yaku_analysis,

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
        # Compact, pre-ranked choices for CLI/LLM consumers. Full candidate
        # evidence remains above for audit and yaku-specific commands.
        "discard_options": build_discard_options(results),
        "yaku_discard_recommendations": yaku_discard_recommendations,
        "yaku_comparison": yaku_comparison,
    }
