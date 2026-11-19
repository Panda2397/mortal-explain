DRAGONS = {"P", "F", "C"}
WINDS = {"E", "S", "W", "N"}
SET_MELD_TYPES = {"pon", "daiminkan", "ankan", "kakan"}


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


def analyze_hand_yakuhai(
    concealed_tiles: list[str],
    melds: list[dict],
    bakaze: str | None,
    jikaze: str | None,
    known_public_tiles: list[str] | None = None,
) -> dict:
    """Report value-honor triplets/quads already present in the hand."""
    sets = []
    potential_sets = []
    known_public_tiles = known_public_tiles or []

    def reasons_for(tile: str) -> list[str]:
        reasons = []
        if tile in DRAGONS:
            reasons.append("dragon")
        if bakaze is not None and tile == bakaze:
            reasons.append("round_wind")
        if jikaze is not None and tile == jikaze:
            reasons.append("seat_wind")
        return reasons

    for tile in sorted(DRAGONS | WINDS):
        count = concealed_tiles.count(tile)
        reasons = reasons_for(tile)
        if count >= 3 and reasons:
            sets.append({
                "tile": tile,
                "source": "concealed",
                "tile_count": count,
                "reasons": reasons,
                "han": len(reasons),
            })
        elif count > 0 and reasons:
            public_count = sum(
                value.replace("r", "") == tile
                for value in known_public_tiles
            )
            copies_needed = 3 - count
            live_copies = max(0, 4 - count - public_count)
            potential_sets.append({
                "tile": tile,
                "concealed_count": count,
                "copies_needed": copies_needed,
                "live_copies": live_copies,
                "feasible_from_known_tiles": live_copies >= copies_needed,
                "promising": count == 2 and live_copies >= 1,
                "reasons": reasons,
                "han_if_completed": len(reasons),
            })

    for index, meld in enumerate(melds):
        tiles = meld.get("tiles") or []
        if meld.get("type") not in SET_MELD_TYPES or len(tiles) < 3:
            continue
        tile = tiles[0].replace("r", "")
        if any(value.replace("r", "") != tile for value in tiles):
            continue
        reasons = reasons_for(tile)
        if reasons:
            sets.append({
                "tile": tile,
                "source": "meld",
                "meld_index": index,
                "meld_type": meld.get("type"),
                "tile_count": len(tiles),
                "reasons": reasons,
                "han": len(reasons),
            })

    return {
        "has_yakuhai": bool(sets),
        "total_han": sum(value["han"] for value in sets),
        "sets": sets,
        "potential_sets": potential_sets,
        "wind_context_complete": bakaze is not None and jikaze is not None,
    }
