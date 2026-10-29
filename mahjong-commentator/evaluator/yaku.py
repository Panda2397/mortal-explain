DRAGONS = {"P", "F", "C"}
WINDS = {"E", "S", "W", "N"}


TILE_NAMES = {
    "E": "東風",
    "S": "南風",
    "W": "西風",
    "N": "北風",
    "P": "白板",
    "F": "發財",
    "C": "紅中",
}

def analyze_honor_tile(
    tile: str,
    bakaze: str,
    jikaze: str,
) -> dict:

    if tile not in DRAGONS | WINDS:
        return {
            "tile": tile,
            "is_honor": False,
            "is_yakuhai": False,
            "yakuhai_reasons": [],
            "potential_yakuhai_han": 0,
        }

    reasons = []

    if tile in DRAGONS:
        reasons.append("dragon")

    if tile == bakaze:
        reasons.append("round_wind")

    if tile == jikaze:
        reasons.append("seat_wind")

    return {
            "tile": tile,
            "name": TILE_NAMES.get(tile, tile),
            "is_honor": tile in DRAGONS | WINDS,
            "is_yakuhai": bool(reasons),
            "yakuhai_reasons": reasons,
            "potential_yakuhai_han": len(reasons),
        }