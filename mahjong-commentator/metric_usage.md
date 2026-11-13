# Metric workflow reference

For the complete command sequence and treatment explanations, start with
[`usage.md`](usage.md). This file is the narrower reference for benchmark
files, metric meanings, safety gates, and dataset expansion.

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

Choose one treatment and keep it fixed across models:

- `python_baseline`: deterministic commentary, no model inference
- `structured_copy`: model receives the verified verdict and reason codes
- `independent_grounded`: model receives shanten/ukeire evidence but not the
  expected verdict

Generate the no-LLM baseline:

```powershell
python evaluate_models.py `
  --treatment python_baseline `
  --output data/metrics/predictions/python-baseline.jsonl
```

Run commands from `Mortal/mahjong-commentator`.

```powershell
python evaluate_models.py `
  --model deepseek-r1:8b `
  --treatment structured_copy `
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

Raw model-level metrics (use these to compare models):

- `raw_json_format_compliance`: response has the required JSON schema
- `raw_comparison_verdict_accuracy`: model returned the evaluator-supported relation
- `raw_reason_code_precision`: used reason codes are supported by the evaluator
- `raw_reason_code_recall`: expected reason codes were not omitted
- `raw_explanation_compliance`: prose is non-empty and does not repeat protected
  numeric or tile facts
- `production_fallback_rate`: model prose was replaced by Python
- `benchmark_coverage`: proportion of expected gold indices present in the
  prediction file; model scores should not be compared below `1.000`

Final-system metrics use the `final_` prefix and verify the rendered pipeline.
They must not be reported as raw model factual accuracy.

- `final_format_compliance`: required four-section structure
- `final_shanten_fidelity`: reported shanten agrees with the evaluator
- `final_ukeire_fidelity`: reported ukeire agrees with the evaluator
- `final_actual_discard_fidelity`: actual discard is reported
- `final_recommended_discard_fidelity`: evaluator recommendation is reported
- `final_comparison_fidelity`: both sides of a differing-discard comparison are reported
- `final_ukeire_comparison_fidelity`: commentary states whether the recommended
  discard has higher, lower, or equal ukeire than the actual discard
- `final_draw_fidelity`: drawn tile is reported correctly
- `final_route_accuracy`: selected route is reported correctly
- `final_effective_tile_fidelity`: effective tiles agree with the selected route
- `clean_cases`: cases with no automatic errors

### Latency components

All fields ending in `_ms` are milliseconds. For each component, the metric
command reports mean, median, p90, and maximum. Median represents a typical
request, while p90 is a better indicator of the delay experienced by slower
requests.

- `wall_latency_ms`: time measured by Python around the complete generation
  call. It includes client and local communication overhead, Ollama processing,
  response parsing, validation, fallback selection, and final rendering.
- `ollama_total_ms`: Ollama's internal total duration. It normally forms most
  of wall latency but excludes some Python/client overhead.
- `model_load_ms`: time Ollama spends loading or switching the model. This can
  be large on a cold first request and almost zero while the model stays loaded.
- `prompt_eval_ms`: time spent processing the system prompt, user evidence,
  and existing context before output generation begins.
- `generation_ms`: time spent decoding output tokens. For local LLMs this is
  commonly the largest component.
- `prompt_tokens`: number of tokens evaluated from the prompt. This is a count,
  not a duration.
- `output_tokens`: number of decoded output tokens, including reasoning tokens
  when the Ollama/model interface counts them in generation.
- `thinking_chars`: number of characters returned in the separate thinking
  field. This is diagnostic only; zero does not prove that the model performed
  no internal computation.
- `generation_tokens_per_second`: output-token throughput calculated from
  `eval_count / eval_duration`.

Wall time can be slightly greater than Ollama total because Python performs
additional work. A large difference suggests client, validation, filesystem,
or scheduling overhead. If model loading dominates, compare warmed runs or
report cold and warm latency separately. If prompt evaluation dominates,
shorten the prompt or context. If generation dominates, reduce output length,
disable thinking where appropriate, or use a faster model.

For a controlled thinking ablation, keep model, treatment, temperature, seed,
context size, output limit, decisions, and hardware identical; change only
`--think` versus `--no-think`. Compare output tokens and generation time, not
only total wall time.

### LLM latency versus the Python baseline

The Python baseline normally completes below the timer's displayed precision
because it performs formatting and comparisons without neural inference. An
8B no-thinking model may still feel "fast enough" interactively, but it is not
computationally similar to the Python baseline. For example, a response taking
one or two seconds can be acceptable to a user while remaining thousands of
times slower than a sub-millisecond template.

The research question is therefore not simply whether the LLM is tolerably
fast. Compare its additional latency against measurable additional value:

- Does it cover useful gold insights that the Python baseline omits?
- Is its explanation clearer in blinded human ratings?
- Does it handle independent comparison rather than copy supplied labels?
- How often does validation replace it with the Python fallback?

If no-thinking LLM output has the same factual content, insight coverage, and
clarity as the Python baseline, the Python baseline is preferable despite both
feeling responsive. If the LLM adds educational value and remains within the
chosen user-experience latency target, its extra computation may be justified.

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
