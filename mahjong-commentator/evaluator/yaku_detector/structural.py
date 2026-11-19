"""Measured structural distances for the first two yaku-search groups."""

from collections import Counter
from functools import lru_cache

from evaluator.shanten import calculate_shanten_by_type, index_to_tile, tile_to_index
from evaluator.yaku_detector.models import YakuContext
from evaluator.yaku_detector.scoring import winning_methods
from evaluator.yaku_detector.context import known_tile_counts


SUITS = "mps"


def _duplicate_sequence_requirements():
    patterns = tuple(
        Counter({f"{rank}{suit}": 2 for rank in range(start, start + 3)})
        for suit in SUITS
        for start in range(1, 8)
    )
    pairs = []
    for first_index, first in enumerate(patterns):
        # Ryanpeikou may use the same sequence twice in both duplicated
        # sequence groups (four copies of each of the three tile types).
        for second in patterns[first_index:]:
            required = first + second
            if all(value <= 4 for value in required.values()):
                pairs.append(required)
    return patterns, tuple(pairs)


DUPLICATE_SEQUENCE_PATTERNS, RYANPEIKOU_PATTERNS = _duplicate_sequence_requirements()


def _regular(ctx: YakuContext, tiles: tuple[str, ...] | None = None) -> int:
    hand = list(tiles if tiles is not None else ctx.concealed_tiles)
    return calculate_shanten_by_type(hand, len(ctx.melds))["regular"]["shanten"]


def _outside(tile: str) -> bool:
    index = tile_to_index(tile)
    return index >= 27 or index % 9 in (0, 8)


def _simple(tile: str) -> bool:
    index = tile_to_index(tile)
    return index < 27 and index % 9 not in (0, 8)


