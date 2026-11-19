# Interactive replay coach

Run from `Mortal/mahjong-commentator`:

```powershell
python -m interact.cli --log data/raw/1st_open_meld.jsonl --player 0 --no-llm
```

Enable grounded questions with a running Ollama server:

```powershell
python -m interact.cli --log data/raw/1st_open_meld.jsonl --model qwen3:8b
```

An existing processed decision file can be opened without reevaluating it:

```powershell
python -m interact.cli --decisions data/processed/decisions.json --no-llm
```

Useful commands are `show`, `yaku`, `candidates`, `recommend`, `common-yaku`,
`yaku-discard tanyao`, `compare 1m`, `ask ...`, `explain`, `next`,
`previous`, `turn 5`, `evidence`, `clear`, and `quit`.

`common-yaku` counts the non-impossible routes reported within the detector's
three-shanten window for every discard. It ranks lower ordinary shanten first,
then confirmed and nearby route coverage, and then ordinary ukeire.
`yaku-discard YAKU` ranks candidates
for that route by feasibility, yaku shanten, measurement quality, yaku ukeire,
and finally ordinary efficiency. Each row also shows its blockers. An absent
route is shown as `not_reported`, which normally means it is outside the
detector's reporting window rather than proven impossible. These are
route-preservation rankings, not claims of globally optimal play.

`recommend` prints the five most efficient discard candidates, ordered by
lowest ordinary shanten and then highest ordinary ukeire. Each row includes
the feasible yaku routes whose yaku shanten is at most one above that
candidate's ordinary shanten. More distant routes are ignored as practical
approaches. Pinfu is also omitted as a current approach while the candidate
hand retains a value-honor pair. It then shows the effective tile types and total remaining ukeire,
for example `[pinfu] [2m 5m] [5]`. Use
`recommend 3` (or another positive number) to change the result count.

The LLM receives only the current turn's compact verified evidence, one chosen
comparison, and a short conversation window. It does not calculate shanten,
ukeire, remaining copies, or yaku feasibility itself.
