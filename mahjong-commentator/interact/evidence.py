"""Compact, JSON-safe evidence for interactive explanations."""

from collections import Counter

from utils.tile_format import sort_hand
from evaluator.yaku_detector import compare_yaku_analyses
from evaluator.discard_options import build_discard_options


def _route_evidence(route: dict) -> dict:
    """Project one route to fields useful for explanation, not recomputation."""
    compact = {
        "shanten": route.get("shanten", {}),
        "feasibility": route.get("feasibility"),
        "route_state": route.get("route_state", "none"),
        "validation": route.get("proof", {}).get("validation"),
        "outcome_scope": route.get("outcome_scope", {}),
        "ukeire": route.get("ukeire", {}),
        "ukeire_kind": route.get("ukeire_kind", "none"),
        "estimated_improving_draws": route.get("estimated_improving_draws", {}),
        "yaku_blockers": route.get("yaku_blockers", []),
    }
    # Full witnesses remain available to Python/CLI but are deliberately not
    # placed in the default LLM prompt. Their useful result is summarized by
    # validation, outcome_scope, ukeire, and ukeire_kind above.
    return compact


def _tenpai_evidence(value: dict | None) -> dict | None:
    """Keep action-legality conclusions while removing repeated scorer detail."""
    if not isinstance(value, dict):
        return None
    result = {
        key: value[key]
        for key in (
            "structural_tenpai", "status", "permanent_furiten",
            "temporary_furiten", "open_no_yaku_tenpai",
            "closed_dama_no_yaku_tenpai", "riichi_eligibility",
        )
        if key in value
    }
    waits = value.get("waits", {})
    if isinstance(waits, dict):
        result["waits"] = {
            tile: {
                "remaining": evidence.get("remaining"),
                "ron_legal": evidence.get("ron", {}).get("legal"),
                "tsumo_legal": evidence.get("tsumo", {}).get("legal"),
            }
            for tile, evidence in waits.items()
        }
    return result


def _candidate(candidate: dict) -> dict:
    yaku_analysis = candidate.get("yaku_analysis", {})
    nearby = {
        name: _route_evidence(route)
        for name, route in yaku_analysis.get("yaku", {}).items()
        if route.get("feasibility") in {"confirmed", "possible"}
        and _is_nearby_route(candidate, route, name)
    }
    return {
        "discard": candidate.get("discard"),
        "shanten": candidate.get("shanten"),
        "ukeire": candidate.get("ukeire"),
        "effective_tiles": candidate.get("effective_tiles", {}),
        "confirmed_yaku": yaku_analysis.get("confirmed_yaku", []),
        "established_components": yaku_analysis.get("established_components", []),
        "validated_yaku_tenpai": yaku_analysis.get("yaku_tenpai", []),
        "nearby_yaku": nearby,
        "tenpai_legality": _tenpai_evidence(candidate.get("tenpai_legality")),
    }


def _is_nearby_route(candidate: dict, route: dict, name: str | None = None) -> bool:
    """A route is a practical consideration only within one extra shanten."""
    ordinary = candidate.get("shanten")
    yaku_shanten = route.get("shanten", {}).get("value")
    if name == "pinfu":
        value_honor_blockers = Counter(
            blocker.get("tile")
            for blocker in route.get("yaku_blockers", [])
            if blocker.get("reason") == "value_honor_cannot_be_pinfu_pair"
            and blocker.get("tile") is not None
        )
        if any(count >= 2 for count in value_honor_blockers.values()):
            return False
    return (
        ordinary is not None
        and yaku_shanten is not None
        and yaku_shanten - ordinary <= 1
    )


