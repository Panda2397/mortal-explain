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

The benchmark uses a stratified 30-decision pilot instead of the first 20
consecutive decisions. It contains:

- 15 cases with equal shanten and equal ukeire
- 12 cases with equal shanten but higher recommended ukeire
- all 3 available cases with lower recommended shanten
- both regular and Chiitoitsu routes
- cases where actual and recommended discards are equal and different

The source currently has no Kokushi, missing-draw, `actual_better`, or
`actual_higher_ukeire` cases. Those outcomes cannot be measured until examples
are added from other games or curated fixtures.

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
  "explanation_source": "llm",
  "json_valid": true,
  "raw_response": "{...}",
  "parsed_response": {
    "comparison": "recommended_better",
    "reason_codes_used": ["SAME_SHANTEN", "RECOMMENDED_HIGHER_UKEIRE"],
    "explanation": "..."
  },
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

Model-level metrics (use these to compare models):

- `json_valid`: response has exactly the required JSON fields and types
- `comparison_accuracy`: model returned the evaluator-supported relation
- `reason_code_precision`: used reason codes are supported by the evaluator
- `reason_code_recall`: expected reason codes were not omitted
- `explanation_compliance`: prose is non-empty and does not repeat protected
  numeric or tile facts
- `llm_explanation_used`: JSON prose passed validation and was used instead of
  the deterministic fallback
- `benchmark_coverage`: proportion of expected gold indices present in the
  prediction file; model scores should not be compared below `1.000`

System-level metrics (these verify the final rendered commentary pipeline):

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

The system-level scores may all be `1.000` because Python deliberately renders
verified facts. That is expected and does not mean all LLMs perform equally.
Compare models primarily with the model-level metrics, fallback rate (the
inverse of `llm_explanation_used`), latency, and manual prose-quality ratings.

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

The 30 decisions are a balanced pilot, not a final generalization benchmark.
For the final FYP comparison, add decisions from more games until the set also
contains Kokushi routes, missing draw tiles, and cases where the actual choice
outperforms the evaluator recommendation. Do not create those labels by
changing correct evaluator results.
