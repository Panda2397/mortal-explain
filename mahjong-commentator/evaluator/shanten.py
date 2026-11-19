from mahjong.shanten import Shanten


# MJAI tile → 34-index representation
HONORS = {
    "E": 27,
    "S": 28,
    "W": 29,
    "N": 30,
    "P": 31,
    "F": 32,
    "C": 33,
}

def index_to_tile(index: int) -> str:
    """
    Convert 34-index representation back to MJAI tile.
    Red fives are represented as normal fives.
    """

    if not isinstance(index, int) or not 0 <= index < 34:
        raise ValueError(f"Invalid 34-tile index: {index}")

    if 0 <= index <= 8:
        return f"{index + 1}m"

    if 9 <= index <= 17:
        return f"{index - 8}p"

    if 18 <= index <= 26:
        return f"{index - 17}s"

    honors = ["E", "S", "W", "N", "P", "F", "C"]

    return honors[index - 27]

def tile_to_index(tile: str) -> int:
    """
    Convert MJAI tile notation into a 34-index tile type.

    Examples:
        1m  -> 0
        9m  -> 8
        1p  -> 9
        9p  -> 17
        1s  -> 18
        9s  -> 26
        E   -> 27
        C   -> 33
        5mr -> 4  (red five)
    """

    if not isinstance(tile, str):
        raise ValueError(f"Invalid MJAI tile: {tile!r}")

    if tile in HONORS:
        return HONORS[tile]

    # A 34-type structural vector cannot represent red identity separately.
    # Normalize red fives here; use ``hand_to_34_with_red`` when bonus-tile
    # identity is also needed.
    if tile.endswith("r"):
        if len(tile) != 3 or tile[0] != "5" or tile[1] not in "mps":
            raise ValueError(f"Invalid MJAI red tile: {tile}")
        tile = tile[:-1]

    if len(tile) != 2 or tile[0] not in "123456789":
        raise ValueError(f"Invalid MJAI tile: {tile}")

    number = int(tile[0])
    suit = tile[1]

    if suit == "m":
        return number - 1

    if suit == "p":
        return 9 + number - 1

    if suit == "s":
        return 18 + number - 1

    raise ValueError(f"Invalid MJAI tile: {tile}")


def hand_to_34(hand: list[str]) -> list[int]:
    """
    Convert MJAI tiles to a 34-element structural count array.

    Red fives are included in their normal five slot because they are not a
    separate structural tile type. Use ``hand_to_34_with_red`` to retain
    their bonus identity alongside the structural counts.
    """

    tiles = [0] * 34

    for tile in hand:
        index = tile_to_index(tile)
        tiles[index] += 1

    return tiles


def hand_to_34_with_red(hand: list[str]) -> dict:
    """Return structural counts together with per-suit red-five counts."""
    red_fives = {
        suit: hand.count(f"5{suit}r")
        for suit in ("m", "p", "s")
    }
    return {
        "counts": hand_to_34(hand),
        "red_fives": red_fives,
        "red_dora_count": sum(red_fives.values()),
    }


def calculate_shanten(
    hand: list[str],
    open_melds: int = 0
) -> int:
    """
    Calculate the minimum shanten number.

    Parameters:
        hand:
            Concealed tiles only, using MJAI notation.

        open_melds:
            Number of already completed melds
            (chi, pon, kan).

    Returns:
        -1: Complete hand
         0: Tenpai
         1: One-shanten
         2: Two-shanten
         ...
    """

    return calculate_shanten_by_type(hand, open_melds)["minimum"]


def calculate_shanten_by_type(
    hand: list[str],
    open_melds: int = 0,
) -> dict:
    """Return shanten independently for each legal winning shape.

    ``calculate_shanten`` remains the compatibility API and returns the
    minimum of these values.  Keeping the three values here prevents a
    Chiitoitsu/Kokushi route from being silently discarded when it is not
    the current minimum.
    """
    tiles = hand_to_34(hand)
    calculator = Shanten()
    regular = calculator.calculate_shanten_for_regular_hand(tiles)

    result = {
        "regular": {"available": True, "shanten": regular},
        "chiitoitsu": {"available": open_melds == 0,
                        "shanten": None},
        "kokushi": {"available": open_melds == 0,
                     "shanten": None},
    }
    if open_melds == 0:
        result["chiitoitsu"]["shanten"] = calculator.calculate_shanten_for_chiitoitsu_hand(tiles)
        result["kokushi"]["shanten"] = calculator.calculate_shanten_for_kokushi_hand(tiles)

    available = [result[name]["shanten"] for name in ("regular", "chiitoitsu", "kokushi")
                 if result[name]["available"]]
    minimum = min(available)
    result["minimum"] = minimum
    result["best_routes"] = [name for name, value in result.items()
                              if name != "minimum" and value["available"]
                              and value["shanten"] == minimum]
    return result