def build_turn_evidence(decision: dict, comparison_discard: str | None = None) -> dict:
    """Select current, actual and one comparison action without prompt bloat."""
    candidates = decision.get("all_candidates", [])
    comparison = None
    target = comparison_discard or decision.get("best_efficiency_discard")
    for candidate in candidates:
        if candidate.get("discard") == target:
            comparison = candidate
            break
    actual = decision.get("actual_evaluation", {})
    same_comparison = bool(
        comparison
        and comparison.get("discard") == actual.get("discard")
    )
    discard_options = decision.get("discard_options")
    if not isinstance(discard_options, list):
        # Compatibility with processed files created before schema 1.3.
        discard_options = build_discard_options(candidates)
    return {
        "round": decision.get("round", {}),
        "turn": decision.get("turn"),
        "player": decision.get("player"),
        "hand": sort_hand(decision.get("hand", [])),
        "drawn_tile": decision.get("drawn_tile"),
        "preceding_action": decision.get("preceding_action"),
        "open_melds": decision.get("open_melds", []),
        "dora_indicators": decision.get("dora_indicators", []),
        "recent_discards": {
            str(player): tiles[-6:]
            for player, tiles in decision.get("discards_by_player", {}).items()
        },
        "actual_discard": decision.get("actual_discard"),
        "actual": _candidate(actual),
        "comparison": (
            None if same_comparison else _candidate(comparison) if comparison else None
        ),
        "comparison_same_as_actual": same_comparison,
        "efficiency_best_discard": decision.get("best_efficiency_discard"),
        # Five Python-ranked choices are enough for recommendation questions;
        # the complete compact list remains in processed decision JSON.
        "discard_options": discard_options[:5],
        "yaku_changes": compare_yaku_analyses(
            actual.get("yaku_analysis", {}),
            comparison.get("yaku_analysis", {}) if comparison else {},
        ) if comparison and not same_comparison else [],
        "measurement_warning": (
            "exact values are proven by their calculator; lower_bound and "
            "heuristic values must not be described as exact"
        ),
    }


