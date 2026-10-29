
OUTPUT_FORMAT = """
Write in Traditional Chinese (Hong Kong).
Use exactly these four sections.

### 1. 局面背景
場風：
自風：
局數：
本場：
巡目：
分數：
手牌：
摸牌：drawn_tile
副露：
牌型特徵：根據blocks解釋

### 2. 棄牌決策
實際棄牌：
牌效推薦：
推薦依據：根據blocks解釋

### 3. 兩種棄牌分析
**實際棄牌：[tile]**
牌效結果：
策略影響：根據blocks解釋

**替代棄牌：[tile] Use equally_efficient_discards**
牌效結果：
策略影響：根據blocks解釋

### 4. 綜合解釋
[One short paragraph comparing both choices.]

Rules:
- Preserve the exact section order and field names.
- Use only the supplied game state and evaluator results.
- Never invent hand tiles, numerical values, or probabilities.
- Lower shanten is preferred by this evaluator.
- Compare ukeire directly only at equal shanten.
- A discarded tile's dora value is a potential loss,
  not a benefit of discarding it.
- Distinguish winds, dragons, and yakuhai.
- If information is missing, write "未提供".
- Do not add extra sections or explanations.

EVIDENCE AND COMPARISON RULES:

1. When two discards have identical shanten and ukeire,
   classify them as equally efficient under the evaluator.
   Do not invent advantages to justify the recommended tile.

2. A taatsu must consist of two tiles from the same suit.
   Tiles from different suits cannot form a sequence.

3. Do not describe a hypothetical future tile as if it
   already exists in the hand.

4. Discarding tile X removes only X from the hand.
   Do not claim that discarding X removes another tile Y.

5. If the evaluator does not provide evidence for a
   strategic advantage, explicitly state that it is unknown.

6. A recommendation is not necessarily uniquely optimal.
   If multiple discards share the best score, report the tie.

7. Do not claim that discard A will lose A's 打點 unless the evaluator can explain what 打點 hand value it exactly loses.
"""
