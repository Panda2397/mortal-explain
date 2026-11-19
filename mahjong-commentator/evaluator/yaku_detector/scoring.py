"""Scorer-backed completed-hand witnesses for yaku-tenpai validation."""

import re
from collections import Counter

from evaluator.shanten import tile_to_index
from evaluator.yaku_detector.models import YakuContext


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


ROUTE_ALIASES = {
    "tanyao": {"tanyao"},
    "pinfu": {"pinfu"},
    "iipeikou": {"iipeiko", "iipeikou"},
    "ryanpeikou": {"ryanpeiko", "ryanpeikou"},
    "chiitoitsu": {"chiitoitsu"},
    "toitoi": {"toitoi"},
    "sanankou": {"sanankou"},
    "suuankou": {"suuankou", "suuankoutanki"},
    "sanshoku_doujun": {"sanshoku"},
    "sanshoku_doukou": {"sanshokudoukou"},
    "ittsu": {"ittsu"},
    "chanta": {"chanta"},
    "junchan": {"junchan"},
    "honroutou": {"honroto", "honroutou"},
    "kokushi": {"kokushimusou", "kokushimusou13sidedwait"},
    "sankantsu": {"sankantsu"},
    "shousangen": {"shousangen"},
    "chuuren_poutou": {"chuurenpoutou", "junseichuurenpoutou"},
    "daisangen": {"daisangen"},
    "shousuushii": {"shousuushii"},
    "daisuushii": {"daisuushii"},
    "tsuuiisou": {"tsuuiisou"},
    "chinroutou": {"chinroutou"},
    "ryuuiisou": {"ryuuiisou"},
    "suukantsu": {"suukantsu"},
}


def _meld_type(value: str) -> str:
    from mahjong.meld import Meld
    if value == "chi":
        return Meld.CHI
    if value == "pon":
        return Meld.PON
    if value == "kakan":
        return Meld.SHOUMINKAN
    return Meld.KAN


def score_completed_hand(
    ctx: YakuContext,
    concealed_with_win: tuple[str, ...],
    *,
    is_tsumo: bool,
) -> dict | None:
    """Score one completed outcome without inventing situational yaku flags."""
    from mahjong.hand_calculating.hand import HandCalculator
    from mahjong.hand_calculating.hand_config import HandConfig, OptionalRules
    from mahjong.meld import Meld

    used = Counter()

    def allocate(tile: str) -> int:
        index = tile_to_index(tile)
        copy = used[index]
        if copy >= 4:
            raise ValueError(f"More than four copies of tile index {index}")
        used[index] += 1
        return index * 4 + copy

    concealed_ids = [allocate(tile) for tile in concealed_with_win]
    win_tile = concealed_ids[-1]
    melds = []
    meld_ids = []
    for fixed in ctx.melds:
        ids = [allocate(tile) for tile in fixed.tiles]
        meld_ids.extend(ids)
        melds.append(Meld(
            meld_type=_meld_type(fixed.type),
            # Parser call order puts the called tile last/first depending on
            # source. The scorer requires chi tiles in ascending tile order.
            tiles=sorted(ids),
            opened=fixed.is_open,
        ))

    config = HandConfig(
        is_tsumo=is_tsumo,
        player_wind=tile_to_index(ctx.seat_wind) if ctx.seat_wind else None,
        round_wind=tile_to_index(ctx.round_wind) if ctx.round_wind else None,
        options=OptionalRules(
            has_open_tanyao=ctx.rules.open_tanyao,
            # Bonus han are deliberately excluded from yaku legality witnesses.
            has_aka_dora=False,
        ),
    )
    response = HandCalculator().estimate_hand_value(
        concealed_ids + meld_ids,
        win_tile,
        melds=melds,
        config=config,
    )
    if response.error is not None:
        return None
    return {
        "method": "tsumo" if is_tsumo else "ron",
        "yaku": [getattr(yaku, "name", str(yaku)) for yaku in response.yaku or []],
    }


def route_matches(route: str, yaku_names: list[str], ctx: YakuContext) -> bool:
    keys = {_key(name) for name in yaku_names}
    if route.startswith("honitsu_"):
        return "honitsu" in keys
    if route.startswith("chinitsu_"):
        return "chinitsu" in keys
    if route.startswith("yakuhai_"):
        tile = route.rsplit("_", 1)[1]
        names = {
            "P": {"yakuhaihaku"},
            "F": {"yakuhaihatsu"},
            "C": {"yakuhaichun"},
        }.get(tile, set())
        if tile == ctx.seat_wind:
            names.add("yakuhai" + "seatwind" + {
                "E": "east", "S": "south", "W": "west", "N": "north",
            }[tile])
        if tile == ctx.round_wind:
            names.add("yakuhai" + "roundwind" + {
                "E": "east", "S": "south", "W": "west", "N": "north",
            }[tile])
        return bool(keys & names)
    return bool(keys & ROUTE_ALIASES.get(route, {route.replace("_", "")}))


def winning_methods(
    ctx: YakuContext,
    route: str,
    draw: str,
    concealed: tuple[str, ...] | None = None,
) -> list[dict]:
    completed = (concealed if concealed is not None else ctx.concealed_tiles) + (draw,)
    results = []
    for is_tsumo in (False, True):
        scored = score_completed_hand(ctx, completed, is_tsumo=is_tsumo)
        if scored and route_matches(route, scored["yaku"], ctx):
            results.append(scored)
    return results