def format_turn_summary(decision: dict) -> str:
    actual = decision["actual_evaluation"]
    analysis = actual.get("yaku_analysis", {})
    actual_types = ", ".join(
        f"{tile} - {copies}"
        for tile, copies in actual.get("effective_tiles", {}).items()
    ) or "none"
    best = decision.get("best_evaluation", {})
    best_types = ", ".join(
        f"{tile} - {copies}"
        for tile, copies in best.get("effective_tiles", {}).items()
    ) or "none"
    hand = list(decision.get("hand", []))
    drawn_tile = decision.get("drawn_tile")
    if drawn_tile in hand:
        # Keep one occurrence of the latest draw out of the sorted concealed
        # tiles, then append it as the visually distinct rightmost tile.
        hand.remove(drawn_tile)
        displayed_hand = sort_hand(hand) + [drawn_tile]
    else:
        displayed_hand = sort_hand(hand)
    yaku_discards = decision.get("yaku_discard_recommendations", {})
    action = decision.get("preceding_action") or {}
    action_parts = []
    if action:
        action_text = f"{action.get('type')} {action.get('tile')}"
        if action.get("from_player") is not None:
            action_text += f" from player {action['from_player']}"
        action_parts.append(action_text)
    if drawn_tile is not None:
        action_parts.append(f"draw {drawn_tile}")
    action_parts.append(f"discard {decision['actual_discard']}")
    hand_lines = [
        f"Decision {decision['turn']} | " + " | ".join(action_parts),
        "Hand: " + " ".join(displayed_hand),
    ]
    efficiency_lines = [
        f"Efficiency: {actual['shanten']} shanten, "
        f"[{actual_types}] {actual['ukeire']} ukeire",
        f"Efficiency alternative: {decision['best_efficiency_discard']} "
        f"[{best_types}] {best.get('ukeire')} ukeire",
    ]
    open_melds = decision.get("open_melds", [])
    if open_melds:
        formatted_melds = []
        for meld in open_melds:
            meld_text = (
                f"{meld.get('type')} "
                f"[{' '.join(sort_hand(meld.get('tiles', [])))}]"
            )
            if meld.get("called_tile") is not None:
                meld_text += f" called {meld['called_tile']}"
            if meld.get("from_player") is not None:
                meld_text += f" from player {meld['from_player']}"
            if meld.get("type") == "ankan":
                meld_text += " (closed)"
            formatted_melds.append(meld_text)
        hand_lines.append("Open melds: " + "; ".join(formatted_melds))
    components = analysis.get("established_components", analysis.get("confirmed_yaku", []))
    tenpai_yaku = analysis.get("yaku_tenpai", [])
    status_lines = [
        "Established components: " + (", ".join(components) or "none"),
        "Validated yaku-tenpai: " + (", ".join(tenpai_yaku) or "none"),
    ]
    legality = actual.get("tenpai_legality", {})
    if legality.get("structural_tenpai"):
        status_lines.append(
            "Tenpai legality: "
            + ("open no-yaku" if legality.get("open_no_yaku_tenpai") else
               "closed dama no-yaku" if legality.get("closed_dama_no_yaku_tenpai") else
               "at least one validated yaku outcome")
        )

    discard_options = decision.get("discard_options")
    if not isinstance(discard_options, list):
        discard_options = build_discard_options(decision.get("all_candidates", []))
    recommendation_lines = ["Yaku recommended discard:"]
    for option in discard_options[:5]:
        yaku_parts = []
        for route in option.get("nearby_yaku", []):
            quality = route.get("tenpai_quality", {})
            quality_text = ""
            if quality.get("status") == "validated_live":
                quality_text = (
                    f", live-tenpai={quality.get('tenpai_endpoint_count', 0)}, "
                    f"best-wait={quality.get('best_wait_type_count', 0)} types/"
                    f"{quality.get('best_live_wait_copies', 0)} copies"
                )
            elif quality.get("status") == "projected":
                quality_text = ", projected"
            yaku_parts.append(
                f"{route['name']} {route['yaku_shanten']} "
                f"({route['measurement']}){quality_text}"
            )
        yaku_text = ", ".join(yaku_parts) or "none"
        effective = ", ".join(
            f"{tile} - {copies}"
            for tile, copies in option.get("effective_tiles", {}).items()
        ) or "none"
        recommendation_lines.append(
            f"  #{option.get('efficiency_rank', '?')} discard "
            f"{option.get('discard')} -> [{yaku_text}] | "
            f"{option.get('ordinary_shanten')} shanten, "
            f"[{effective}] {option.get('ordinary_ukeire')} ukeire"
        )
    routes = analysis.get("yaku", {})
    if yaku_discards:
        nearby_routes = {}
        for name, recommendation in yaku_discards.items():
            route = {
                "shanten": {
                    "value": recommendation.get("yaku_shanten"),
                    "measurement": recommendation.get("measurement"),
                },
                "feasibility": recommendation.get("feasibility"),
                "route_state": recommendation.get("route_state"),
                "yaku_blockers": recommendation.get("yaku_blockers", []),
                "estimated_improving_draws": recommendation.get(
                    "estimated_improving_draws", {}
                ),
                "tenpai_quality": recommendation.get("tenpai_quality", {}),
            }
            candidate = {"shanten": recommendation.get("ordinary_shanten")}
            if (
                route["feasibility"] in {"confirmed", "possible"}
                and _is_nearby_route(candidate, route, name)
            ):
                nearby_routes[name] = route
    else:
        nearby_routes = {
            name: route for name, route in routes.items()
            if route.get("feasibility") in {"confirmed", "possible"}
            and _is_nearby_route(actual, route, name)
        }
    nearby_lines = []
    if nearby_routes:
        nearby_lines.append("Nearby yaku:")
        for name, route in nearby_routes.items():
            metric = route.get("shanten", {})
            estimated = route.get("estimated_improving_draws", {})
            estimated_types = ", ".join(
                f"{tile} - {copies}"
                for tile, copies in estimated.items()
            ) or "none"
            recommended = yaku_discards.get(name, {})
            if recommended:
                yaku_discard = recommended.get("discard")
            else:
                # Compatibility with processed decisions created before the
                # evaluator emitted yaku-specific current-hand discards.
                ranked = rank_discards_for_yaku(decision, name)
                yaku_discard = ranked[0]["discard"] if ranked else None
            nearby_lines.append(
                f"  {name}: {metric.get('value')} "
                f"({metric.get('measurement')}), {route.get('feasibility')}, "
                f"yaku-discard={yaku_discard}, "
                f"estimated-improving=[{estimated_types}] {sum(estimated.values())}"
                + (
                    f", live-tenpai={route.get('tenpai_quality', {}).get('tenpai_endpoint_count', 0)}, "
                    f"best-wait={route.get('tenpai_quality', {}).get('best_wait_type_count', 0)} types/"
                    f"{route.get('tenpai_quality', {}).get('best_live_wait_copies', 0)} copies"
                    if route.get("tenpai_quality", {}).get("status") == "validated_live"
                    else ", projected"
                    if route.get("tenpai_quality", {}).get("status") == "projected"
                    else ""
                )
            )
    sections = [hand_lines, efficiency_lines, status_lines, recommendation_lines]
    if nearby_lines:
        sections.append(nearby_lines)
    return "\n\n=====\n\n".join(
        "\n".join(section) for section in sections if section
    )


