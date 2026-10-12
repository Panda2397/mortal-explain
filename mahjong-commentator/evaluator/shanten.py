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

    if tile in HONORS:
        return HONORS[tile]

    # Normalize red fives
    if tile.endswith("r"):
        tile = tile[:-1]

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
    Convert a list of MJAI tiles to a 34-element count array.
    """

    tiles = [0] * 34

    for tile in hand:
        index = tile_to_index(tile)
        tiles[index] += 1

    return tiles


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

    tiles = hand_to_34(hand)

    calculator = Shanten()

    # Standard hand
    standard = calculator.calculate_shanten_for_regular_hand(
        tiles
    )

    # Chiitoitsu and Kokushi require a closed hand
    if open_melds > 0:
        return standard

    chiitoitsu = calculator.calculate_shanten_for_chiitoitsu_hand(
        tiles
    )

    kokushi = calculator.calculate_shanten_for_kokushi_hand(
        tiles
    )

    return min(standard, chiitoitsu, kokushi)