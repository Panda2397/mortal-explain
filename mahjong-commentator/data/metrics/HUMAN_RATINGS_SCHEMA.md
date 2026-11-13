# Human ratings schema

`gold_annotations_draft.jsonl` is not reviewed gold data. Change a record's
`review_status` only after checking the source decision and agreeing that its
insights are appropriate.

Create a separate ratings JSONL file with one row per decision and system:

```json
{
  "decision_index": 14,
  "system": "python_baseline",
  "annotator": "A1",
  "insight_coverage": {"14-g1": true, "14-g2": true},
  "supported_comparative_claims": 1,
  "assessed_comparative_claims": 1,
  "unsupported_or_contradicted_claims": 0,
  "assessed_claims": 2,
  "clarity_rating": 4,
  "notes": ""
}
```

Rules:

- Use `true` only when an insight is correctly expressed, not merely mentioned.
- Do not count `not_assessable` advice as false; record it in notes for review.
- A comparative claim is supported only if it distinguishes the alternatives
  or correctly explains that they are tied.
- `clarity_rating` uses 1–5 and must be assigned blind to model identity when
  practical.
- Keep unsupported and contradicted claims distinguishable in annotation
  notes, even though the initial aggregate reports their combined rate.
- If a denominator is zero, the aggregation script reports N/A.

Run:

```powershell
python -m evaluator.human_metrics --ratings data/metrics/human_ratings.jsonl
```