def _route(candidate: dict, yaku: str) -> tuple[str, dict] | None:
    routes = candidate.get("yaku_analysis", {}).get("yaku", {})
    wanted = yaku.strip().lower().replace("-", "_").replace(" ", "_")
    for name, route in routes.items():
        if name.lower().replace("-", "_").replace(" ", "_") == wanted:
            return name, route
    return None


def rank_discards_for_yaku(decision: dict, yaku: str) -> list[dict]:
    """Rank candidate discards for one route without claiming global optimality."""
    ranked = []
    feasibility_rank = {
        "confirmed": 0, "possible": 1, "unknown": 2,
        "impossible": 3, "not_reported": 4,
    }
    measurement_rank = {"exact": 0, "lower_bound": 1, "upper_bound": 2, "heuristic": 3}
    for candidate in decision.get("all_candidates", []):
        match = _route(candidate, yaku)
        route = match[1] if match else {}
        metric = route.get("shanten", {})
        value = metric.get("value")
        ranked.append({
            "discard": candidate["discard"],
            "yaku": match[0] if match else yaku,
            "yaku_shanten": value,
            "measurement": metric.get("measurement"),
            "yaku_ukeire": sum(route.get("ukeire", {}).values()),
            "ukeire_kind": route.get("ukeire_kind", "none"),
            "estimated_improving_draws": route.get("estimated_improving_draws", {}),
            "feasibility": route.get("feasibility", "not_reported"),
            "yaku_blockers": route.get("yaku_blockers", []),
            "ordinary_shanten": candidate.get("shanten"),
            "ordinary_ukeire": candidate.get("ukeire"),
            "availability": route.get("availability", "unknown"),
            "tenpai_quality": route.get("tenpai_quality", {}),
        })
    return sorted(ranked, key=lambda item: (
        feasibility_rank.get(item["feasibility"], 9),
        item["availability"] == "dead",
        item["yaku_shanten"] is None,
        measurement_rank.get(item["measurement"], 9),
        item["yaku_shanten"] if item["yaku_shanten"] is not None else 99,
        -item["tenpai_quality"].get("tenpai_endpoint_count", 0),
        -item["tenpai_quality"].get("best_live_wait_copies", 0),
        -item["yaku_ukeire"],
        item["ordinary_shanten"] if item["ordinary_shanten"] is not None else 99,
        -(item["ordinary_ukeire"] or 0),
        item["discard"],
    ))


