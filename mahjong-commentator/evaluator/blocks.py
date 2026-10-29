from evaluator.shanten import hand_to_34, index_to_tile

HONORS = ["E", "S", "W", "N", "P", "F", "C"]

def analyze_blocks(
    hand: list[str],
    open_melds: int = 0,
    max_results: int = 5,
) -> list[dict]:
    """
    Enumerate and rank possible hand decompositions.

    hand:
        Concealed tiles in MJAI notation.

    open_melds:
        Number of completed melds already called.

    Returns:
        List of candidate block decompositions.
    """

    counts = hand_to_34(hand)
    decompositions = []

    def dfs(
        counts: list[int],
        melds: list[list[str]],
        taatsu: list[list[str]],
        pairs: list[list[str]],
        isolated: list[str],
    ):
        # Find first remaining tile
        i = next(
            (i for i, count in enumerate(counts) if count > 0),
            None,
        )

        if i is None:
            decompositions.append({
                "melds": [m.copy() for m in melds],
                "taatsu": [t.copy() for t in taatsu],
                "pairs": [p.copy() for p in pairs],
                "isolated": isolated.copy(),
            })
            return

        # 1. Triplet
        if counts[i] >= 3:
            counts[i] -= 3

            melds.append([index_to_tile(i)] * 3)

            dfs(counts, melds, taatsu, pairs, isolated)

            melds.pop()
            counts[i] += 3

        # 2. Sequence
        if (
            i < 27
            and i % 9 <= 6
            and counts[i + 1] > 0
            and counts[i + 2] > 0
        ):
            for j in (i, i + 1, i + 2):
                counts[j] -= 1

            melds.append([
                index_to_tile(i),
                index_to_tile(i + 1),
                index_to_tile(i + 2),
            ])

            dfs(counts, melds, taatsu, pairs, isolated)

            melds.pop()

            for j in (i, i + 1, i + 2):
                counts[j] += 1

        # 3. Pair
        if counts[i] >= 2:
            counts[i] -= 2

            pairs.append([index_to_tile(i)] * 2)

            dfs(counts, melds, taatsu, pairs, isolated)

            pairs.pop()
            counts[i] += 2

        # 4. Consecutive taatsu
        if (
            i < 27
            and i % 9 <= 7
            and counts[i + 1] > 0
        ):
            counts[i] -= 1
            counts[i + 1] -= 1

            taatsu.append([
                index_to_tile(i),
                index_to_tile(i + 1),
            ])

            dfs(counts, melds, taatsu, pairs, isolated)

            taatsu.pop()
            counts[i] += 1
            counts[i + 1] += 1

        # 5. Gapped taatsu
        if (
            i < 27
            and i % 9 <= 6
            and counts[i + 2] > 0
        ):
            counts[i] -= 1
            counts[i + 2] -= 1

            taatsu.append([
                index_to_tile(i),
                index_to_tile(i + 2),
            ])

            dfs(counts, melds, taatsu, pairs, isolated)

            taatsu.pop()
            counts[i] += 1
            counts[i + 2] += 1

        # 6. Isolated tile
        counts[i] -= 1
        isolated.append(index_to_tile(i))

        dfs(counts, melds, taatsu, pairs, isolated)

        isolated.pop()
        counts[i] += 1

    dfs(counts, [], [], [], [])

    def rank(decomposition):
        meld_count = len(decomposition["melds"]) + open_melds
        pair_count = len(decomposition["pairs"])
        taatsu_count = len(decomposition["taatsu"])

        # Standard-hand structural shanten:
        # choose one pair as the head; other pairs may serve as taatsu.
        head = 1 if pair_count else 0
        effective_taatsu = taatsu_count + max(0, pair_count - head)

        # Only 4 meld slots can be used.
        usable_taatsu = min(
            effective_taatsu,
            max(0, 4 - meld_count),
        )

        shanten = (
            8
            - 2 * meld_count
            - usable_taatsu
            - head
        )

        useful_blocks = min(
            5,
            meld_count + usable_taatsu + head
        )

        return (
            shanten,
            -useful_blocks,
            len(decomposition["isolated"]),
        )

    decompositions.sort(key=rank)

    results = []

    for decomposition in decompositions[:max_results]:
        shanten, neg_blocks, _ = rank(decomposition)

        results.append({
            **decomposition,
            "open_melds": open_melds,
            "block_count": -neg_blocks,
            "structural_shanten": shanten,
        })

    return results