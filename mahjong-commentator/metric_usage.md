# Metric workflow usage

This project evaluates commentary one decision at a time. The complete
`decisions.json` file is used as the evidence database, but each LLM request
receives only one selected decision.

## Files

```text
data/processed/decisions.json
    Source evaluator decisions

data/metrics/gold_indices.json
    Decisions included in the benchmark

data/metrics/predictions/<model>.jsonl
    One generated commentary record per decision

evaluate_models.py
    Sends the selected decisions to an LLM

evaluator/metrics.py
    Checks predictions against evaluator evidence
```

The initial pilot set contains decisions `0` through `19`:

```json
[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
```

## 1. Generate predictions

Run commands from `Mortal/mahjong-commentator`.

```powershell
python evaluate_models.py `
  --model deepseek-r1:8b `
  --output data/metrics/predictions/deepseek-r1-8b.jsonl
```

For another model, use the same gold indices and change only the model/output:

```powershell
python evaluate_models.py `
  --model qwen3:8b `
  --output data/metrics/predictions/qwen3-8b.jsonl
```

The runner records one JSON object per line:

```json
{
  "index": 0,
  "model": "deepseek-r1:8b",
  "latency_ms": 1234.5,
  "commentary": "..."
}
```

If generation is interrupted, resume without overwriting completed cases:

```powershell
python evaluate_models.py `
  --model deepseek-r1:8b `
  --output data/metrics/predictions/deepseek-r1-8b.jsonl `
  --resume
```

Every model must use the same `gold_indices.json` for a fair comparison.

## 2. Run automatic metrics

```powershell
python -m evaluator.metrics `
  --decisions data/processed/decisions.json `
  --predictions data/metrics/predictions/deepseek-r1-8b.jsonl
```

The checker reports:

- `format_compliance`: required four-section structure
- `shanten_fidelity`: reported shanten agrees with the evaluator
- `ukeire_fidelity`: reported ukeire agrees with the evaluator
- `actual_discard_fidelity`: actual discard is reported
- `recommended_discard_fidelity`: evaluator recommendation is reported
- `comparison_fidelity`: both sides of a differing-discard comparison are reported
- `ukeire_comparison_fidelity`: commentary states whether the recommended
  discard has higher, lower, or equal ukeire than the actual discard
- `draw_fidelity`: drawn tile is reported correctly
- `route_accuracy`: selected route is reported correctly
- `effective_tile_fidelity`: effective tiles agree with the selected route
- `clean_cases`: cases with no automatic errors
- `latency_ms_mean`: average generation latency

Each failed case is printed with its decision index and error list.

## 3. Compare models

Generate a prediction file for every model, then run the metric command once
per file. Keep the outputs together for the report:

```powershell
python -m evaluator.metrics --decisions data/processed/decisions.json --predictions data/metrics/predictions/deepseek-r1-8b.jsonl
python -m evaluator.metrics --decisions data/processed/decisions.json --predictions data/metrics/predictions/qwen3-8b.jsonl
```

Do not select a model by latency or writing style if it fails factual safety
gates. The recommended minimum gates are:

```text
Factual/evidence checks: 95% or higher
Route accuracy:           95% or higher
Format compliance:        95% or higher
```

After automatic checking, manually annotate a sample for comparative relevance
and atomic recall. Report hallucination cases separately instead of hiding them
inside an average score.

## 4. Expand the benchmark

The first 20 decisions are a pipeline smoke test. For final FYP comparison,
replace `gold_indices.json` with a stratified set containing regular,
Chiitoitsu, and Kokushi routes; tied discards; different shanten levels;
supplied and missing draw tiles; and cases where actual and recommended
discards differ.
