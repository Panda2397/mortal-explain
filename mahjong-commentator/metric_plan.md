# Mahjong commentary metric plan

## Goal

Evaluate whether generated commentary is factually grounded in the evaluator
evidence before comparing writing style or model preference.

The unit of evaluation is one decision. Python converts evaluator output into
an expected comparison and an allowed reason-code set. The LLM returns
structured JSON plus a short explanation; Python then renders the factual
four-section commentary.

## Dataset

Create a fixed gold set of 30–50 decisions from `data/processed/decisions.json`.
Include regular, Chiitoitsu, and Kokushi routes; tied discards; supplied and
missing draw tiles; visible honors not in the hand; and different shanten levels.
Keep the indices in `data/metrics/gold_indices.json` so every model sees the
same cases.

The current 30-case pilot is stratified by comparison outcome and route: 15
equal cases, 12 higher-recommended-ukeire cases, and all 3 available
lower-recommended-shanten cases. The current source file contains no Kokushi,
missing-draw, or actual-better examples, so final evaluation requires decisions
from additional games for those categories.

For each case, the evaluator evidence is authoritative. Human annotation is
only needed for insights that cannot be checked mechanically, such as whether
the strategic explanation is clear.

## Prediction format

Store one JSON object per line in `data/metrics/predictions/<model>.jsonl`:

```json
{
  "index": 19,
  "model": "model-name",
  "raw_response": "{...}",
  "parsed_response": {
    "comparison": "recommended_better",
    "reason_codes_used": ["SAME_SHANTEN", "RECOMMENDED_HIGHER_UKEIRE"],
    "explanation": "..."
  },
  "explanation_source": "llm",
  "commentary": "..."
}
```

The index must identify the source decision. Do not evaluate a commentary file
without its source index.

## Automatic metrics

Model-level checks used to distinguish models:

1. JSON validity and exact schema compliance.
2. Comparison accuracy against evaluator-derived gold.
3. Reason-code precision and recall.
4. Explanation compliance: non-empty prose without protected numeric/tile
   facts that should be rendered by Python.
5. LLM explanation acceptance versus deterministic fallback rate.

System-level checks used to verify the final pipeline:

1. Format compliance: all four required headings occur in the required order.
2. Hand fidelity: every claimed hand tile must be present in the source hand;
   a visible tile must not be presented as a concealed tile.
3. Draw fidelity: `drawn_tile` is reported exactly when present; missing draw
   information is not replaced with a guessed tile.
4. Numeric fidelity: reported shanten and ukeire values match the selected
   evaluator result.
5. Route accuracy: the commentary uses the evaluator's `best_routes` route.
6. Effective-tile fidelity: effective tile names must come from the selected
   route's effective-tile set.

Most checks produce per-case `0/1` values and an error list; reason-code
precision and recall are fractional. System-level checks can remain perfect
because verified facts are rendered deterministically. Model selection should
therefore use the model-level results, latency, and blinded human assessment.

## Human metrics

Annotators score a sampled claim set, blind to model identity:

- Factual Precision: correct verifiable claims / verifiable claims.
- Evidence Support Rate: claims directly supported by evaluator evidence /
  assessed claims.
- Comparative Relevance: valid actual-versus-alternative comparisons /
  comparative claims.
- Atomic Recall: expert-approved insights present / required insights.

Use two annotators for at least 20% of cases and report agreement. Resolve
disagreements before calculating the final score.

## Safety gates and aggregate score

Reject a model from style comparison if any of these fail:

```text
Factual Precision       >= 95%
Evidence Support Rate   >= 95%
Route Accuracy          >= 95%
Format Compliance       >= 95%
```

For models passing the gates, report:

```text
0.30 factual precision
0.20 evidence support
0.15 comparative relevance
0.10 atomic recall
0.10 route accuracy
0.10 format compliance
0.05 latency score
```

Also report hallucination rate separately. A low latency or attractive style
must never compensate for invented tiles or numerical facts.

## Running the checks

From `Mortal/mahjong-commentator`:

```powershell
python -m evaluator.metrics `
  --decisions data/processed/decisions.json `
  --predictions data/metrics/predictions/model.jsonl
```

The command prints per-case failures and aggregate automatic metrics. Human
metrics are entered separately after annotation.
