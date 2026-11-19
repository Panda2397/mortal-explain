"""Phase 1 Yakuhai and Tanyao opportunity detectors."""

from collections import Counter

from evaluator.shanten import tile_to_index
from evaluator.yaku_detector.models import (
    YakuAnalysis,
    YakuContext,
    YakuOpportunity,
)
from evaluator.yaku_detector.structural import (
    _canonical_hand,
    _live_winning_waits,
    attach_ukeire,
    route_distances,
)
from evaluator.yaku_detector.scoring import winning_methods
from evaluator.yaku_detector.context import known_tile_counts
from evaluator.yaku_detector.inventory import YAKU_INVENTORY


DRAGONS = ("P", "F", "C")
WINDS = ("E", "S", "W", "N")
SET_MELDS = {"pon", "daiminkan", "ankan", "kakan"}


def _compact_ukeire_witnesses(witnesses: dict) -> list[dict]:
    """Group repeated per-draw evidence by its resulting target.

    Remaining-copy counts already live in ``ukeire`` or
    ``estimated_improving_draws``.  The source hand is also present in the
    surrounding evaluation, so repeating a full post-draw hand for every tile
    makes processed logs much larger without adding reconstructible evidence.
    """
    groups: dict[tuple, dict] = {}
    for draw, raw_witness in witnesses.items():
        if isinstance(raw_witness, list):
            validation = "scorer_validated"
            discard = None
            target = None
            outcomes = raw_witness
        else:
            validation = raw_witness.get("validation", "unknown")
            discard = raw_witness.get("discard")
            target = raw_witness.get("yaku_shanten_after")
            outcomes = raw_witness.get("winning_outcomes", [])

        methods = tuple(sorted({
            outcome.get("method") for outcome in outcomes
            if outcome.get("method")
        }))
        key = (validation, discard, target, methods)
        if key not in groups:
            group = {
                "draws": [],
                "validation": validation,
            }
            if discard is not None:
                group["discard"] = discard
            if target is not None:
                group["yaku_shanten_after"] = target
            if methods:
                group["methods"] = list(methods)
            groups[key] = group
        groups[key]["draws"].append(draw)
    return list(groups.values())


def _normalized(tile: str) -> str:
    return tile[:-1] if tile.endswith("r") else tile


def _is_simple(tile: str) -> bool:
    index = tile_to_index(tile)
    return index < 27 and 1 <= index % 9 <= 7


def _value_reasons(tile: str, context: YakuContext) -> tuple[str, ...]:
    reasons: list[str] = []
    if tile in DRAGONS:
        reasons.append("dragon")
    if tile == context.round_wind:
        reasons.append("round_wind")
    if tile == context.seat_wind:
        reasons.append("seat_wind")
    return tuple(reasons)


def _fixed_value_sets(tile: str, context: YakuContext) -> tuple[int, ...]:
    result = []
    for meld in context.melds:
        normalized = tuple(_normalized(value) for value in meld.tiles)
        if (
            meld.type in SET_MELDS
            and len(normalized) >= 3
            and all(value == tile for value in normalized)
        ):
            result.append(meld.source_index)
    return tuple(result)


