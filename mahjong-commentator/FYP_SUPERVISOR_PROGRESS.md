# FYP Progress Update

**Executive summary**

- The project has expanded from a tile-efficiency explainer into an interactive Riichi Mahjong analysis prototype.
- Python now produces efficiency evidence, yaku-route evidence, comparisons and basic explanations.
- A deterministic comparison layer is needed to compare evaluator outputs before any evidence is sent to the LLM.
- The repository declares **28 supported structural yaku routes**, although some calculations are lower bounds or heuristics.
- All **104 automated tests pass**.
- A 30-case pilot currently favours **Qwen3:8b structured (no-thinking)** for its combination of automatic-check reliability and lower latency.
- Proposed direction: use the LLM as an **interactive, evidence-grounded tutor**, rather than generating commentary for every discard.

## 1. Recap of Previous Meeting

### Previous system

| Component        | Role                                                     |
| ---------------- | -------------------------------------------------------- |
| Python evaluator | Calculate ordinary shanten and ukeire for legal discards |
| Ranking policy   | Minimise shanten, then maximise ukeire                   |
| Evidence         | Produce structured JSON facts                            |
| LLM              | Convert evidence into natural-language commentary        |

### Supervisor feedback

- Compare different LLMs.
- Define quantitative evaluation metrics.
- Test model parameters, prompts and context sizes.
- Evaluate factual accuracy and usefulness.

## 2. Progress Since Previous Meeting

### Yaku-opportunity evaluator

The evaluator now reports:

- yaku feasibility and blockers;
- yaku-specific distance and effective draws;
- fixed-meld and open/closed restrictions;
- established components and validated yaku-tenpai;
- evidence type: `exact`, `lower_bound` or `heuristic`.

| Yaku group             | Implemented routes                                                                                                                     |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Closed/shape-dependent | Pinfu, Iipeikou, Ryanpeikou, Chiitoitsu                                                                                                |
| Open-capable regular   | Tanyao, Yakuhai, Toitoi, Sanankou, Sanshoku Doujun/Doukou, Ittsu, Chanta, Junchan, Honitsu, Chinitsu, Honroutou, Sankantsu, Shousangen |
| Structural yakuman     | Kokushi, Suuankou, Chuuren Poutou, Daisangen, Shousuushii, Daisuushii, Tsuuiisou, Chinroutou, Ryuuiisou, Suukantsu                     |

The current inventory contains **28 routes**, not the earlier estimate of approximately 18. Support is not equally exact: for example, kan-related routes are action-dependent heuristics.

### Interactive replay CLI

| Implemented feature                   | Example commands              |
| ------------------------------------- | ----------------------------- |
| View hand, melds and current analysis | `show`, `yaku`                |
| Navigate replay decisions             | `next`, `previous`, `turn`    |
| Inspect discard candidates            | `candidates`, `recommend`     |
| Explore yaku-preserving alternatives  | `common-yaku`, `yaku-discard` |
| Compare hypothetical discards         | `compare`, `evidence`         |
| Ask the grounded local LLM            | `ask`, `explain`              |

The CLI's efficiency and yaku rankings are separate views. They do **not** form a validated overall strategy ranking.

<img src="images\Snipaste_2026-11-19_09-22-06.jpg">
<img src="images\Snipaste_2026-11-19_09-26-48.jpg">

### Testing

| Result                   | Repository evidence                                                                          |
| ------------------------ | -------------------------------------------------------------------------------------------- |
| **104/104 tests passed** | Python `unittest` suite                                                                      |
| Evaluator coverage       | Shanten/ukeire ranking, tiles, visible information and discard history                       |
| Yaku coverage            | Meld context, blockers, open/closed restrictions, waits, no-yaku tenpai and regression cases |
| System coverage          | Parsing, batch processing, JSON output, CLI navigation, evidence selection and LLM history   |
| Limitation               | Passing tests do not prove complete Mahjong-rule correctness                                 |

