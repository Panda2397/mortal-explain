"""Exact live-wait and no-yaku evidence for a post-discard hand."""

from collections import Counter

from evaluator.shanten import calculate_shanten, index_to_tile, tile_to_index
from evaluator.yaku_detector.models import YakuContext
from evaluator.yaku_detector.scoring import score_completed_hand
from evaluator.yaku_detector.context import known_tile_counts


def analyze_tenpai_legality(
    ctx: YakuContext,
    *,
    own_discards: list[str] | tuple[str, ...] = (),
    player_score: int | None = None,
    remaining_wall_tiles: int | None = None,
) -> dict:
    if not ctx.melds_complete:
        return {"structural_tenpai": None, "status": "unknown_incomplete_meld_context"}
    if calculate_shanten(list(ctx.concealed_tiles), len(ctx.melds)) != 0:
        return {"structural_tenpai": False, "waits": {}, "status": "not_tenpai"}

    known = known_tile_counts(ctx)
    waits = {}
    for index in range(34):
        remaining = 4 - known[index]
        if remaining <= 0:
            continue
        draw = index_to_tile(index)
        completed = ctx.concealed_tiles + (draw,)
        if calculate_shanten(list(completed), len(ctx.melds)) != -1:
            continue
        outcomes = {}
        for is_tsumo in (False, True):
            scored = score_completed_hand(ctx, completed, is_tsumo=is_tsumo)
            yaku = scored["yaku"] if scored else []
            outcomes["tsumo" if is_tsumo else "ron"] = {
                "has_yaku": bool(yaku),
                "yaku": yaku,
            }
        waits[draw] = {"remaining": remaining, **outcomes}

    own_indices = {tile_to_index(tile) for tile in own_discards}
    permanent_furiten = any(tile_to_index(tile) in own_indices for tile in waits)
    for evidence in waits.values():
        evidence["ron"]["furiten"] = permanent_furiten
        evidence["ron"]["legal"] = evidence["ron"]["has_yaku"] and not permanent_furiten
        evidence["tsumo"]["legal"] = evidence["tsumo"]["has_yaku"]

    live = list(waits.values())
    dama_ron_any = any(item["ron"]["has_yaku"] for item in live)
    dama_tsumo_any = any(item["tsumo"]["has_yaku"] for item in live)
    if ctx.menzen is False:
        riichi = "ineligible_open_hand"
    elif player_score is not None and player_score < 1000:
        riichi = "ineligible_points"
    elif remaining_wall_tiles is not None and remaining_wall_tiles < 4:
        riichi = "ineligible_wall"
    else:
        riichi = "eligible_if_untracked_conditions_allow"

    return {
        "structural_tenpai": True,
        "status": "validated",
        "waits": waits,
        "permanent_furiten": permanent_furiten,
        "temporary_furiten": "unknown",
        "dama_ron_has_yaku_on_any_live_wait": dama_ron_any,
        "dama_tsumo_has_yaku_on_any_live_wait": dama_tsumo_any,
        "has_yaku_on_all_live_waits": bool(live) and all(
            item["ron"]["has_yaku"] or item["tsumo"]["has_yaku"] for item in live
        ),
        "open_no_yaku_tenpai": ctx.menzen is False and not dama_ron_any and not dama_tsumo_any,
        "closed_dama_no_yaku_tenpai": ctx.menzen is True and not dama_ron_any,
        "riichi_eligibility": riichi,
    }