def rank_discards_by_yaku_coverage(decision: dict) -> list[dict]:
    """Exploratory route view, separated by evidence strength."""
    rows = []
    for candidate in decision.get("all_candidates", []):
        routes = candidate.get("yaku_analysis", {}).get("yaku", {})
        preserved = sorted(
            name for name, route in routes.items()
            if route.get("feasibility") in {"confirmed", "possible"}
            and _is_nearby_route(candidate, route, name)
        )
        confirmed = sorted(
            name for name, route in routes.items()
            if route.get("route_state") in {"component_present", "yaku_tenpai", "complete"}
            and _is_nearby_route(candidate, route, name)
        )
        validated = sorted(
            name for name in preserved
            if routes[name].get("route_state") in {"yaku_tenpai", "complete"}
            and routes[name].get("proof", {}).get("validation") == "scorer_validated"
        )
        bounded = sorted(
            name for name in preserved
            if routes[name].get("shanten", {}).get("measurement") == "lower_bound"
            and name not in validated
        )
        exact = sorted(
            name for name in preserved
            if routes[name].get("shanten", {}).get("measurement") == "exact"
            and name not in validated
        )
        heuristic = sorted(
            name for name in preserved
            if routes[name].get("shanten", {}).get("measurement") == "heuristic"
        )
        rows.append({
            "discard": candidate["discard"],
            "yaku_count": len(preserved),
            "confirmed_yaku": confirmed,
            "nearby_yaku": preserved,
            "validated_yaku": validated,
            "exact_routes": exact,
            "bounded_routes": bounded,
            "heuristic_routes": heuristic,
            "ordinary_shanten": candidate.get("shanten"),
            "ordinary_ukeire": candidate.get("ukeire"),
        })
    return sorted(rows, key=lambda item: (
        item["ordinary_shanten"] if item["ordinary_shanten"] is not None else 99,
        -len(item["validated_yaku"]),
        -len(item["exact_routes"]),
        -len(item["bounded_routes"]),
        -len(item["heuristic_routes"]),
        -(item["ordinary_ukeire"] or 0),
        item["discard"],
    ))


def rank_efficiency_discards(decision: dict, limit: int = 5) -> list[dict]:
    """Return efficient discards with their reported achievable yaku routes."""
    stored = decision.get("discard_options")
    if isinstance(stored, list):
        return [{
            "discard": option.get("discard"),
            "shanten": option.get("ordinary_shanten"),
            "ukeire": option.get("ordinary_ukeire"),
            "effective_tiles": sort_hand(
                list(option.get("effective_tiles", {}).keys())
            ),
            "yaku": [route["name"] for route in option.get("nearby_yaku", [])],
            "confirmed_yaku": sorted(
                route["name"] for route in option.get("nearby_yaku", [])
                if route.get("route_state") in {
                    "component_present", "yaku_tenpai", "complete",
                }
            ),
        } for option in stored[:max(0, limit)]]

    rows = []
    for candidate in decision.get("all_candidates", []):
        analysis = candidate.get("yaku_analysis", {})
        routes = analysis.get("yaku", {})
        yaku = sorted({
            name
            for name, route in routes.items()
            if route.get("feasibility") in {"confirmed", "possible"}
            and _is_nearby_route(candidate, route, name)
        })
        rows.append({
            "discard": candidate.get("discard"),
            "shanten": candidate.get("shanten"),
            "ukeire": candidate.get("ukeire"),
            "effective_tiles": sort_hand(
                list(candidate.get("effective_tiles", {}).keys())
            ),
            "yaku": yaku,
            "confirmed_yaku": sorted(analysis.get("established_components", [])),
        })
    ranked = sorted(rows, key=lambda item: (
        item["shanten"] if item["shanten"] is not None else 99,
        -(item["ukeire"] or 0),
        item["discard"] or "",
    ))
    return ranked[:max(0, limit)]