### Model-selection pilot

The repository contains saved results from the same 30-case benchmark. The figures below are automatic checks, not human ratings of educational quality.

| Model/treatment                       | Comparison accuracy | Fallback rate | Mean latency | Assessment                       |
| ------------------------------------- | ------------------: | ------------: | -----------: | -------------------------------- |
| Qwen3:8b, structured                  |                100% |            0% |        9.3 s | Reliable but slow                |
| **Qwen3:8b, structured, no-thinking** |            **100%** |        **0%** |    **2.4 s** | **Current practical choice**     |
| Qwen3:8b, independent grounded        |               96.7% |         76.7% | Not reported | More unsupported/omitted reasons |
| DeepSeek-R1:8b, structured            |                 80% |         26.7% | Not reported | Less reliable on recorded checks |
| DeepSeek-R1:8b, independent grounded  |               26.7% |         96.7% | Not reported | Unsuitable in this pilot         |

**Current model choice: Qwen3:8b structured (no-thinking).** It retained the recorded automatic reliability of the full structured run while reducing mean latency. This is a provisional engineering choice because the benchmark is small and the structured prompt already supplies much of the reasoning.

## 3. Preliminary Findings

- Python is sufficient for factual shanten/ukeire summaries.
- Automatic LLM paraphrasing adds latency and hallucination risk.
- Yaku evidence reveals trade-offs that efficiency alone cannot explain.
- Structured grounding improves reliability, but may reduce the LLM to paraphrasing Python.
- Human evaluation is still needed to establish relevance and teaching value.

These are preliminary observations, not final experimental conclusions.

## 4. Current Challenges

| Challenge                 | Current position                                                             |
| ------------------------- | ---------------------------------------------------------------------------- |
| LLM added value           | Must provide adaptation or educational explanation beyond templates          |
| Conflicting objectives    | Efficiency, yaku and future defense evaluators may favour different discards |
| Yaku accuracy             | Exact, lower-bound and heuristic results must remain clearly separated       |
| Missing strategy evidence | No active defense-aware or score-aware overall ranking                       |
| Project scope             | Full scoring, defense and search could distract from the AI research         |

A deterministic comparison layer should compare every candidate across the available evaluators. It should state dimension-specific facts such as "better efficiency", "preserves a closer yaku route" or, once implemented, "lower defensive risk". If the evidence does not justify one overall winner, the layer should report a trade-off rather than force a single ranking. Only this verified comparison should be passed to the LLM.

## 5. Proposed Revised Research Direction

| Previous LLM role                         | Proposed LLM role                            |
| ----------------------------------------- | -------------------------------------------- |
| Automatic commentary for every discard    | Answer user-selected strategy questions      |
| Repeat calculated results                 | Explain precomputed comparison evidence      |
| Potentially imply unsupported conclusions | State uncertainty and abstain when necessary |
| Limited value over templates              | Provide comparison, adaptation and tutoring  |

### Required analysis pipeline

| Stage                 | Responsibility                                                                  |
| --------------------- | ------------------------------------------------------------------------------- |
| 1. Evaluators         | Calculate efficiency, yaku opportunities and, in future, defensive risk         |
| 2. Comparison layer   | Compare candidates on each available dimension and identify verified trade-offs |
| 3. Evidence selection | Select the comparison facts relevant to the user's question                     |
| 4. LLM                | Explain those facts clearly; do not perform Mahjong calculations or rankings    |

Python should remain responsible for:

- shanten, ukeire and remaining-copy calculations;
- winning legality and yaku evidence;
- evaluating hypothetical discards before explanation;
- deciding which candidate is better on each supported evaluator dimension.

The LLM may interpret the natural-language question and optionally use RAG strategy knowledge, but it must receive the comparison result from Python. It must not independently decide whether a discard is better for efficiency, yaku or defense. This direction requires supervisor approval.

## 6. Research Questions and Evaluation Plan

### Research questions

