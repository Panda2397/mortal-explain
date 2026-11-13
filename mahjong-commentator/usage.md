# Usage guide

Run all commands from:

```powershell
cd D:\Programming\mortal\Mortal\mahjong-commentator
```

Activate the project environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

For LLM treatments, start Ollama and make sure the requested models are
installed. The Python baseline and metric commands do not perform model
inference.

## Treatment differences

| Treatment | What the model receives | What the model must do | What the result measures |
|---|---|---|---|
| `python_baseline` | Evaluator evidence through Python only | Nothing; no model is called | Deterministic system quality and speed |
| `structured_copy` | The correct efficiency verdict, every required reason code, and verified route context | Return the supplied labels and express them as Traditional Chinese prose | JSON/schema adherence, copying reliability, and language quality |
| `independent_grounded` | Actual and alternative shanten, ukeire, discard identities, and verified route context—but not the correct verdict | Apply the shanten-first/ukeire-second rule, select the verdict and reason codes, then explain it | Independent application of the evaluator's comparison rule |

Example `structured_copy` input:

```json
{
  "expected_comparison": "equal_efficiency_distinct_actions",
  "allowed_reason_codes": [
    "SAME_SHANTEN",
    "SAME_UKEIRE",
    "DISTINCT_ACTIONS"
  ],
  "route_context": {
    "actual_best_routes": ["kokushi"],
    "alternative_best_routes": ["kokushi"]
  }
}
```

The answer is already supplied. A perfect score does not demonstrate Mahjong
calculation or independent comparison.

Example `independent_grounded` input:

```json
{
  "actual_discard": "2p",
  "alternative_discard": "3s",
  "actual": {"shanten": 2, "ukeire": 18},
  "alternative": {"shanten": 1, "ukeire": 12},
  "route_context": {
    "actual_best_routes": ["regular"],
    "alternative_best_routes": ["regular"]
  }
}
```

The model must conclude that the alternative is more efficient because lower
shanten has priority even though its immediate ukeire is smaller.

Neither LLM treatment independently calculates shanten or ukeire. Neither can
prove the best overall strategic action because the current evaluator lacks
complete yaku, value, defense, and opponent-risk evidence.

## 1. Rebuild evaluator decisions

This parses `data/raw/game_001.json`, evaluates every discard, and overwrites
`data/processed/decisions.json`:

```powershell
python main.py
```

Do not run this merely to evaluate existing predictions. Prediction indices
refer to the current ordering in `decisions.json`; rebuilding from different
input data can invalidate those indices.

## 2. Generate the Python-only baseline

This makes no LLM call:

```powershell
python evaluate_models.py `
  --treatment python_baseline `
  --output data/metrics/predictions/python-baseline.jsonl
```

Expected result:

- deterministic four-section commentary;
- final-system metrics are available;
- raw-model metrics report `N/A`;
- latency is close to zero because there is no inference.

## 3. Generate structured-copy predictions

In this treatment, Python gives the model the verified efficiency verdict and
required reason codes. It measures schema adherence and language realization,
not independent Mahjong reasoning.

### Qwen3 8B

```powershell
python evaluate_models.py `
  --model qwen3:8b `
  --treatment structured_copy `
  --think `
  --temperature 0 `
  --seed 42 `
  --num-ctx 8192 `
  --num-predict 1024 `
  --output data/metrics/predictions/qwen3-8b-structured.jsonl
```

### DeepSeek R1 8B

```powershell
python evaluate_models.py `
  --model deepseek-r1:8b `
  --treatment structured_copy `
  --think `
  --temperature 0 `
  --seed 42 `
  --num-ctx 8192 `
  --num-predict 1024 `
  --output data/metrics/predictions/deepseek-r1-8b-structured.jsonl
```

Use different output filenames for different models and treatments. Otherwise
a later run will overwrite an earlier result.

### Inference settings used during generation

Every LLM `evaluate_models.py` command accepts:

