
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


def analyze_discard_dora(
    tile: str,
    dora_indicators: list[str],
) -> dict:
    """Analyze bonus-han potential lost by discarding this tile."""
    is_aka_dora = tile.endswith("r")

    indicator_dora = [
        dora_from_indicator(indicator)
        for indicator in dora_indicators
    ]

    normal_tile = tile.replace("r", "")

    indicator_dora_count = sum(
        tile_to_index(normal_tile) == tile_to_index(dora)
        for dora in indicator_dora
    )

    return {
        "tile": tile,
        "is_aka_dora": is_aka_dora,
        "is_indicator_dora": indicator_dora_count > 0,
        "aka_dora_han": int(is_aka_dora),
        "indicator_dora_han": indicator_dora_count,
        "potential_bonus_han": (
            int(is_aka_dora) + indicator_dora_count
        ),
    }
