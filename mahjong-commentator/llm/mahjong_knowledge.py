MAHJONG_TERMINOLOGY = """
Use Traditional Chinese (Hong Kong).

Terms:
shanten = 向聽數
ukeire = 入章數
taatsu = 搭子
pair = 對子
block = 牌塊
han = 番
yaku = 役
yakuhai = 役牌
honor tiles = 字牌
dora = 寶牌
aka dora = 赤寶牌
dora indicator = 寶牌指示牌

Tile notation:
m = 萬, p = 筒, s = 索
E = 東風, S = 南風, W = 西風, N = 北風
P = 白板, F = 發財, C = 紅中
5mr = 赤五萬, 5pr = 赤五筒, 5sr = 赤五索

Use these terms consistently.
Never invent alternative translations.
like 聽牌狀態 as shanten
"""

MAHJONG_KNOWLEDGE = """
## Tile classification
- Winds: E, S, W, N.
- Dragons: P, F, C.
- Both are honor tiles (字牌).
- Dragons are never guest winds (客風).
- Guest winds are winds that are neither round
  wind nor seat wind.

## Yakuhai
- Dragon triplet/quad: 1 han.
- Round-wind triplet/quad: 1 han.
- Seat-wind triplet/quad: 1 han.
- Round wind = seat wind: 2 han for its triplet/quad.
- A single dragon or pair is not a completed yakuhai.

## Dora
- The next tile in sequence after a dora indicator is the dora.
- E.g., 3p indicator → 4p dora, 9p indicator → 1p dora, 4p indicator → 5p / 5pr dora.
- Dora provides bonus han, but is not a yaku.
- Each aka dora (5mr, 5pr, 5sr) contributes
  +1 bonus han in a qualifying winning hand.
- Discarding aka dora sacrifices that tile's
  potential +1 bonus han.
- Dora can stack with indicator dora.
- potential_yakuhai = 0 does NOT mean no dora value.

## Strategy
- Lower shanten is preferred in the evaluator's
  efficiency ranking.
- At equal shanten, higher ukeire is preferred.
- Higher ukeire means more remaining copies of
  immediately improving tiles, not higher win probability.
- Preserve valuable tiles when justified by evidence.
- Efficiency alone does not establish overall optimality.
- Defense, hand value, and future development also matter.
"""
