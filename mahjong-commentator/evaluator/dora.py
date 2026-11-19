
from evaluator.shanten import tile_to_index

DRAGON_NEXT = {"P": "F", "F": "C", "C": "P"}
WIND_NEXT = {"E": "S", "S": "W", "W": "N", "N": "E"}


def dora_from_indicator(indicator: str) -> str:
    """Return the dora tile corresponding to an indicator."""
    if indicator in DRAGON_NEXT:
        return DRAGON_NEXT[indicator]

    if indicator in WIND_NEXT:
        return WIND_NEXT[indicator]

    tile = indicator.replace("r", "")
    number = int(tile[0])
    suit = tile[1]

    next_number = number + 1 if number < 9 else 1
    return f"{next_number}{suit}"


def analyze_hand_dora(
    concealed_tiles: list[str],
    melds: list[dict],
    dora_indicators: list[str],
) -> dict:
    """Count indicator dora and red dora currently held by the player."""
    indicator_dora = [
        dora_from_indicator(indicator)
        for indicator in dora_indicators
    ]
    held_tiles = [(tile, "concealed", None) for tile in concealed_tiles]
    for meld_index, meld in enumerate(melds):
        held_tiles.extend(
            (tile, "meld", meld_index)
            for tile in (meld.get("tiles") or [])
        )

    tile_breakdown = []
    aka_dora_han = 0
    indicator_dora_han = 0
    for tile, source, meld_index in held_tiles:
        aka = int(tile.endswith("r"))
        indicator_han = sum(
            tile_to_index(tile) == tile_to_index(dora)
            for dora in indicator_dora
        )
        if not aka and not indicator_han:
            continue
        item = {
            "tile": tile,
            "source": source,
            "aka_dora_han": aka,
            "indicator_dora_han": indicator_han,
            "total_han": aka + indicator_han,
        }
        if meld_index is not None:
            item["meld_index"] = meld_index
        tile_breakdown.append(item)
        aka_dora_han += aka
        indicator_dora_han += indicator_han

    return {
        "dora_indicators": dora_indicators.copy(),
        "indicator_dora_tiles": indicator_dora,
        "aka_dora_han": aka_dora_han,
        "indicator_dora_han": indicator_dora_han,
        "total_dora_han": aka_dora_han + indicator_dora_han,
        "tiles": tile_breakdown,
    }