def detect_yakuhai(context: YakuContext) -> dict[str, YakuOpportunity]:
    concealed = Counter(_normalized(tile) for tile in context.concealed_tiles)
    known = known_tile_counts(context) if context.melds_complete else Counter(
        tile_to_index(tile) for tile in context.concealed_tiles + context.visible_tiles
    )
    result: dict[str, YakuOpportunity] = {}

    value_tiles = set(DRAGONS)
    if context.round_wind is not None:
        value_tiles.add(context.round_wind)
    if context.seat_wind is not None:
        value_tiles.add(context.seat_wind)

    for tile in sorted(value_tiles, key=lambda value: (*WINDS, *DRAGONS).index(value)):
        reasons = _value_reasons(tile, context)
        fixed_sets = _fixed_value_sets(tile, context)
        count = concealed[tile]
        # A value honor with no held/fixed support is technically drawable,
        # but listing every such tile on every discard candidate creates
        # noise rather than a meaningful current opportunity.
        if count == 0 and not fixed_sets:
            continue
        copies_needed = max(0, 3 - count)
        live_copies = max(0, 4 - known[tile_to_index(tile)])
        structure_present = bool(fixed_sets) or count >= 3

        if not context.melds_complete:
            feasibility = "unknown"
            guaranteed = None
            facts = ("MELD_CONTEXT_INCOMPLETE",)
        elif fixed_sets:
            feasibility = "possible"
            guaranteed = True
            facts = ("FIXED_VALUE_HONOR_SET",)
        elif count >= 3:
            feasibility = "possible"
            guaranteed = False
            facts = ("CONCEALED_VALUE_HONOR_SET",)
        elif live_copies < copies_needed:
            feasibility = "impossible"
            guaranteed = False
            facts = ("INSUFFICIENT_LIVE_COPIES",)
        else:
            feasibility = "possible"
            guaranteed = False
            facts = ("VALUE_HONOR_ROUTE_AVAILABLE",)

        support_count = count + sum(len(context.melds[i].tiles) for i in fixed_sets)
        result[f"yakuhai_{tile}"] = YakuOpportunity(
            yaku="yakuhai",
            feasibility=feasibility,
            promising=(structure_present or count == 2) if feasibility != "unknown" else None,
            guaranteed_on_completion=guaranteed,
            supporting_tiles=tuple([tile] * support_count),
            fixed_meld_indices=fixed_sets,
            facts=facts,
            metrics={
                "tile": tile,
                "reasons": list(reasons),
                "han_if_completed": len(reasons),
                "concealed_count": count,
                "copies_needed": copies_needed,
                "live_copies": live_copies,
                "structure_present": structure_present,
            },
        )
    return result


def detect_tanyao(context: YakuContext) -> YakuOpportunity:
    obstructing = tuple(tile for tile in context.concealed_tiles if not _is_simple(tile))
    conflicts = tuple(
        meld.source_index
        for meld in context.melds
        if any(not _is_simple(tile) for tile in meld.tiles)
    )

    if not context.melds_complete:
        feasibility = "unknown"
        promising = None
        guaranteed = None
        facts = ("MELD_CONTEXT_INCOMPLETE",)
    elif context.menzen is False and not context.rules.open_tanyao:
        feasibility = "impossible"
        promising = False
        guaranteed = False
        facts = ("OPEN_TANYAO_DISABLED",)
    elif conflicts:
        feasibility = "impossible"
        promising = False
        guaranteed = False
        facts = ("FIXED_OUTSIDE_MELD",)
    elif obstructing:
        # These tiles can be discarded, but Phase 1 does not perform a
        # constructive yaku-specific completion search.
        feasibility = "unknown"
        promising = len(obstructing) <= 1
        guaranteed = False
        facts = ("CONCEALED_OUTSIDE_TILES_DISCARDABLE",)
    else:
        feasibility = "possible"
        promising = True
        guaranteed = False
        facts = ("ALL_CURRENT_TILES_SIMPLE",)

    supporting = tuple(sorted({
        _normalized(tile)
        for tile in context.concealed_tiles
        if _is_simple(tile)
    }, key=tile_to_index))
    return YakuOpportunity(
        yaku="tanyao",
        feasibility=feasibility,
        promising=promising,
        guaranteed_on_completion=guaranteed,
        supporting_tiles=supporting,
        obstructing_tiles=obstructing,
        fixed_meld_indices=conflicts,
        facts=facts,
        metrics={
            "incompatible_concealed_tiles": len(obstructing),
            "simple_concealed_tiles": len(supporting),
            "open_tanyao_enabled": context.rules.open_tanyao,
            "yaku_shanten": None,
            "yaku_ukeire": None,
        },
    )


def detect_yaku_opportunities(context: YakuContext) -> YakuAnalysis:
    opportunities = detect_yakuhai(context)
    opportunities["tanyao"] = detect_tanyao(context)
    established = any(
        value.guaranteed_on_completion is True
        for value in opportunities.values()
    )
    return YakuAnalysis(
        menzen=context.menzen,
        input_complete=(
            context.input_complete
            and context.round_wind is not None
            and context.seat_wind is not None
        ),
        has_established_yaku=established if context.melds_complete else None,
        opportunities=opportunities,
    )


