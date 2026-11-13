qwen3:8b structured

PS D:\Programming\mortal\Mortal\mahjong-commentator> python -m evaluator.metrics `

> > --decisions data/processed/decisions.json `
> > --predictions data/metrics/predictions/qwen3-8b-structured.jsonl
> >
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
> > production_fallback_rate: 0.000 (eligible=30)
> > raw_comparison_verdict_accuracy: 1.000 (eligible=30)
> > raw_explanation_compliance: 1.000 (eligible=30)
> > raw_json_format_compliance: 1.000 (eligible=30)
> > raw_reason_code_precision: 1.000 (eligible=30)
> > raw_reason_code_recall: 1.000 (eligible=30)
> > clean_cases: 1.000
> > wall_latency_ms_mean: 9282.9
> > wall_latency_ms_median: 10154.5
> > wall_latency_ms_p90: 11136.6
> > wall_latency_ms_max: 17260.3
> > ollama_total_ms_mean: 9213.5
> > ollama_total_ms_median: 10152.7
> > ollama_total_ms_p90: 11134.7
> > ollama_total_ms_max: 15216.7
> > model_load_ms_mean: 186.9
> > model_load_ms_median: 3.0
> > model_load_ms_p90: 8.0
> > model_load_ms_max: 5474.7
> > prompt_eval_ms_mean: 98.4
> > prompt_eval_ms_median: 35.3
> > prompt_eval_ms_p90: 37.6
> > prompt_eval_ms_max: 1963.8
> > generation_ms_mean: 8918.4
> > generation_ms_median: 8671.6
> > generation_ms_p90: 11078.0
> > generation_ms_max: 11168.1
> > prompt_tokens_mean: 1772.0
> > prompt_tokens_median: 1775.0
> > prompt_tokens_p90: 1777.0
> > prompt_tokens_max: 1777.0
> > output_tokens_mean: 385.0
> > output_tokens_median: 362.5
> > output_tokens_p90: 478.0
> > output_tokens_max: 478.0
> > generation_tokens_per_second_mean: 43.2
> > generation_tokens_per_second_median: 43.2
> > generation_tokens_per_second_p90: 43.5
> > generation_tokens_per_second_max: 43.5

qwen3:8b independent

PS D:\Programming\mortal\Mortal\mahjong-commentator> & d:/Programming/mortal/Mortal/playground/.venv/Scripts/Activate.ps1
(.venv) PS D:\Programming\mortal\Mortal\mahjong-commentator> python -m evaluator.metrics `

> > --decisions data/processed/decisions.json `
> > --predictions data/metrics/predictions/qwen3-8b-independent.jsonl
> > 0: structured response contains unsupported reason codes
> > 14: structured response omits expected reason codes
> > 17: structured comparison is incorrect; structured response contains unsupported reason codes
> > 18: structured response omits expected reason codes
> > 19: structured response contains unsupported reason codes; explanation is empty or repeats protected facts
> > 21: explanation is empty or repeats protected facts
> > 28: structured response omits expected reason codes
> > 34: explanation is empty or repeats protected facts
> > 49: structured response contains unsupported reason codes; structured response omits expected reason codes; explanation is empty or repeats protected facts
> > 63: structured response contains unsupported reason codes; explanation is empty or repeats protected facts
> > 71: explanation is empty or repeats protected facts
> > 83: structured response omits expected reason codes
> > 100: structured response omits expected reason codes
> > 102: structured response contains unsupported reason codes; structured response omits expected reason codes; explanation is empty or repeats protected facts
> > 103: explanation is empty or repeats protected facts
> > 112: structured response contains unsupported reason codes
> > 114: explanation is empty or repeats protected facts
> > 123: structured response contains unsupported reason codes; explanation is empty or repeats protected facts
> > 125: structured response omits expected reason codes
> > 131: structured response contains unsupported reason codes
> > 151: explanation is empty or repeats protected facts
> > 168: structured response omits expected reason codes
> > 174: structured response contains unsupported reason codes; structured response omits expected reason codes
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
> > production_fallback_rate: 0.767 (eligible=30)
> > raw_comparison_verdict_accuracy: 0.967 (eligible=30)
> > raw_explanation_compliance: 0.633 (eligible=30)
> > raw_json_format_compliance: 1.000 (eligible=30)
> > raw_reason_code_precision: 0.761 (eligible=30)
> > raw_reason_code_recall: 0.822 (eligible=30)
> > clean_cases: 0.233
> > latency_ms_mean: 11649.7
> > latency_ms_median: 9440.0
> > latency_ms_p90: 17163.5  
> > latency_ms_max: 38243.6