- **RQ1:** Are evidence-grounded LLM answers more relevant and educational than Python templates?
- **RQ2:** Does a deterministic multi-evaluator comparison layer improve factual correctness and evidence faithfulness?
- **RQ3:** Does RAG improve contextual explanations beyond evaluator evidence alone?

### Proposed comparison

| System                           | Description                                                                                      |
| -------------------------------- | ------------------------------------------------------------------------------------------------ |
| Python baseline                  | Template generated from deterministic comparison evidence                                        |
| LLM + efficiency comparison      | LLM explains a Python-computed efficiency comparison                                             |
| LLM + multi-evaluator comparison | LLM explains Python-computed efficiency and yaku trade-offs; defense can be added when available |
| LLM + comparison + RAG           | Same verified comparison plus retrieved strategy knowledge                                       |

An ungrounded "LLM only" system is excluded from the main comparison because the LLM must not calculate or rank Mahjong decisions. If retained at all, it should be labelled only as an unsafe negative control, not a deployable approach.

Metrics: factual correctness, unsupported-claim rate, evidence faithfulness, relevance, completeness, educational usefulness and latency.

To control workload, first fix one model and decoding setup. Afterwards, run small ablations for model choice, temperature, prompts, context length and evidence selection.

## 7. Next Steps

| Priority     | Work                                                                                                                                                          |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **High**     | Fix material evaluator errors; stabilise evidence; implement the deterministic multi-evaluator comparison layer; define benchmark questions and rating rubric |
| **Medium**   | Add curated RAG; compare selected models/prompts; improve multi-turn questions                                                                                |
| **Optional** | Defense, richer scoring, replay-level strategy and rare-yaku edge cases                                                                                       |

## 8. Questions for Supervisor

1. Should the LLM move from automatic commentary to interactive tutoring?
2. What is going to be presented in December's sharing:
   - project goal
   - challenges
   - python code?
   - comparison of model
   - things to be done in sem 2
   - others?
3. Is the template versus evidence-grounded versus RAG comparison a sufficient FYP contribution?
4. Should evaluator validation or systematic LLM experiments come next?

## 9. Evidence Sent to the LLM

The LLM does **not** receive the complete `processed/*.json` replay. For each question, Python selects one decision and builds compact evidence:

`processed JSON -> current decision -> Python evaluators -> comparison layer -> compact evidence -> LLM explanation`

| Evidence                |                                         Amount sent per question |
| ----------------------- | ---------------------------------------------------------------: |
| Current replay decision |                                                                1 |
| Actual discard          |                                             1 detailed candidate |
| Comparison discard      |                                     At most 1 detailed candidate |
| Other choices           |                              Top 5 Python-ranked discard options |
| Recent discard history  |                                          Last 6 tiles per player |
| Yaku routes             | Only feasible nearby routes within 1 shanten of ordinary shanten |
| Yaku differences        |               Python-computed changes between the two candidates |
| Full route witnesses    |                                 Excluded from the default prompt |

The evidence includes the hand and round state, open melds, actual discard, efficiency-best discard, shanten, ukeire, effective tiles, nearby yaku routes, blockers, tenpai legality and measurement warnings. The LLM should explain these facts; it must not calculate or rank the candidates itself.

For the current `data/processed/decisions.json` file:

| Measurement across 175 decisions |                     Result |
| -------------------------------- | -------------------------: |
| Median evidence size             | Approximately 1,690 tokens |
| Mean evidence size               | Approximately 1,742 tokens |
| Range                            |           779-3,883 tokens |
| Nearby yaku for actual discard   |             1-10; mean 3.3 |
| Nearby yaku for comparison       |              0-8; mean 1.7 |
| Python-computed yaku changes     |                        0-6 |

The interactive coach also receives the user's question, system instructions and up to six recent conversation messages. Estimated total input is limited to 6,500 tokens within an 8,192-token context. Old conversation turns are removed before current verified evidence is truncated.