def detect_yaku_routes(
    context: YakuContext,
    *,
    include_transitions: bool = True,
    max_extra_shanten: int | None = None,
) -> dict:
    """Return the compact measured route contract requested by the evaluator."""
    analysis = detect_yaku_opportunities(context)
    if not context.melds_complete:
        return {
            "confirmed_yaku": [],
            "established_components": [],
            "yaku_tenpai": [],
            "validated_complete_yaku": [],
            "yaku": {},
            "route_evidence_status": "unknown_incomplete_meld_context",
        }
    routes = route_distances(context)
    regular = _regular_shanten(context)
    equivalent_tiles = len(context.concealed_tiles) + 3 * len(context.melds)
    if equivalent_tiles == 13:
        routes = attach_ukeire(
            context, routes, include_transitions=include_transitions
        )
    established_components = []
    yaku_tenpai = []
    for key, route in routes.items():
        if route.get("route_state") == "component_present":
            established_components.append(key)
        if route.get("route_state") == "yaku_tenpai":
            yaku_tenpai.append(key)
    # A numeric zero alone is not proof of yaku-tenpai. Only scorer-backed
    # live waits may promote the route state.
    for key, route in routes.items():
        if (
            route["feasibility"] == "possible"
            and route["shanten"]["value"] == 0
            and route["shanten"]["measurement"] == "exact"
            and route.get("ukeire_witnesses")
        ):
            route["route_state"] = "yaku_tenpai"
            route["proof"]["validation"] = "scorer_validated"
            route["legacy_feasibility"] = "confirmed"
            if key not in yaku_tenpai:
                yaku_tenpai.append(key)
    for key, opportunity in analysis.opportunities.items():
        if opportunity.yaku != "yakuhai":
            continue
        if opportunity.feasibility == "impossible":
            value = None
        else:
            structure_present = opportunity.metrics.get("structure_present")
            missing = 0 if structure_present else opportunity.metrics["copies_needed"]
            # A pair can be a zero-shanten shanpon/tanki component waiting on
            # the third copy. A singleton still needs two copies before it can
            # supply a Yakuhai set in a qualifying tenpai structure.
            honor_distance = max(0, missing - 1)
            value = max(regular, honor_distance)

            # A singleton's theoretical distance of one is valid only if
            # drawing the second honor, discarding one tile, and later winning
            # on the third honor produces a scorer-accepted Yakuhai hand.
            # Otherwise at least two structural improvements are necessary.
            concealed_count = opportunity.metrics.get("concealed_count", 0)
            if equivalent_tiles == 13 and concealed_count == 1 and value == 1:
                honor = opportunity.metrics["tile"]
                fourteen = context.concealed_tiles + (honor,)
                one_step_witness = False
                seen_discards = set()
                for discard_index, discard in enumerate(fourteen):
                    discard_type = tile_to_index(discard)
                    if discard_type in seen_discards or _normalized(discard) == honor:
                        continue
                    seen_discards.add(discard_type)
                    after = fourteen[:discard_index] + fourteen[discard_index + 1:]
                    if winning_methods(context, key, honor, concealed=after):
                        one_step_witness = True
                        break
                if not one_step_witness:
                    value = 2
        # The interactive route summary treats an already formed concealed
        # value-honor triplet as confirmed in the current post-discard hand.
        # The lower-level opportunity object still distinguishes it from an
        # irreversible fixed meld through guaranteed_on_completion.
        component_present = opportunity.metrics.get("structure_present")
        feasibility = opportunity.feasibility
        if component_present and key not in established_components:
            established_components.append(key)
        ukeire = {}
        ukeire_kind = "none"
        ukeire_witnesses = {}
        tenpai_endpoints = {}
        if equivalent_tiles == 13 and value == 0:
            known = known_tile_counts(context)
            concealed_count = opportunity.metrics.get("concealed_count", 0)
            # With only a value-honor pair, Yakuhai can be completed only on
            # that honor. An existing triplet/fixed set permits any hand wait.
            draw_indices = (
                [tile_to_index(opportunity.metrics["tile"])]
                if concealed_count == 2 and not component_present else range(34)
            )
            from evaluator.shanten import index_to_tile
            for draw_index in draw_indices:
                remaining = 4 - known[draw_index]
                if remaining <= 0:
                    continue
                draw = index_to_tile(draw_index)
                methods = winning_methods(context, key, draw)
                if methods:
                    ukeire[draw] = remaining
                    ukeire_kind = "scorer_validated"
                    ukeire_witnesses[draw] = methods

            # Numeric zero without a live scorer-backed wait is only a lower
            # bound, not demonstrated Yakuhai tenpai.
            if not ukeire_witnesses and not component_present:
                value = 1
        if equivalent_tiles == 13 and value is not None and value > 0:
            from evaluator.shanten import calculate_shanten_by_type
            from evaluator.shanten import index_to_tile
            known = known_tile_counts(context)
            honor = opportunity.metrics["tile"]
            fixed_present = bool(opportunity.fixed_meld_indices)
            metric_cache = {}

            def yakuhai_metric(hand):
                canonical = _canonical_hand(hand)
                if canonical in metric_cache:
                    return metric_cache[canonical]
                count = sum(_normalized(tile) == honor for tile in hand)
                structure = fixed_present or count >= 3
                honor_floor = 0 if structure else max(0, (3 - count) - 1)
                shape = calculate_shanten_by_type(
                    list(hand), len(context.melds)
                )["regular"]["shanten"]
                measured = max(shape, honor_floor)
                if count == 1 and measured == 1 and not fixed_present:
                    paired = hand + (honor,)
                    one_step = False
                    seen = set()
                    for index, discard in enumerate(paired):
                        discard_type = tile_to_index(discard)
                        if discard_type in seen or _normalized(discard) == honor:
                            continue
                        seen.add(discard_type)
                        after_discard = paired[:index] + paired[index + 1:]
                        if winning_methods(
                            context, key, honor, concealed=after_discard
                        ):
                            one_step = True
                            break
                    if not one_step:
                        measured = 2
                metric_cache[canonical] = measured
                return measured

            for draw_index in range(34):
                remaining = 4 - known[draw_index]
                if remaining <= 0:
                    continue
                draw = index_to_tile(draw_index)
                fourteen = context.concealed_tiles + (draw,)
                best = value
                best_transitions = []
                seen_discards = set()
                for discard_index, discard in enumerate(fourteen):
                    discard_type = tile_to_index(discard)
                    if discard_type in seen_discards:
                        continue
                    seen_discards.add(discard_type)
                    after = fourteen[:discard_index] + fourteen[discard_index + 1:]
                    measured = yakuhai_metric(after)
                    if measured < best:
                        best = measured
                        best_transitions = [(discard, after)]
                    elif measured == best and measured < value:
                        best_transitions.append((discard, after))
                if best >= value:
                    continue

                chosen = best_transitions[0] if best_transitions else (None, None)
                live_waits = {}
                if best == 0:
                    for transition in best_transitions:
                        waits = _live_winning_waits(
                            context, key, transition[1], (transition[0],)
                        )
                        if waits:
                            chosen = transition
                            live_waits = waits
                            break
                    if value == 1 and not live_waits:
                        continue

                ukeire[draw] = remaining
                ukeire_kind = "estimated_metric_improvement"
                witness = {
                    "draw": draw,
                    "discard": chosen[0],
                    "yaku_shanten_after": best,
                    "validation": "estimated_metric_improvement",
                }
                if live_waits:
                    witness["tenpai_waits"] = {
                        tile: item["remaining"]
                        for tile, item in live_waits.items()
                    }
                    tenpai_endpoints[_canonical_hand(chosen[1])] = live_waits
                ukeire_witnesses[draw] = witness
        routes[key] = {
            "shanten": {"value": value, "measurement": "lower_bound"},
            "ukeire": ukeire,
            "feasibility": feasibility,
            "yaku_blockers": (
                [] if opportunity.feasibility != "impossible" else [{
                    "type": "insufficient_copies",
                    "severity": "irreversible",
                    "reason": "insufficient_live_copies",
                }]
            ),
            "route_state": "component_present" if component_present else "none",
            "proof": {"distance": "lower_bound", "validation": (
                "scorer_validated" if value == 0 and ukeire_witnesses else (
                    "structural_witness" if component_present else "unvalidated"
                )
            )},
            "outcome_scope": {"ron": "unknown", "tsumo": "unknown"},
            "availability": "live" if ukeire else "unknown",
            "guarantee": (
                "some_live_wins"
                if (value == 0 and ukeire_witnesses) or tenpai_endpoints else
                "none"
            ),
            "legacy_feasibility": "confirmed" if component_present else feasibility,
            "ukeire_kind": ukeire_kind,
            "ukeire_witnesses": ukeire_witnesses,
            "estimated_improving_draws": (
                ukeire.copy() if ukeire_kind == "estimated_metric_improvement" else {}
            ),
            "tenpai_quality": {
                "status": (
                    "validated_live" if ukeire_witnesses and value == 0 else
                    "validated_live" if tenpai_endpoints else
                    "projected" if value in {1, 2} else
                    "dead" if value == 0 else "not_reached"
                ),
                "lookahead_depth": 0 if value == 0 else (1 if value in {1, 2} else 0),
                "tenpai_endpoint_count": (
                    1 if value == 0 and ukeire_witnesses else len(tenpai_endpoints)
                ),
                "distinct_winning_tiles": sorted({
                    tile for waits in tenpai_endpoints.values() for tile in waits
                } if value else set(ukeire)),
                "best_wait_type_count": (
                    len(ukeire) if value == 0 else
                    max((len(waits) for waits in tenpai_endpoints.values()), default=0)
                ),
                "best_live_wait_copies": (
                    sum(ukeire.values()) if value == 0 else
                    max((sum(item["remaining"] for item in waits.values())
                         for waits in tenpai_endpoints.values()), default=0)
                ),
            },
        }
        if ukeire_kind == "estimated_metric_improvement":
            routes[key]["ukeire"] = {}
        if value == 0 and ukeire_witnesses:
            routes[key]["route_state"] = "yaku_tenpai"
            routes[key]["legacy_feasibility"] = "confirmed"
            routes[key]["outcome_scope"] = {
                "ron": "validated" if any(
                    outcome["method"] == "ron"
                    for outcomes in ukeire_witnesses.values() for outcome in outcomes
                ) else "invalid",
                "tsumo": "validated" if any(
                    outcome["method"] == "tsumo"
                    for outcomes in ukeire_witnesses.values() for outcome in outcomes
                ) else "invalid",
            }
            if key not in yaku_tenpai:
                yaku_tenpai.append(key)
    for key, route in routes.items():
        base_name = (
            "yakuhai" if key.startswith("yakuhai_") else
            "honitsu" if key.startswith("honitsu_") else
            "chinitsu" if key.startswith("chinitsu_") else key
        )
        metadata = YAKU_INVENTORY.get(base_name, {})
        category = metadata.get("category", "unknown")
        route["yaku_category"] = category
        route["menzen_required"] = category in {"menzen_only", "yakuman_menzen"}
        route["open_allowed"] = category in {
            "open_reduced", "open_same", "yakuman_open"
        }
        route["open_han_reduced"] = category == "open_reduced"
        route["structural"] = metadata.get("structural", True)

        # Internally, transition search uses a per-draw mapping.  Serialize a
        # compact grouped list after all validation and outcome aggregation is
        # complete so consumers receive only a few target groups per route.
        route["ukeire_witnesses"] = _compact_ukeire_witnesses(
            route.get("ukeire_witnesses", {})
        )

    def within_reported_distance(route: dict) -> bool:
        value = route["shanten"]["value"]
        if value is None:
            return False
        if max_extra_shanten is None:
            # Broad detector/audit view retained for direct callers.
            return value <= 3
        return value - regular <= max_extra_shanten

    reported = {
        key: value for key, value in routes.items()
        if value.get("route_state") in {"component_present", "yaku_tenpai", "complete"}
        or value["feasibility"] == "impossible"
        or within_reported_distance(value)
    }
    reported = dict(sorted(reported.items(), key=lambda item: (
        item[1]["shanten"]["value"] is None,
        item[1]["shanten"]["value"] if item[1]["shanten"]["value"] is not None else 99,
        item[0],
    )))
    return {
        # Deprecated compatibility field: use the explicit state lists below.
        "confirmed_yaku": sorted(set(established_components) | set(yaku_tenpai)),
        "established_components": sorted(established_components),
        "yaku_tenpai": sorted(yaku_tenpai),
        "validated_complete_yaku": [],
        "yaku": reported,
        "route_evidence_status": "complete",
        "route_filter": {
            "max_extra_shanten": max_extra_shanten,
            "formula": (
                "yaku_shanten - ordinary_shanten <= max_extra_shanten"
                if max_extra_shanten is not None else
                "broad_detector_view_yaku_shanten <= 3"
            ),
            "preserves_established_and_impossible_routes": True,
        },
    }


