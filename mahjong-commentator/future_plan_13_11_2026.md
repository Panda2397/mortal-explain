# FYP future plan — 13 November 2026

## Research objective

Determine whether an evidence-grounded local LLM adds strategically relevant
and educational explanation beyond a deterministic Mahjong-efficiency
baseline, while keeping raw model performance separate from Python validation
and fallback.

## P0 — supervisor-ready evaluation

### Scope

1. Introduce explicit efficiency verdicts:
   `same_action`, `equal_efficiency_distinct_actions`,
   `actual_more_efficient`, and `alternative_more_efficient`.
2. Add a Python-only explanation baseline using the same decision evidence.
3. Preserve two LLM treatments:
   - `structured_copy`: receives the verified verdict and reason codes.
   - `independent_grounded`: receives decision evidence and must select a
     verdict without being given the answer.
4. Store treatment, prompt version, generation settings, exact messages,
   timestamps, model timings, validation result, and fallback reason.
5. Report raw-model metrics separately from final-system fidelity metrics.
6. Report benchmark coverage and latency mean, median, p90, and maximum.
7. Create a small annotation draft with explicit `needs_human_review` status.
8. Add tests for verdict classification, schema validation, fallback, and
   metric denominator behaviour.

### Acceptance criteria

- Same-action and distinct-action ties are never merged silently.
- Python baseline requires no model call.
- Existing JSONL predictions remain readable.
- Raw model scores cannot be confused with Python-rendered output scores.
- Empty or ineligible denominators are reported as N/A, not perfect scores.
- No draft annotation is presented as reviewed gold evidence.

### Meeting artifacts

- Architecture and limitation summary.
- Frozen pilot indices and annotation draft.
- Python baseline plus Qwen and DeepSeek treatments on identical decisions.
- Raw/final metric table and three qualitative examples.
- Explicit statement that shanten/ukeire efficiency is not overall strategy.

## P1 — state integrity and claim-level evaluation

1. Replace integer-only open-meld state with structured meld objects.
2. Track all public opponent meld tiles and legal action opportunities.
3. Add discard/call/riichi/win decision types incrementally.
4. Version the candidate-ranking policy and fix red-five identity handling.
5. Define a limited, tested yaku scope with confirmed/conditional/unknown
   evidence labels.
6. Add human-reviewed atomic claims and calculate factual precision, evidence
   support, comparative relevance, unsupported-claim rate, atomic recall, and
   incremental insight coverage.
7. Validate any automatic claim extractor against human annotations.
8. Expand the dataset across games and group results by game/round.

### P1 acceptance criteria

- Meld tiles and call provenance can be reconstructed from processed data.
- Strategic claims abstain when the evaluator lacks evidence.
- Claim metrics expose eligibility counts and N/A cases.
- Evaluator errors, extraction errors, and generator errors are reported
  separately.

## P2 — deferred work

- Defensive-risk modelling and calibration.
- Full yaku/han/fu/point evaluation.
- Controlled RAG corpus and with/without-RAG ablation.
- Interactive tutoring and user study.

These items are deferred because RAG cannot compensate for missing
state-specific evidence, and a full strategy engine is not feasible for the
three-day milestone.
