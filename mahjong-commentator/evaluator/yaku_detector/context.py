"""Normalize evaluator state into a conservative yaku detector context."""

from collections import Counter

from evaluator.shanten import tile_to_index
from evaluator.yaku_detector.models import (
    FixedMeld,
    YakuContext,
    YakuRules,
)


MELD_TYPES = {"chi", "pon", "daiminkan", "ankan", "kakan"}


def _validate_tile(tile: str) -> str:
    tile_to_index(tile)
    return tile


def normalize_yaku_context(
    *,
    hand: list[str],
    open_melds: list[dict] | int,
    visible_tiles: list[str],
    round_info: dict | None,
    rules: YakuRules | None = None,
) -> YakuContext:
    """Validate and normalize live or legacy decision state.

    Integer-only meld data remains readable, but its contents and menzen state
    are deliberately unknown rather than guessed.
    """
    concealed = tuple(_validate_tile(tile) for tile in hand)
    visible = tuple(_validate_tile(tile) for tile in visible_tiles)
    normalized_melds: list[FixedMeld] = []

    melds_complete = isinstance(open_melds, list)
    if melds_complete:
        for index, meld in enumerate(open_melds):
            if not isinstance(meld, dict):
                raise ValueError(f"Meld {index} must be an object")
            meld_type = meld.get("type")
            if meld_type not in MELD_TYPES:
                raise ValueError(f"Unsupported meld type at {index}: {meld_type!r}")
            raw_tiles = meld.get("tiles")
            if not isinstance(raw_tiles, list) or len(raw_tiles) not in (3, 4):
                raise ValueError(f"Meld {index} must contain three or four tiles")
            tiles = tuple(_validate_tile(tile) for tile in raw_tiles)
            ids = sorted(tile_to_index(tile) for tile in tiles)
            if meld_type == "chi":
                if len(ids) != 3 or ids[0] >= 27 or ids[0] // 9 != ids[-1] // 9 \
                        or ids != list(range(ids[0], ids[0] + 3)):
                    raise ValueError(f"Meld {index} is not a valid chi")
            elif meld_type == "pon":
                if len(ids) != 3 or len(set(ids)) != 1:
                    raise ValueError(f"Meld {index} is not a valid pon")
            else:
                if len(ids) != 4 or len(set(ids)) != 1:
                    raise ValueError(f"Meld {index} is not a valid kan")
            default_open = meld_type != "ankan"
            is_open = meld.get("open", default_open)
            if not isinstance(is_open, bool):
                raise ValueError(f"Meld {index} has invalid open flag")
            if meld_type == "ankan" and is_open:
                raise ValueError("Ankan cannot be marked open")
            if meld_type != "ankan" and not is_open:
                raise ValueError(f"{meld_type} must be marked open")
            normalized_melds.append(FixedMeld(
                type=meld_type,
                tiles=tiles,
                is_open=is_open,
                source_index=index,
            ))
        menzen: bool | None = not any(meld.is_open for meld in normalized_melds)
        declared_meld_count = len(normalized_melds)
    else:
        if not isinstance(open_melds, int) or open_melds < 0:
            raise ValueError("open_melds must be a structured list or non-negative count")
        menzen = True if open_melds == 0 else None
        declared_meld_count = open_melds

    round_info = round_info or {}
    round_wind = round_info.get("bakaze")
    seat_wind = round_info.get("jikaze")
    for label, wind in (("round", round_wind), ("seat", seat_wind)):
        if wind is not None and wind not in {"E", "S", "W", "N"}:
            raise ValueError(f"Invalid {label} wind: {wind!r}")

    context = YakuContext(
        concealed_tiles=concealed,
        melds=tuple(normalized_melds),
        visible_tiles=visible,
        round_wind=round_wind,
        seat_wind=seat_wind,
        rules=rules or YakuRules(),
        melds_complete=melds_complete,
        menzen=menzen,
        declared_meld_count=declared_meld_count,
    )
    if melds_complete:
        known_tile_counts(context)
    return context


def known_tile_counts(context: YakuContext) -> Counter:
    """Count unavailable copies without double-counting melds in visibility.

    Parser-produced states already include called tiles in ``visible_tiles``;
    direct detector callers often supply melds separately.  Taking the larger
    public count per tile supports both representations.
    """
    concealed = Counter(tile_to_index(tile) for tile in context.concealed_tiles)
    public = Counter(tile_to_index(tile) for tile in context.visible_tiles)
    fixed = Counter(
        tile_to_index(tile) for meld in context.melds for tile in meld.tiles
    )
    result = concealed.copy()
    for index in range(34):
        result[index] += max(public[index], fixed[index])
        if result[index] > 4:
            raise ValueError(f"More than four known copies of tile index {index}")
    return result