def _regular_shanten(context: YakuContext) -> int:
    from evaluator.shanten import calculate_shanten_by_type
    return calculate_shanten_by_type(
        list(context.concealed_tiles), len(context.melds)
    )["regular"]["shanten"]


def compare_yaku_analyses(actual: dict, alternative: dict) -> list[dict]:
    """Return compact, factual changes between two serialized analyses."""
    result = []
    actual_opportunities = actual.get("opportunities", {})
    alternative_opportunities = alternative.get("opportunities", {})
    for key in sorted(set(actual_opportunities) | set(alternative_opportunities)):
        before = actual_opportunities.get(key)
        after = alternative_opportunities.get(key)
        if before is None or after is None:
            continue
        effects = []
        if before["feasibility"] != after["feasibility"]:
            effects.append("FEASIBILITY_CHANGED")
        before_obstructions = before.get("metrics", {}).get("incompatible_concealed_tiles")
        after_obstructions = after.get("metrics", {}).get("incompatible_concealed_tiles")
        if before_obstructions is not None and after_obstructions is not None:
            if after_obstructions < before_obstructions:
                effects.append("FEWER_OBSTRUCTIONS")
            elif after_obstructions > before_obstructions:
                effects.append("MORE_OBSTRUCTIONS")
        before_support = before.get("metrics", {}).get("concealed_count")
        after_support = after.get("metrics", {}).get("concealed_count")
        if before_support is not None and after_support is not None:
            if after_support < before_support:
                effects.append("LESS_SUPPORT")
            elif after_support > before_support:
                effects.append("MORE_SUPPORT")
        if effects:
            result.append({"yaku": key, "effects": effects})
    actual_routes = actual.get("yaku", {})
    alternative_routes = alternative.get("yaku", {})
    for key in sorted(set(actual_routes) | set(alternative_routes)):
        before = actual_routes.get(key)
        after = alternative_routes.get(key)
        effects = []
        if before is None:
            effects.append("ROUTE_ADDED")
        elif after is None:
            effects.append("ROUTE_REMOVED")
        else:
            before_value = before.get("shanten", {}).get("value")
            after_value = after.get("shanten", {}).get("value")
            if before_value is not None and after_value is not None:
                if after_value < before_value:
                    effects.append("ROUTE_DISTANCE_LOWER")
                elif after_value > before_value:
                    effects.append("ROUTE_DISTANCE_HIGHER")
            if before.get("route_state") != after.get("route_state"):
                effects.append("ROUTE_STATE_CHANGED")
        if effects:
            existing = next((item for item in result if item["yaku"] == key), None)
            if existing:
                existing["effects"].extend(
                    effect for effect in effects if effect not in existing["effects"]
                )
            else:
                result.append({"yaku": key, "effects": effects})
    return result