nothink 8b
PS D:\Programming\mortal\Mortal\mahjong-commentator> python -m evaluator.metrics `

> > --decisions data/processed/decisions.json `
> > --predictions data/metrics/predictions/qwen3-8b-structured-nothink.jsonl
> >
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
> > production_fallback_rate: 0.000 (eligible=30)
> > raw_comparison_verdict_accuracy: 1.000 (eligible=30)
> > raw_explanation_compliance: 1.000 (eligible=30)
> > raw_json_format_compliance: 1.000 (eligible=30)
> > raw_reason_code_precision: 1.000 (eligible=30)
> > raw_reason_code_recall: 1.000 (eligible=30)
> > clean_cases: 1.000
> > wall_latency_ms_mean: 2425.1
> > wall_latency_ms_median: 2108.3
> > wall_latency_ms_p90: 2181.1
> > wall_latency_ms_max: 14090.6
> > ollama_total_ms_mean: 2356.0
> > ollama_total_ms_median: 2106.9
> > ollama_total_ms_p90: 2180.3
> > ollama_total_ms_max: 12049.7
> > model_load_ms_mean: 313.1
> > model_load_ms_median: 3.0
> > model_load_ms_p90: 6.0
> > model_load_ms_max: 9281.7
> > prompt_eval_ms_mean: 80.9
> > prompt_eval_ms_median: 45.6
> > prompt_eval_ms_p90: 51.0
> > prompt_eval_ms_max: 1095.2
> > generation_ms_mean: 1953.2
> > generation_ms_median: 2045.7
> > generation_ms_p90: 2118.8
> > generation_ms_max: 2119.8
> > prompt_tokens_mean: 1855.6
> > prompt_tokens_median: 1857.0
> > prompt_tokens_p90: 1862.0
> > prompt_tokens_max: 1866.0
> > output_tokens_mean: 81.1
> > output_tokens_median: 85.0
> > output_tokens_p90: 88.0
> > output_tokens_max: 88.0
> > thinking_chars_mean: 0.0
> > thinking_chars_median: 0.0
> > thinking_chars_p90: 0.0
> > thinking_chars_max: 0.0
> > generation_tokens_per_second_mean: 41.5
> > generation_tokens_per_second_median: 41.5
> > generation_tokens_per_second_p90: 41.6
> > generation_tokens_per_second_max: 42.8

qwen3:4b instruct (nothink)
PS D:\Programming\mortal\Mortal\mahjong-commentator> python -m evaluator.metrics `

> > --decisions data/processed/decisions.json `
> > --predictions data/metrics/predictions/qwen3-4b-instruct-structured.jsonl
> >
> > 21: ukeire comparison direction is missing or incorrect
> > 32: ukeire comparison direction is missing or incorrect
> > 46: ukeire comparison direction is missing or incorrect
> > 53: ukeire comparison direction is missing or incorrect
> > 103: ukeire comparison direction is missing or incorrect
> > 113: ukeire comparison direction is missing or incorrect
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
> > final_ukeire_comparison_fidelity: 0.800 (eligible=30)
> > final_ukeire_fidelity: 1.000 (eligible=30)
> > production_fallback_rate: 0.000 (eligible=30)
> > raw_comparison_verdict_accuracy: 1.000 (eligible=30)
> > raw_explanation_compliance: 1.000 (eligible=30)
> > raw_json_format_compliance: 1.000 (eligible=30)
> > raw_reason_code_precision: 1.000 (eligible=30)
> > raw_reason_code_recall: 1.000 (eligible=30)
> > clean_cases: 0.800
> > latency_ms_mean: 1625.2
> > latency_ms_median: 1436.6
> > latency_ms_p90: 1629.7
> > latency_ms_max: 7595.8
