PS D:\Programming\mortal\Mortal\mahjong-commentator> python -m evaluator.metrics `

> > --decisions data/processed/decisions.json `
> > --predictions data/metrics/predictions/deepseek-r1-8b-structured.jsonl
> >
> > 17: structured comparison is incorrect; explanation is empty or repeats protected facts
> > 21: structured comparison is incorrect
> > 32: structured comparison is incorrect
> > 46: explanation is empty or repeats protected facts
> > 53: structured comparison is incorrect
> > 71: ukeire comparison direction is missing or incorrect
> > 93: ukeire comparison direction is missing or incorrect
> > 103: structured comparison is incorrect
> > 113: structured comparison is incorrect
> > 152: explanation is empty or repeats protected facts
> > cases: 30/30
> > benchmark_coverage: 1.000
> > final_actual_discard_fidelity: 1.000 (eligible=30)
> > final_comparison_fidelity: 1.000 (eligible=30)
> > final_draw_fidelity: 1.000 (eligible=30)
> > final_effective_tile_fidelity: 1.000 (eligible=30)
> > final_format_compliance: 1.000 (eligible=30)
> > final_recommended_discard_fidelity: 1.000 (eligible=30)
> > final_route_accuracy: 1.000 (eligible=30)
> > final_shanten_fidelity: 1.000 (eligible=30)
> > final_ukeire_comparison_fidelity: 0.933 (eligible=30)
> > final_ukeire_fidelity: 1.000 (eligible=30)
> > production_fallback_rate: 0.267 (eligible=30)
> > raw_comparison_verdict_accuracy: 0.800 (eligible=30)
> > raw_explanation_compliance: 0.900 (eligible=30)
> > raw_json_format_compliance: 1.000 (eligible=30)
> > raw_reason_code_precision: 1.000 (eligible=30)
> > raw_reason_code_recall: 1.000 (eligible=30)
> > clean_cases: 0.667
> > latency_ms_mean: 16956.7
> > latency_ms_median: 11640.7
> > latency_ms_p90: 34961.8
> > latency_ms_max: 43624.1

PS D:\Programming\mortal\Mortal\mahjong-commentator> python -m evaluator.metrics `

> > --decisions data/processed/decisions.json `
> > --predictions data/metrics/predictions/deepseek-r1-8b-independent.jsonl
> >
> > 0: structured response contains unsupported reason codes; structured response omits expected reason codes; explanation is empty or repeats protected facts
> > 14: structured comparison is incorrect; structured response contains unsupported reason codes; structured response omits expected reason codes; explanation is empty or repeats protected facts
> > 17: structured comparison is incorrect; structured response contains unsupported reason codes; structured response omits expected reason codes
> > 18: structured comparison is incorrect
> > 19: structured comparison is incorrect; structured response contains unsupported reason codes; structured response omits expected reason codes; explanation is empty or repeats protected facts
> > 21: structured comparison is incorrect; structured response contains unsupported reason codes; structured response omits expected reason codes
> > 32: explanation is empty or repeats protected facts
> > 34: structured comparison is incorrect; explanation is empty or repeats protected facts
> > 46: structured comparison is incorrect; structured response contains unsupported reason codes; structured response omits expected reason codes
> > 49: explanation is empty or repeats protected facts
> > 53: structured comparison is incorrect; structured response contains unsupported reason codes; structured response omits expected reason codes; explanation is empty or repeats protected facts
> > 57: structured comparison is incorrect; structured response contains unsupported reason codes; structured response omits expected reason codes; explanation is empty or repeats protected facts
> > 63: structured response contains unsupportedreason codes; structured response omits expected reason codes; explanation is empty or repeats protected facts
> > 71: structured comparison is incorrect; structured response contains unsupported reason codes; structured response omits expected reason codes
> > 83: structured comparison is incorrect; structured response contains unsupported reason codes; structured response omits expected reason codes
> > 93: structured comparison is incorrect; structured response contains unsupported reason codes; structured response omits expected reason codes
> > 100: structured response omits expected reason codes
> > 102: model response is not valid benchmark JSON
> > 103: structured comparison is incorrect; structured response contains unsupported reason codes; structured response omits expected reason codes; explanation is empty or repeats protected facts
> > 112: structured comparison is incorrect; structured response contains unsupported reason codes; explanation is empty or repeats protected facts
> > 113: structured comparison is incorrect; structured response contains unsupported reason codes; structured response omits expected reason codes; explanation is empty or repeats protected facts
> > 114: structured comparison is incorrect; structured response contains unsupported reason codes; explanation is empty or repeats protected facts
> > 123: structured comparison is incorrect; structured response contains unsupported reason codes; explanation is empty or repeats protected facts
> > 125: structured comparison is incorrect; structured response contains unsupported reason codes; structured response omits expected reason codes; explanation is empty or repeats protected facts
> > 131: structured response contains unsupported reason codes
> > 151: structured comparison is incorrect; structured response contains unsupported reason codes; structured response omits expected reason codes; explanation is empty or repeats protected facts
> > 152: structured comparison is incorrect; structured response contains unsupported reason codes
> > 168: structured comparison is incorrect; explanation is empty or repeats protected facts
> > 174: structured response contains unsupported reason codes; explanation is empty or repeats protected facts
> > cases: 30/30
> > benchmark_coverage: 1.000
> > final_actual_discard_fidelity: 1.000 (eligible=30)
> > final_comparison_fidelity: 1.000 (eligible=30)
> > final_draw_fidelity: 1.000 (eligible=30)
> > final_effective_tile_fidelity: 1.000 (eligible=30)
> > final_format_compliance: 1.000 (eligible=30)
> > final_recommended_discard_fidelity: 1.000 (eligible=30)
> > final_route_accuracy: 1.000 (eligible=30)
> > final_shanten_fidelity: 1.000 (eligible=30)
> > final_ukeire_comparison_fidelity: 1.000 (eligible=30)
> > final_ukeire_fidelity: 1.000 (eligible=30)
> > production_fallback_rate: 0.967 (eligible=30)
> > raw_comparison_verdict_accuracy: 0.267 (eligible=30)
> > raw_explanation_compliance: 0.367 (eligible=30)
> > raw_json_format_compliance: 0.967 (eligible=30)
> > raw_reason_code_precision: 0.511 (eligible=30)
> > raw_reason_code_recall: 0.611 (eligible=30)
> > clean_cases: 0.033
> > latency_ms_mean: 11353.3
> > latency_ms_median: 11002.5
> > latency_ms_p90: 13035.1
> > latency_ms_max: 19889.0
