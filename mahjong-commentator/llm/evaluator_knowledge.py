
EVALUATOR_KNOWLEDGE = """
You are given structured evidence from a Riichi Mahjong
discard evaluator.

The following definitions are authoritative.

## Tile notation

m = 萬子
p = 筒子
s = 索子

E = 東風
S = 南風
W = 西風
N = 北風
P = 白板
F = 發財
C = 紅中

5mr = 赤五萬
5pr = 赤五筒
5sr = 赤五索

Red fives are aka dora (赤寶牌).
They are normal five tiles with additional dora value,
not separate tile types for shanten calculations.

## Evaluation fields

actual_discard:
The tile actually discarded by the player.

best_efficiency_discard:
The evaluator's preferred discard under its ranking
rules. This is NOT necessarily the strategically
optimal discard.

actual_evaluation:
Evaluation after the player's actual discard.

best_evaluation:
Evaluation after the preferred alternative discard.

shanten:
向聽數. The number of tile improvements needed
to reach tenpai, minus one.
A smaller value is generally better.
0 = tenpai (聽牌).
-1 = completed hand (和牌形).

ukeire:
入章數. Total remaining copies of tile types
that immediately reduce shanten, according to
the evaluator's visible-tile assumptions.
It is NOT a probability, score, or han value.

effective_tiles:
A mapping from tile notation to the estimated
number of remaining copies of that tile.

Example:
{"3m": 4} means four copies of 3萬 are estimated
to remain. It does NOT mean efficiency score 4.

discarded_tile_yaku_potential:
Describes the potential yakuhai value of the
tile being discarded, NOT the hand's current han.

is_honor:
Whether the discarded tile is a wind or dragon.

is_yakuhai:
Whether the discarded tile is a value honor
given the current round wind and seat wind.

potential_yakuhai_han:
The number of yakuhai han that tile could provide
if it formed a qualifying triplet or quad.
It does NOT mean the hand currently has those han.

potential_bonus_han: (aka dora)
The number of bonus han that tile could provide
if it formed a qualifying triplet or quad.

indicator_dora_han: (dora)
The number of dora han that tile could provide
if it formed a qualifying triplet or quad.

blocks:
A possible decomposition of the hand after
discarding the candidate tile.
The decomposition may not be unique or exhaustive.

## Ranking rules

1. Prefer lower shanten.
2. When shanten is equal, prefer higher ukeire.
3. When both are equal, use the configured
   yakuhai tie-break heuristic if applicable.
4. Do not claim the evaluator accounts for defense,
   hand value, dora preservation, or opponent behavior
   unless those features are explicitly evaluated.

## Grounding requirements

- Never invent numerical ratings.
- Never interpret effective tile counts as scores.
- Never interpret ukeire as han or winning probability.
- Never claim that discarding a tile awards its yaku.
- Never claim to know Mortal's internal reasoning.
- If two fields contradict each other, report the
  inconsistency instead of inventing an explanation.



## Comparing shanten and ukeire

- Ukeire counts remaining copies of tiles that
  immediately reduce the current shanten.

- At equal shanten, higher ukeire is preferred
  by the efficiency evaluator.

- At different shanten values, ukeire counts
  improvements from DIFFERENT starting levels.
  Do not treat the higher ukeire as an overall
  efficiency advantage over lower shanten.

- Example:
  Discard A: shanten=4, ukeire=65
  Discard B: shanten=3, ukeire=50

  Correct: B has lower shanten and is preferred
  by the evaluator's shanten-first ranking.
  The ukeire values refer to different
  improvement levels.

  Incorrect: A is more efficient because 65>50.
  Incorrect: B is better because 50<65.
  Incorrect: B has a 25% higher tenpai probability.
"""