def _meld_sequence(meld) -> tuple[str, int] | None:
    ids = sorted(tile_to_index(tile) for tile in meld.tiles)
    if len(ids) != 3 or ids[0] >= 27 or ids != list(range(ids[0], ids[0] + 3)):
        return None
    return SUITS[ids[0] // 9], ids[0] % 9


def _blocker(kind, reason, *, severity="irreversible", tile=None, meld_index=None):
    value = {"type": kind, "severity": severity, "reason": reason}
    if tile is not None:
        value["tile"] = tile
    if meld_index is not None:
        value["meld_index"] = meld_index
    return value


def _known_counts_for_hand(
    ctx: YakuContext,
    hand: tuple[str, ...],
    extra_visible: tuple[str, ...] = (),
) -> Counter:
    """Count unavailable copies for a hypothetical concealed hand."""
    concealed = Counter(tile_to_index(tile) for tile in hand)
    public = Counter(
        tile_to_index(tile) for tile in ctx.visible_tiles + extra_visible
    )
    fixed = Counter(
        tile_to_index(tile) for meld in ctx.melds for tile in meld.tiles
    )
    result = concealed.copy()
    for index in range(34):
        result[index] += max(public[index], fixed[index])
    return result


def _live_winning_waits(
    ctx: YakuContext,
    route: str,
    hand: tuple[str, ...],
    extra_visible: tuple[str, ...] = (),
) -> dict[str, dict]:
    """Return scorer-valid winning tiles that still have a live copy."""
    known = _known_counts_for_hand(ctx, hand, extra_visible)
    waits = {}
    for index in range(34):
        remaining = 4 - known[index]
        if remaining <= 0:
            continue
        tile = index_to_tile(index)
        methods = winning_methods(ctx, route, tile, concealed=hand)
        if methods:
            waits[tile] = {"remaining": remaining, "outcomes": methods}
    return waits


def _fixed_set_tile(meld) -> str | None:
    if meld.type not in {"pon", "daiminkan", "ankan", "kakan"}:
        return None
    return meld.tiles[0][:-1] if meld.tiles[0].endswith("r") else meld.tiles[0]


def _has_pinfu_wait(ctx: YakuContext, hand: tuple[str, ...]) -> bool:
    """Use the installed scorer to validate at least one genuine Pinfu wait."""
    if ctx.melds:
        return False
    counts = Counter(tile_to_index(tile) for tile in hand)
    for win_index in range(34):
        if counts[win_index] >= 4:
            continue
        if winning_methods(ctx, "pinfu", index_to_tile(win_index), hand):
            return True
    return False


def _compute_route_distances(
    ctx: YakuContext,
    tiles: tuple[str, ...] | None = None,
    requested: frozenset[str] | None = None,
) -> dict[str, dict]:
    """Return route distance before availability-based ukeire is attached."""
    hand = tiles if tiles is not None else ctx.concealed_tiles
    counts = Counter(tile[:-1] if tile.endswith("r") else tile for tile in hand)
    regular = _regular(ctx, hand)
    by_type = calculate_shanten_by_type(list(hand), len(ctx.melds))
    chiitoitsu = (
        by_type["chiitoitsu"]["shanten"]
        if by_type["chiitoitsu"]["available"] else None
    )
    routes: dict[str, dict] = {}

    def wanted(name: str) -> bool:
        return requested is None or name in requested

    def add(
        name, value, measurement, feasibility="possible", blockers=(),
        *, route_state="none", validation="unvalidated",
    ):
        if not wanted(name):
            return
        routes[name] = {
            "shanten": {"value": value, "measurement": measurement},
            "ukeire": {},
            "feasibility": feasibility,
            "yaku_blockers": list(blockers),
            "route_state": route_state,
            "proof": {"distance": measurement, "validation": validation},
            "outcome_scope": {"ron": "unknown", "tsumo": "unknown"},
            "availability": "unknown",
            "guarantee": "none",
            "legacy_feasibility": (
                "confirmed" if route_state == "component_present" else feasibility
            ),
            "ukeire_kind": "none",
            "ukeire_witnesses": {},
            "estimated_improving_draws": {},
            "tenpai_quality": {
                "status": "not_reached",
                "lookahead_depth": 0,
                "tenpai_endpoint_count": 0,
                "distinct_winning_tiles": [],
                "best_wait_type_count": 0,
                "best_live_wait_copies": 0,
            },
        }

    # Tile-domain routes: max() is a safe lower bound because shape and domain
    # requirements may interact and require additional replacements.
    tanyao_bad = [tile for tile in hand if not _simple(tile)]
    tanyao_fixed = [m for m in ctx.melds if any(not _simple(t) for t in m.tiles)]
    if tanyao_fixed or (ctx.menzen is False and not ctx.rules.open_tanyao):
        blockers = [_blocker("fixed_meld", "contains_terminal_or_honor", meld_index=m.source_index)
                    for m in tanyao_fixed]
        if ctx.menzen is False and not ctx.rules.open_tanyao:
            blockers.append(_blocker("rule_disabled", "open_tanyao_disabled"))
        add("tanyao", None, "exact", "impossible", blockers)
    else:
        blockers = [_blocker("concealed_tile", "terminal_or_honor", severity="removable", tile=t)
                    for t in tanyao_bad]
        shape_floor = min(regular, chiitoitsu) if chiitoitsu is not None else regular
        add("tanyao", max(shape_floor, len(tanyao_bad)), "lower_bound", blockers=blockers)

    all_tiles = list(hand) + [t for m in ctx.melds for t in m.tiles]
    for suit in SUITS:
        off_honitsu = [t for t in hand if t[-1:] in SUITS and t[1] != suit]
        fixed_off = [m for m in ctx.melds if any(t[-1:] in SUITS and t[1] != suit for t in m.tiles)]
        blockers = [_blocker("fixed_meld", "off_suit", meld_index=m.source_index) for m in fixed_off]
        shape_floor = min(regular, chiitoitsu) if chiitoitsu is not None else regular
        has_honor = any(tile_to_index(t) >= 27 for t in all_tiles)
        honitsu_floor = max(shape_floor, len(off_honitsu), 0 if has_honor else 1)
        add(f"honitsu_{suit}", None if fixed_off else honitsu_floor,
            "lower_bound", "impossible" if fixed_off else "possible", blockers)
        off_chinitsu = [t for t in hand if t[-1:] not in SUITS or t[1] != suit]
        fixed_chin = [m for m in ctx.melds if any(t[-1:] not in SUITS or t[1] != suit for t in m.tiles)]
        blockers = [_blocker("fixed_meld", "off_suit_or_honor", meld_index=m.source_index) for m in fixed_chin]
        add(f"chinitsu_{suit}", None if fixed_chin else max(shape_floor, len(off_chinitsu)),
            "lower_bound", "impossible" if fixed_chin else "possible", blockers)

    fixed_chi = [m for m in ctx.melds if _meld_sequence(m) is not None]
    triplets = sum(1 for m in ctx.melds if _meld_sequence(m) is None)
    triplets += sum(1 for count in counts.values() if count >= 3)
    pairs = sum(1 for count in counts.values() if count == 2)
    if fixed_chi:
        toitoi_distance = None
        add("toitoi", None, "exact", "impossible",
            [_blocker("fixed_meld", "fixed_sequence", meld_index=m.source_index) for m in fixed_chi])
    else:
        head = int(pairs > 0)
        progress = 2 * triplets + head + min(max(0, pairs - head), max(0, 4 - triplets))
        toitoi_distance = max(-1, 8 - progress)
        add("toitoi", toitoi_distance, "exact")

    concealed_triplets = sum(1 for count in counts.values() if count >= 3)
    concealed_triplets += sum(1 for meld in ctx.melds if meld.type == "ankan")
    open_set_melds = [
        meld for meld in ctx.melds
        if meld.type in {"pon", "daiminkan", "kakan"} and meld.is_open
    ]
    if sum(1 for meld in ctx.melds if meld.is_open) > 1:
        add("sanankou", None, "exact", "impossible", [
            _blocker("fixed_meld_capacity", "fewer_than_three_concealed_meld_slots")
        ])
    else:
        fixed_ankans = sum(1 for meld in ctx.melds if meld.type == "ankan")
        triplets_needed = max(0, 3 - fixed_ankans)
        # Before Sanankou tenpai, the concealed hand must contain three
        # triplets or be one tile short of the last triplet for a tsumo
        # completion. A pair costs one added copy, a singleton costs two,
        # and an absent type costs three. The previous formula treated every
        # pair as completed progress and could report one-shanten with no
        # concealed triplets at all.
        triplet_deficits = sorted(
            max(0, 3 - counts[index_to_tile(index)])
            for index in range(34)
        )
        triplet_draw_floor = max(
            0, sum(triplet_deficits[:triplets_needed]) - 1
        )
        sanankou_distance = (
            -1 if regular == -1 and concealed_triplets >= 3
            else max(regular, triplet_draw_floor)
        )
        add(
            "sanankou", sanankou_distance, "lower_bound", "possible",
            route_state=("component_present" if concealed_triplets >= 3 else "none"),
            validation=("structural_witness" if concealed_triplets >= 3 else "unvalidated"),
        )

    if ctx.menzen is False or open_set_melds:
        add("suuankou", None, "exact", "impossible",
            [_blocker("open_hand", "closed_only")])
    else:
        # With no open melds, Suuankou needs the same four-triplets-plus-pair
        # structure as Toitoi. Keeping this exact distance prevents ordinary
        # sequence improvements from being counted as Suuankou ukeire.
        add("suuankou", toitoi_distance, "exact")

    free_group_slots = max(0, 4 - len(ctx.melds))
    sanshoku_doukou_values = []
    for rank in range(1, 10):
        fixed_matches = sum(
            1 for meld in ctx.melds
            if meld.type in {"pon", "daiminkan", "ankan", "kakan"}
            and tile_to_index(meld.tiles[0]) < 27
            and tile_to_index(meld.tiles[0]) % 9 == rank - 1
        )
        if 3 - fixed_matches > free_group_slots:
            continue
        missing = sum(
            max(0, 3 - counts[f"{rank}{suit}"])
            for suit in SUITS
            if not any(
                meld.type in {"pon", "daiminkan", "ankan", "kakan"}
                and all(tile_to_index(tile) % 9 == rank - 1 for tile in meld.tiles)
                and tile_to_index(meld.tiles[0]) // 9 == SUITS.index(suit)
                for meld in ctx.melds
            )
        )
        sanshoku_doukou_values.append(max(regular, max(0, missing - 1)))
    add(
        "sanshoku_doukou",
        min(sanshoku_doukou_values) if sanshoku_doukou_values else None,
        "lower_bound" if sanshoku_doukou_values else "exact",
        "possible" if sanshoku_doukou_values else "impossible",
        [] if sanshoku_doukou_values else [
            _blocker("fixed_meld_capacity", "insufficient_triplet_slots")
        ],
    )

    add("chiitoitsu", by_type["chiitoitsu"]["shanten"], "exact",
        "possible" if by_type["chiitoitsu"]["available"] else "impossible",
        [] if by_type["chiitoitsu"]["available"] else [_blocker("open_hand", "closed_only")])
    add("kokushi", by_type["kokushi"]["shanten"], "exact",
        "possible" if by_type["kokushi"]["available"] else "impossible",
        [] if by_type["kokushi"]["available"] else [_blocker("open_hand", "closed_only")])

    # Required-sequence lower bounds.
    fixed_sequences = {_meld_sequence(m) for m in ctx.melds if _meld_sequence(m) is not None}
    ittsu_values = []
    for suit in SUITS:
        fixed_matches = sum(1 for sequence in fixed_sequences
                            if sequence in {(suit, 0), (suit, 3), (suit, 6)})
        if 3 - fixed_matches > free_group_slots:
            continue
        missing = 0
        for rank in range(1, 10):
            if counts[f"{rank}{suit}"] == 0 and (suit, ((rank - 1) // 3) * 3) not in fixed_sequences:
                missing += 1
        ittsu_values.append(max(regular, max(0, missing - 1)))
    add(
        "ittsu", min(ittsu_values) if ittsu_values else None,
        "lower_bound" if ittsu_values else "exact",
        "possible" if ittsu_values else "impossible",
        [] if ittsu_values else [
            _blocker("fixed_meld_capacity", "insufficient_sequence_slots")
        ],
    )

    sanshoku_values = []
    for start in range(7):
        fixed_matches = sum(1 for suit in SUITS if (suit, start) in fixed_sequences)
        if 3 - fixed_matches > free_group_slots:
            continue
        missing = 0
        for suit in SUITS:
            if (suit, start) in fixed_sequences:
                continue
            missing += sum(counts[f"{rank}{suit}"] == 0 for rank in range(start + 1, start + 4))
        sanshoku_values.append(max(regular, max(0, missing - 1)))
    add(
        "sanshoku_doujun", min(sanshoku_values) if sanshoku_values else None,
        "lower_bound" if sanshoku_values else "exact",
        "possible" if sanshoku_values else "impossible",
        [] if sanshoku_values else [
            _blocker("fixed_meld_capacity", "insufficient_sequence_slots")
        ],
    )

    if ctx.menzen is False:
        closed_blocker = [_blocker("open_hand", "closed_only")]
        add("iipeikou", None, "exact", "impossible", closed_blocker)
        add("ryanpeikou", None, "exact", "impossible", closed_blocker)
    elif free_group_slots < 2:
        blocker = [_blocker("fixed_meld_capacity", "fewer_than_two_sequence_slots")]
        add("iipeikou", None, "exact", "impossible", blocker)
        add("ryanpeikou", None, "exact", "impossible", blocker)
    else:
        if wanted("iipeikou"):
            iipeikou_missing = min(sum(
                max(0, need - counts[tile]) for tile, need in required.items()
            ) for required in DUPLICATE_SEQUENCE_PATTERNS)
            # Pattern completion and completion of the other hand groups can
            # compete for different draws. Treat their combined cost as a
            # heuristic rather than the previous unsafe lower bound.
            add("iipeikou", regular + max(0, iipeikou_missing - 1), "heuristic")
        if wanted("ryanpeikou"):
            if ctx.melds or free_group_slots < 4:
                add("ryanpeikou", None, "exact", "impossible", [
                    _blocker("fixed_meld_capacity", "ryanpeikou_requires_four_sequence_slots")
                ])
            else:
                ryanpeikou_missing = min(sum(
                    max(0, need - counts[tile]) for tile, need in required.items()
                ) for required in RYANPEIKOU_PATTERNS)
                add("ryanpeikou", regular + max(0, ryanpeikou_missing - 1),
                    "heuristic")

    for name, allow_honors in (("chanta", True), ("junchan", False)):
        bad_fixed = []
        for meld in ctx.melds:
            values = [tile_to_index(t) for t in meld.tiles]
            has_terminal = any(v < 27 and v % 9 in (0, 8) for v in values)
            has_honor = any(v >= 27 for v in values)
            if (has_honor and not allow_honors) or not (has_terminal or (allow_honors and has_honor)):
                bad_fixed.append(meld)
        # Chanta sequences can only be 123/789. Therefore every concealed
        # 4/5/6 is necessarily removable; Junchan must also remove honors.
        incompatible = [
            tile for tile in hand
            if (
                tile_to_index(tile) < 27
                and tile_to_index(tile) % 9 in (3, 4, 5)
            ) or (not allow_honors and tile_to_index(tile) >= 27)
        ]
        blockers = [
            _blocker("fixed_meld", "incompatible_group", meld_index=m.source_index)
            for m in bad_fixed
        ] + [
            _blocker("concealed_tile", "incompatible_with_outside_hand",
                     severity="removable", tile=tile)
            for tile in incompatible
        ]
        outside_sequences = sum(
            1 for suit, start in fixed_sequences if start in (0, 6)
        )
        concealed_sequence_missing = min(
            sum(counts[f"{rank}{suit}"] == 0 for rank in ranks)
            for suit in SUITS for ranks in ((1, 2, 3), (7, 8, 9))
        )
        sequence_floor = 0 if outside_sequences else max(0, concealed_sequence_missing - 1)
        honor_floor = 0
        if name == "chanta" and not any(tile_to_index(t) >= 27 for t in all_tiles):
            honor_floor = 1
        add(name, None if bad_fixed else max(
            regular, len(incompatible), sequence_floor, honor_floor
        ), "lower_bound",
            "impossible" if bad_fixed else "possible",
            blockers)

    honroutou_bad = [t for t in hand if not _outside(t)]
    fixed_bad = [m for m in ctx.melds if any(not _outside(t) for t in m.tiles)]
    honroutou_floor = min(regular, chiitoitsu) if chiitoitsu is not None else regular
    add("honroutou", None if fixed_bad else max(honroutou_floor, len(honroutou_bad)), "lower_bound",
        "impossible" if fixed_bad else "possible",
        [_blocker("fixed_meld", "contains_simple", meld_index=m.source_index) for m in fixed_bad])

    # Honor/terminal/green yakuman support regular and Chiitoitsu shapes.
    domain_routes = {
        "tsuuiisou": lambda tile: tile_to_index(tile) >= 27,
        "chinroutou": lambda tile: (
            tile_to_index(tile) < 27 and tile_to_index(tile) % 9 in (0, 8)
        ),
        "ryuuiisou": lambda tile: (
            (tile[:-1] if tile.endswith("r") else tile)
            in {"2s", "3s", "4s", "6s", "8s", "F"}
        ),
    }
    for name, allowed in domain_routes.items():
        bad = [tile for tile in hand if not allowed(tile)]
        fixed_bad = [meld for meld in ctx.melds if any(
            not allowed(tile) for tile in meld.tiles
        )]
        # Only the seven honor types can form a seven-distinct-pairs hand.
        # Terminals and green tiles each provide only six distinct types.
        domain_shape_floor = honroutou_floor if name == "tsuuiisou" else regular
        add(
            name,
            None if fixed_bad else max(domain_shape_floor, len(bad)),
            "lower_bound",
            "impossible" if fixed_bad else "possible",
            [_blocker("fixed_meld", "tile_outside_yaku_domain", meld_index=m.source_index)
             for m in fixed_bad],
        )

    fixed_sets = Counter(
        tile for meld in ctx.melds
        if (tile := _fixed_set_tile(meld)) is not None
    )

    def required_set_route(name, patterns):
        values = []
        relevant_tiles = {
            tile for triplet_tiles, pair_tile in patterns
            for tile in (*triplet_tiles, *((pair_tile,) if pair_tile else ()))
        }
        for triplet_tiles, pair_tile in patterns:
            if any(
                fixed_sets[tile] and tile in relevant_tiles and tile not in triplet_tiles
                for tile in fixed_sets
            ):
                continue
            fixed_matches = sum(1 for tile in triplet_tiles if fixed_sets[tile])
            if len(triplet_tiles) - fixed_matches > free_group_slots:
                continue
            missing = sum(
                0 if fixed_sets[tile] else max(0, 3 - counts[tile])
                for tile in triplet_tiles
            )
            if pair_tile is not None:
                if fixed_sets[pair_tile]:
                    continue
                missing += max(0, 2 - counts[pair_tile])
            values.append(max(regular, max(0, missing - 1)))
        add(
            name, min(values) if values else None,
            "lower_bound" if values else "exact",
            "possible" if values else "impossible",
            [] if values else [_blocker(
                "fixed_meld_capacity", "required_honor_groups_cannot_fit"
            )],
        )

    dragons = ("P", "F", "C")
    required_set_route("daisangen", [(dragons, None)])
    required_set_route("shousangen", [
        (tuple(tile for tile in dragons if tile != pair), pair)
        for pair in dragons
    ])
    winds = ("E", "S", "W", "N")
    required_set_route("daisuushii", [(winds, None)])
    required_set_route("shousuushii", [
        (tuple(tile for tile in winds if tile != pair), pair)
        for pair in winds
    ])

    fixed_kans = sum(
        1 for meld in ctx.melds if meld.type in {"daiminkan", "ankan", "kakan"}
    )
    potential_quads = fixed_kans + sum(
        1 for tile, count in counts.items() if count == 4
        and not fixed_sets[tile]
    )
    for name, required in (("sankantsu", 3), ("suukantsu", 4)):
        capacity = fixed_kans + free_group_slots
        incompatible = (
            capacity < required
            or (name == "suukantsu" and any(
                meld.type not in {"daiminkan", "ankan", "kakan"}
                for meld in ctx.melds
            ))
        )
        add(
            name,
            None if incompatible else max(regular, required - potential_quads),
            "exact" if incompatible else "heuristic",
            "impossible" if incompatible else "possible",
            [_blocker("fixed_meld_capacity", "insufficient_kan_slots")]
            if incompatible else [],
        )

    # Chuuren is closed, one-suit, and requires 1112345678999 plus one extra
    # suited tile on completion. This is a safe lower bound to its tenpai
    # family; completion is still scorer-validated before yaku-tenpai.
    if wanted("chuuren_poutou"):
        if ctx.menzen is False or ctx.melds:
            add("chuuren_poutou", None, "exact", "impossible", [
                _blocker("open_hand", "closed_only")
            ])
        else:
            chuuren_values = []
            for suit in SUITS:
                off_suit = sum(1 for tile in hand if tile[-1:] != suit)
                required_counts = {f"{rank}{suit}": (3 if rank in (1, 9) else 1)
                                   for rank in range(1, 10)}
                missing = sum(max(0, need - counts[tile])
                              for tile, need in required_counts.items())
                chuuren_values.append(max(regular, off_suit, max(0, missing - 1)))
            add("chuuren_poutou", min(chuuren_values), "lower_bound")

    if not wanted("pinfu"):
        return routes
    if ctx.menzen is False or ctx.melds:
        add("pinfu", None, "exact", "impossible", [_blocker("open_hand", "closed_only")])
    elif regular == 0 and not _has_pinfu_wait(ctx, hand):
        add("pinfu", None, "exact", "impossible", [_blocker("wait_shape", "no_valid_pinfu_wait")])
    elif regular == 0:
        add("pinfu", 0, "exact")
    else:
        value_honors = {"P", "F", "C"}
        if ctx.round_wind:
            value_honors.add(ctx.round_wind)
        if ctx.seat_wind:
            value_honors.add(ctx.seat_wind)
        incompatible = [tile for tile in hand if tile in value_honors]
        # Existing triplet-shaped groups are not automatically sequences.
        # This is decomposition-sensitive, so expose a conservative heuristic
        # instead of claiming the ordinary shanten is a Pinfu lower bound.
        triplet_pressure = sum(1 for count in counts.values() if count >= 3)
        add("pinfu", max(regular, len(incompatible), triplet_pressure),
            "heuristic", blockers=[
            _blocker("concealed_tile", "value_honor_cannot_be_pinfu_pair",
                     severity="removable", tile=tile)
            for tile in incompatible
        ] + [
            _blocker("concealed_group", "triplet_must_be_restructured",
                     severity="removable", tile=tile)
            for tile, count in counts.items() if count >= 3
        ])
    return routes


def _canonical_hand(tiles: tuple[str, ...]) -> tuple[str, ...]:
    """Canonical structural hand key; red identity is irrelevant to yaku shape."""
    return tuple(sorted(
        (index_to_tile(tile_to_index(tile)) for tile in tiles),
        key=tile_to_index,
    ))


@lru_cache(maxsize=32768)
def _cached_route_metrics(
    hand: tuple[str, ...],
    melds: tuple,
    round_wind: str | None,
    seat_wind: str | None,
    rules,
    menzen: bool | None,
    requested: tuple[str, ...],
) -> tuple[tuple[str, int | None], ...]:
    """Cache compact route values shared by all candidates in a game.

    Visibility is intentionally absent: structural distance is independent of
    live-copy availability. Availability is applied by ``attach_ukeire``.
    """
    synthetic = YakuContext(
        concealed_tiles=hand,
        melds=melds,
        visible_tiles=(),
        round_wind=round_wind,
        seat_wind=seat_wind,
        rules=rules,
        melds_complete=True,
        menzen=menzen,
        declared_meld_count=len(melds),
    )
    routes = _compute_route_distances(synthetic, hand, frozenset(requested))
    return tuple(
        (name, route["shanten"]["value"])
        for name, route in routes.items()
    )


def _route_metric_values(
    ctx: YakuContext, tiles: tuple[str, ...], requested: set[str]
) -> dict[str, int | None]:
    return dict(_cached_route_metrics(
        _canonical_hand(tiles), ctx.melds, ctx.round_wind, ctx.seat_wind,
        ctx.rules, ctx.menzen, tuple(sorted(requested)),
    ))


def route_distances(ctx: YakuContext, tiles: tuple[str, ...] | None = None) -> dict[str, dict]:
    """Return independent route objects; callers may safely enrich them."""
    hand = tiles if tiles is not None else ctx.concealed_tiles
    # Base route objects are built once per candidate. Compact cached metrics
    # are used for the thousands of draw-discard transition checks below.
    return _compute_route_distances(ctx, _canonical_hand(hand))


def attach_ukeire(
    ctx: YakuContext,
    routes: dict[str, dict],
    *,
    include_transitions: bool = True,
) -> dict[str, dict]:
    """Attach draws whose best post-draw discard lowers the same measurement."""
    known = known_tile_counts(ctx)
    endpoint_hands: dict[str, set[tuple[str, ...]]] = {
        name: set() for name in routes
    }
    endpoint_waits: dict[str, list[dict[str, dict]]] = {
        name: [] for name in routes
    }
    selected = {name for name, route in routes.items()
                if route["feasibility"] != "impossible"
                and route["shanten"]["value"] is not None
                and route["shanten"]["value"] <= 3}
    for index in range(34):
        remaining = 4 - known[index]
        if remaining <= 0:
            continue
        draw = index_to_tile(index)
        fourteen = ctx.concealed_tiles + (draw,)
        best = {name: routes[name]["shanten"]["value"] for name in selected}
        best_discards = {name: None for name in selected}
        best_transitions = {name: [] for name in selected}
        zero_routes = {name for name in selected if best[name] == 0}
        for name in zero_routes:
            methods = winning_methods(ctx, name, draw)
            if methods:
                routes[name]["ukeire"][draw] = remaining
                routes[name]["ukeire_kind"] = "scorer_validated"
                routes[name]["ukeire_witnesses"][draw] = {
                    "draw": draw,
                    "post_draw_hand": list(fourteen),
                    "winning_outcomes": methods,
                    "validation": "scorer_validated",
                }
                routes[name]["route_state"] = "yaku_tenpai"
                routes[name]["legacy_feasibility"] = "confirmed"
                routes[name]["proof"]["validation"] = "scorer_validated"
                routes[name]["availability"] = "live"
                routes[name]["guarantee"] = "some_live_wins"
                routes[name]["outcome_scope"] = {
                    "ron": "validated" if any(m["method"] == "ron" for m in methods) else "invalid",
                    "tsumo": "validated" if any(m["method"] == "tsumo" for m in methods) else "invalid",
                }
                endpoint_hands[name].add(tuple(ctx.concealed_tiles))
        if not include_transitions:
            continue
        seen_discards = set()
        for discard_index in range(len(fourteen)):
            discard_type = tile_to_index(fourteen[discard_index])
            if discard_type in seen_discards:
                continue
            seen_discards.add(discard_type)
            after = fourteen[:discard_index] + fourteen[discard_index + 1:]
            measured = _route_metric_values(ctx, after, selected)
            for name in selected:
                value = measured[name]
                if value is not None and value < best[name]:
                    best[name] = value
                    best_discards[name] = fourteen[discard_index]
                    best_transitions[name] = [(fourteen[discard_index], after)]
                elif value is not None and value == best[name] \
                        and value < routes[name]["shanten"]["value"]:
                    best_transitions[name].append((fourteen[discard_index], after))
        for name in selected:
            if name not in zero_routes and best[name] < routes[name]["shanten"]["value"]:
                live_endpoint = None
                live_waits = {}
                if best[name] == 0:
                    for endpoint_discard, after in best_transitions[name]:
                        waits = _live_winning_waits(
                            ctx, name, after, (endpoint_discard,)
                        )
                        if waits:
                            live_endpoint = after
                            live_waits = waits
                            best_discards[name] = endpoint_discard
                            break

                    # A one-shanten route improvement is actionable only when
                    # the resulting yaku-tenpai has a live scorer-valid wait.
                    if routes[name]["shanten"]["value"] == 1 and not live_waits:
                        continue

                witness = {
                    "draw": draw,
                    "discard": best_discards[name],
                    "yaku_shanten_after": best[name],
                    "validation": "exact_transition" if (
                        routes[name]["shanten"]["measurement"] == "exact"
                    ) else "estimated_metric_improvement",
                }
                if live_waits:
                    witness["tenpai_waits"] = {
                        tile: value["remaining"]
                        for tile, value in live_waits.items()
                    }
                    canonical = _canonical_hand(live_endpoint)
                    if canonical not in endpoint_hands[name]:
                        endpoint_hands[name].add(canonical)
                        endpoint_waits[name].append(live_waits)
                if routes[name]["shanten"]["measurement"] == "exact":
                    routes[name]["ukeire"][draw] = remaining
                    routes[name]["ukeire_kind"] = "exact_transition"
                    routes[name]["ukeire_witnesses"][draw] = witness
                else:
                    routes[name]["estimated_improving_draws"][draw] = remaining
                    routes[name]["ukeire_witnesses"][draw] = witness

    for name in selected:
        route = routes[name]
        value = route["shanten"]["value"]
        waits = endpoint_waits[name]
        if value == 0:
            current_waits = {
                tile: {
                    "remaining": count,
                    "outcomes": route["ukeire_witnesses"][tile]["winning_outcomes"],
                }
                for tile, count in route["ukeire"].items()
                if tile in route["ukeire_witnesses"]
            }
            if current_waits:
                waits = [current_waits]
        winning_tiles = sorted({tile for item in waits for tile in item})
        route["tenpai_quality"] = {
            "status": (
                "validated_live" if waits else
                "dead" if value in {0, 1}
                and route["shanten"]["measurement"] == "exact" else
                "projected" if value in {1, 2} else "not_reached"
            ),
            "lookahead_depth": 0 if value == 0 else (1 if value in {1, 2} else 0),
            "tenpai_endpoint_count": len(endpoint_hands[name]) if waits else 0,
            "distinct_winning_tiles": winning_tiles,
            "best_wait_type_count": max((len(item) for item in waits), default=0),
            "best_live_wait_copies": max(
                (sum(value["remaining"] for value in item.values()) for item in waits),
                default=0,
            ),
        }
        if value == 0 and not waits \
                and route["shanten"]["measurement"] == "exact":
            route["availability"] = "dead"
            route["guarantee"] = "no_live_wins"
            route["feasibility"] = "impossible"
            route["legacy_feasibility"] = "impossible"
            route["yaku_blockers"].append(_blocker(
                "tile_availability", "all_scorer_validated_waits_exhausted"
            ))
    return routes
