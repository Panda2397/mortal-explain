
SUIT_ORDER = {"m": 0, "p": 1, "s": 2}
HONOR_ORDER = {
    "E": 0, "S": 1, "W": 2, "N": 3,
    "P": 4, "F": 5, "C": 6,
}

HONOR_NAMES = {
    "E": "東",
    "S": "南",
    "W": "西",
    "N": "北",
    "P": "白",
    "F": "發",
    "C": "中",
}

SUIT_NAMES = {
    "m": "萬",
    "p": "筒",
    "s": "索",
}


def tile_sort_key(tile: str):
    if tile in HONOR_ORDER:
        return (3, HONOR_ORDER[tile], 0)

    suit = tile[1]
    number = int(tile[0])

    # Red five beside regular five
    is_red = tile.endswith("r")

    return (
        SUIT_ORDER[suit],
        number,
        1 if is_red else 0,
    )


def sort_hand(hand: list[str]) -> list[str]:
    return sorted(hand, key=tile_sort_key)


def tile_to_chinese(tile: str) -> str:
    if tile in HONOR_NAMES:
        return HONOR_NAMES[tile]

    number = tile[0]
    suit = SUIT_NAMES[tile[1]]

    if tile.endswith("r"):
        return f"赤{number}{suit}"

    return f"{number}{suit}"


def format_hand(hand: list[str]) -> str:
    return " ".join(
        tile_to_chinese(tile)
        for tile in sort_hand(hand)
    )