| Parameter | Default | Purpose |
|---|---:|---|
| `--think` / `--no-think` | `--think` | Enable or disable Ollama thinking mode |
| `--temperature FLOAT` | `0.0` | Sampling randomness |
| `--seed NUMBER` | `42` | Reproducible sampling seed |
| `--num-ctx NUMBER` | `8192` | Context-window allocation |
| `--num-predict NUMBER` | `1024` | Maximum generated tokens |

To compare thinking with non-thinking, run the same model and treatment twice,
change only `--think` to `--no-think`, and use different output filenames.
Keep temperature, seed, context, token limit, decisions, and indices identical.
The metric report separates wall time, loading, prompt evaluation, generation,
token counts, thinking characters, and generation throughput.

## 4. Generate independent-grounded predictions

In this treatment, the model receives the actual and alternative shanten and
ukeire evidence, but not the expected verdict. This is the more meaningful
test of whether the model can apply the evaluator's comparison rule.

### Qwen3 8B

```powershell
python evaluate_models.py `
  --model qwen3:8b `
  --treatment independent_grounded `
  --think `
  --temperature 0 `
  --seed 42 `
  --num-ctx 8192 `
  --num-predict 1024 `
  --output data/metrics/predictions/qwen3-8b-independent.jsonl
```

### DeepSeek R1 8B

```powershell
python evaluate_models.py `
  --model deepseek-r1:8b `
  --treatment independent_grounded `
  --think `
  --temperature 0 `
  --seed 42 `
  --num-ctx 8192 `
  --num-predict 1024 `
  --output data/metrics/predictions/deepseek-r1-8b-independent.jsonl
```

This treatment still evaluates efficiency only. It does not establish the
best overall strategic action because full yaku, value, and defense evidence
is unavailable.

## 5. Resume an interrupted generation

Add `--resume` with exactly the same model, treatment, indices, and output
file:

```powershell
python evaluate_models.py `
  --model qwen3:8b `
  --treatment independent_grounded `
  --output data/metrics/predictions/qwen3-8b-independent.jsonl `
  --resume
```

The runner skips decision indices already present in the JSONL file. Do not
resume into a file created with another treatment or model.

## 6. Use another decision set

By default, generation uses:

```text
data/processed/decisions.json
data/metrics/gold_indices.json
```

Override either path when needed:

```powershell
python evaluate_models.py `
  --decisions data/processed/decisions.json `
  --indices data/metrics/gold_indices.json `
  --model qwen3:8b `
  --treatment structured_copy `
  --output data/metrics/predictions/qwen3-custom.jsonl
```

All compared systems must use the same decision and index files.

## 7. Calculate automatic metrics

Run the metric command separately for every prediction file.

### Python baseline

```powershell
python -m evaluator.metrics `
  --decisions data/processed/decisions.json `
  --predictions data/metrics/predictions/python-baseline.jsonl
```

### Structured Qwen

```powershell
python -m evaluator.metrics `
  --decisions data/processed/decisions.json `
  --predictions data/metrics/predictions/qwen3-8b-structured.jsonl
```

### Independent Qwen

```powershell
python -m evaluator.metrics `
  --decisions data/processed/decisions.json `
  --predictions data/metrics/predictions/qwen3-8b-independent.jsonl
```

Replace the prediction path for DeepSeek or another model.

Interpret metric prefixes carefully:

- `raw_*`: evaluates the uncorrected model JSON;
- `production_fallback_rate`: how often Python rejected model prose;
- `final_*`: evaluates the Python-rendered production commentary;
- `benchmark_coverage`: must be `1.000` for a complete comparison;
- latency statistics: mean, median, p90, and maximum inference time.

Perfect `final_*` scores do not prove that the model reasoned correctly,
because Python renders verified factual fields.

## 8. Prepare and calculate human metrics

The current annotation file is a draft:

```text
data/metrics/gold_annotations_draft.jsonl
```

Review each record against `decisions.json` before treating it as gold data.
Create a separate ratings file following:

```text
data/metrics/HUMAN_RATINGS_SCHEMA.md
```

Then calculate human metrics:

```powershell
python -m evaluator.human_metrics `
  --ratings data/metrics/human_ratings.jsonl
```

The command reports, per system:

- micro and macro Atomic Recall;
- Comparative Relevance;
- Unsupported Claim Rate;
- mean clarity rating;
- explicit eligibility counts;
- Incremental Insight Coverage over `python_baseline`, when paired ratings
  are present.

Empty denominators are reported as `N/A`, not zero or perfect performance.

## 9. Run tests

```powershell
python -m unittest discover -s tests -v
```

The P0 tests cover comparison labels, shanten/ukeire priority, structured JSON
checking, invalid schema handling, and human-metric denominator behaviour.

## 10. Recommended experiment order

1. Generate `python-baseline.jsonl`.
2. Generate both models with `structured_copy`.
3. Generate both models with `independent_grounded`.
4. Run automatic metrics on every file.
5. Blind the system names and complete human ratings.
6. Run `evaluator.human_metrics`.
7. Compare raw accuracy, fallback rate, latency, educational insight coverage,
   and clarity separately.

Do not combine structured-copy and independent-grounded results into one
average: they answer different research questions.

## 11. Preview one explanation directly

Both entry-point names work:

```powershell
python .\test-commentator.py
python .\test_commentator.py
```

`test-commentator.py` is a compatibility wrapper. The implementation remains
in `test_commentator.py`.

### Parameter reference

| Parameter | Default | Meaning |
|---|---|---|
| `--decisions PATH` | `data/processed/decisions.json` | Processed decision JSON file |
| `--index NUMBER` | `0` | Zero-based decision index inside the file |
| `--model NAME` | `qwen3:8b` | Ollama model used for LLM treatments |
| `--treatment NAME` | `independent_grounded` | `python_baseline`, `structured_copy`, or `independent_grounded` |
| `--show MODE` | `both` | `commentary`, `raw`, `both`, or `prompt` |
| `--think` / `--no-think` | `--think` | Enable or disable Ollama thinking mode |
| `--temperature FLOAT` | `0.0` | Sampling temperature |
| `--seed NUMBER` | `42` | Sampling seed |
| `--num-ctx NUMBER` | `8192` | Context-window allocation |
| `--num-predict NUMBER` | `1024` | Maximum generated tokens |

Show all command-line options:

```powershell
python .\test-commentator.py --help
```

### Independent-grounded

The model receives shanten, ukeire, discard and verified route evidence, but
must determine the efficiency verdict itself:

```powershell
python .\test-commentator.py `
  --decisions data/processed/decisions.json `
  --index 14 `
  --model qwen3:8b `
  --treatment independent_grounded `
  --show both
```

### Structured-copy

The model receives the verified verdict and required reason codes:

```powershell
python .\test-commentator.py `
  --decisions data/processed/decisions.json `
  --index 14 `
  --model qwen3:8b `
  --treatment structured_copy `
  --show both
```

### Python baseline

No model is called:

```powershell
python .\test-commentator.py `
  --index 14 `
  --treatment python_baseline `
  --show commentary
```

### Custom Chiitoitsu fixture

```powershell
python .\test-commentator.py `
  --decisions data/processed/1st_seven_pair_decisions.json `
  --index 0 `
  --model qwen3:8b `
  --treatment independent_grounded `
  --show both
```

### Custom Kokushi fixture

```powershell
python .\test-commentator.py `
  --decisions data/processed/1st_ks_decisions.json `
  --index 0 `
  --model qwen3:8b `
  --treatment independent_grounded `
  --show both
```

Use `--index 1` to test the second decision in either custom file.

### Display modes

Show only the final four-section commentary:

```powershell
python .\test-commentator.py --index 14 --show commentary
```

Show only the raw model JSON:

```powershell
python .\test-commentator.py `
  --index 14 `
  --model deepseek-r1:8b `
  --treatment independent_grounded `
  --show raw
```

Show the raw JSON and final commentary:

```powershell
python .\test-commentator.py --index 14 --show both
```

Inspect the prompt without calling the model:

```powershell
python .\test-commentator.py `
  --decisions data/processed/1st_ks_decisions.json `
  --index 0 `
  --treatment independent_grounded `
  --show prompt
```

`--show prompt` never calls the model. The other display modes call the model
unless `--treatment python_baseline` is selected.
