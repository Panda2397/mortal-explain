"""Lightweight, evidence-grounded checks for generated commentary."""

import argparse
import json
import re
import statistics
from pathlib import Path

from evaluator.comparison import (
    VERDICTS,
    efficiency_reason_codes,
    efficiency_verdict,
)
from utils.tile_format import tile_to_chinese


HEADINGS = [
    "### 1.",
    "### 2.",
    "### 3.",
    "### 4.",
]

LEGACY_COMPARISONS = {"actual_better", "recommended_better", "equal"}
VALID_COMPARISONS = VERDICTS | LEGACY_COMPARISONS


def expected_structured_answer(decision: dict) -> tuple[str, set[str]]:
    """Compatibility helper for prediction files using the legacy schema."""
    actual = decision["actual_evaluation"]
    best = decision["best_evaluation"]
    reasons = set()
    if best["shanten"] < actual["shanten"]:
        comparison = "recommended_better"
        reasons.add("RECOMMENDED_LOWER_SHANTEN")
    elif best["shanten"] > actual["shanten"]:
        comparison = "actual_better"
        reasons.add("ACTUAL_LOWER_SHANTEN")
    elif best["ukeire"] > actual["ukeire"]:
        comparison = "recommended_better"
        reasons.update({"SAME_SHANTEN", "RECOMMENDED_HIGHER_UKEIRE"})
    elif best["ukeire"] < actual["ukeire"]:
        comparison = "actual_better"
        reasons.update({"SAME_SHANTEN", "ACTUAL_HIGHER_UKEIRE"})
    else:
        comparison = "equal"
        reasons.update({"SAME_SHANTEN", "SAME_UKEIRE"})
    if decision["actual_discard"] == decision["best_efficiency_discard"]:
        reasons.add("ACTUAL_EQUALS_RECOMMENDATION")
    return comparison, reasons


def expected_answer_for_prediction(
    decision: dict, parsed: dict
) -> tuple[str, set[str]]:
    if parsed["comparison"] in LEGACY_COMPARISONS:
        return expected_structured_answer(decision)
    return efficiency_verdict(decision), set(efficiency_reason_codes(decision))


def parse_structured_prediction(prediction: dict) -> dict | None:
    parsed = prediction.get("parsed_response")
    if parsed is None and isinstance(prediction.get("raw_response"), str):
        try:
            parsed = json.loads(prediction["raw_response"])
        except json.JSONDecodeError:
            return None
    if not isinstance(parsed, dict):
        return None
    if set(parsed) != {"comparison", "reason_codes_used", "explanation"}:
        return None
    if parsed["comparison"] not in VALID_COMPARISONS:
        return None
    if not isinstance(parsed["reason_codes_used"], list) or not all(
        isinstance(code, str) for code in parsed["reason_codes_used"]
    ):
        return None
    if not isinstance(parsed["explanation"], str):
        return None
    return parsed


def check_structured_prediction(decision: dict, prediction: dict) -> dict:
    parsed = parse_structured_prediction(prediction)
    if parsed is None:
        return {
            "raw_json_format_compliance": 0,
            "raw_comparison_verdict_accuracy": 0,
            "raw_reason_code_precision": 0.0,
            "raw_reason_code_recall": 0.0,
            "raw_explanation_compliance": 0,
            "structured_errors": ["model response is not valid benchmark JSON"],
        }

    expected_comparison, expected_reasons = expected_answer_for_prediction(
        decision, parsed
    )
    predicted_reasons = set(parsed["reason_codes_used"])
    precision = (
        len(predicted_reasons & expected_reasons) / len(predicted_reasons)
        if predicted_reasons else float(not expected_reasons)
    )
    recall = (
        len(predicted_reasons & expected_reasons) / len(expected_reasons)
        if expected_reasons else 1.0
    )
    explanation = parsed["explanation"].strip()
    # Numeric values and tile identities belong to deterministic sections.
    explanation_ok = bool(explanation) and not re.search(
        r"\d|[1-9][mps萬筒索]", explanation
    )
    errors = []
    if parsed["comparison"] != expected_comparison:
        errors.append("structured comparison is incorrect")
    if precision < 1:
        errors.append("structured response contains unsupported reason codes")
    if recall < 1:
        errors.append("structured response omits expected reason codes")
    if not explanation_ok:
        errors.append("explanation is empty or repeats protected facts")
    return {
        "raw_json_format_compliance": 1,
        "raw_comparison_verdict_accuracy": int(
            parsed["comparison"] == expected_comparison
        ),
        "raw_reason_code_precision": precision,
        "raw_reason_code_recall": recall,
        "raw_explanation_compliance": int(explanation_ok),
        "structured_errors": errors,
    }


def _contains_value(text: str, value) -> bool:
    return str(value) in text


def percentile_90(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, int(0.9 * len(ordered) + 0.999999) - 1)]


def print_distribution(name: str, values: list[float]) -> None:
    if not values:
        return
    print(f"{name}_mean: {statistics.mean(values):.1f}")
    print(f"{name}_median: {statistics.median(values):.1f}")
    print(f"{name}_p90: {percentile_90(values):.1f}")
    print(f"{name}_max: {max(values):.1f}")


def check_prediction(decision: dict, commentary: str) -> dict:
    errors = []
    actual = decision["actual_evaluation"]
    best_routes = actual.get("shanten_by_type", {}).get("best_routes", [])
    selected_route = best_routes[0] if best_routes else None
    route_data = actual.get("ukeire_by_type", {}).get(selected_route, {})

    positions = [commentary.find(h) for h in HEADINGS]
    format_ok = all(p >= 0 for p in positions) and positions == sorted(positions)
    if not format_ok:
        errors.append("required headings are missing or out of order")

    shanten_ok = _contains_value(commentary, actual.get("shanten"))
    ukeire_ok = _contains_value(commentary, actual.get("ukeire"))
    if not shanten_ok:
        errors.append("top-level shanten is not reported")
    if not ukeire_ok:
        errors.append("top-level ukeire is not reported")

    actual_discard_ok = tile_to_chinese(decision["actual_discard"]) in commentary
    best_discard_ok = tile_to_chinese(decision["best_efficiency_discard"]) in commentary
    if not actual_discard_ok:
        errors.append("actual discard is not reported")
    if not best_discard_ok:
        errors.append("recommended discard is not reported")

    actual_eval = decision["actual_evaluation"]
    best_eval = decision["best_evaluation"]
    comparison_required = decision["actual_discard"] != decision["best_efficiency_discard"]
    comparison_ok = True
    ukeire_comparison_ok = True
    if comparison_required:
        # Both values must occur when the two discard choices differ. The
        # deterministic renderer supplies the complete comparison; this check
        # catches an LLM paragraph that contradicts it or omits one choice.
        comparison_ok = (
            _contains_value(commentary, actual_eval["shanten"])
            and _contains_value(commentary, best_eval["shanten"])
            and _contains_value(commentary, actual_eval["ukeire"])
            and _contains_value(commentary, best_eval["ukeire"])
        )
        if not comparison_ok:
            errors.append("actual/recommended discard comparison is incomplete")

        # Ukeire is the tie-breaker only when both choices have equal shanten.
        # When shanten differs, requiring an ukeire direction can penalize a
        # correct explanation that focuses on the evaluator's primary rule.
        if actual_eval["shanten"] == best_eval["shanten"]:
            actual_ukeire = actual_eval["ukeire"]
            best_ukeire = best_eval["ukeire"]
            if best_ukeire > actual_ukeire:
                expected_words = ("較高", "更高", "優於")
            elif best_ukeire < actual_ukeire:
                expected_words = ("較低", "更低", "不如")
            else:
                expected_words = ("相同", "一樣", "沒有差異", "效率相同")
            ukeire_comparison_ok = any(
                word in commentary for word in expected_words
            )
            if not ukeire_comparison_ok:
                errors.append(
                    "ukeire comparison direction is missing or incorrect"
                )

    drawn = decision.get("drawn_tile")
    drawn_ok = drawn is None or tile_to_chinese(drawn) in commentary
    if not drawn_ok:
        errors.append("drawn tile is missing or incorrect")

    route_names = {
        "regular": "一般型",
        "chiitoitsu": "七對子",
        "kokushi": "國士無雙",
    }
    route_ok = selected_route is None or route_names.get(selected_route, selected_route) in commentary
    if not route_ok:
        errors.append("best route is not identified")

    effective = route_data.get("effective_tiles", {})
    effective_ok = all(tile_to_chinese(tile) in commentary for tile in effective)
    if not effective_ok:
        errors.append("one or more selected-route effective tiles are missing")

    return {
        "final_format_compliance": int(format_ok),
        "final_shanten_fidelity": int(shanten_ok),
        "final_ukeire_fidelity": int(ukeire_ok),
        "final_actual_discard_fidelity": int(actual_discard_ok),
        "final_recommended_discard_fidelity": int(best_discard_ok),
        "final_comparison_fidelity": int(comparison_ok),
        "final_ukeire_comparison_fidelity": int(ukeire_comparison_ok),
        "final_draw_fidelity": int(drawn_ok),
        "final_route_accuracy": int(route_ok),
        "final_effective_tile_fidelity": int(effective_ok),
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decisions", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument(
        "--indices",
        type=Path,
        default=Path("data/metrics/gold_indices.json"),
        help="Expected benchmark indices used to report coverage",
    )
    args = parser.parse_args()

    decisions = json.loads(args.decisions.read_text(encoding="utf-8"))
    expected_indices = set(json.loads(args.indices.read_text(encoding="utf-8")))
    scores = []
    seen_indices = set()
    response_metadata = []
    for line in args.predictions.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        prediction = json.loads(line)
        index = prediction["index"]
        seen_indices.add(index)
        result = check_prediction(decisions[index], prediction["commentary"])
        treatment = prediction.get("treatment", "legacy_structured_copy")
        if treatment == "python_baseline":
            result.update({
                "raw_json_format_compliance": None,
                "raw_comparison_verdict_accuracy": None,
                "raw_reason_code_precision": None,
                "raw_reason_code_recall": None,
                "raw_explanation_compliance": None,
                "production_fallback_rate": None,
            })
        else:
            structured = check_structured_prediction(decisions[index], prediction)
            result.update({
                k: v for k, v in structured.items()
                if k != "structured_errors"
            })
            result["errors"].extend(structured["structured_errors"])
            result["production_fallback_rate"] = int(
                prediction.get("explanation_source") != "llm"
            )
        result["latency_ms"] = prediction.get("latency_ms")
        response_metadata.append(prediction.get("response_metadata") or {})
        scores.append(result)
        if result["errors"]:
            print(f"{index}: {'; '.join(result['errors'])}")

    if not scores:
        raise SystemExit("No predictions found")

    missing_indices = sorted(expected_indices - seen_indices)
    extra_indices = sorted(seen_indices - expected_indices)
    if missing_indices:
        print(f"missing benchmark indices: {missing_indices}")
    if extra_indices:
        print(f"extra prediction indices: {extra_indices}")

    keys = sorted(
        set().union(*(score.keys() for score in scores))
        - {"errors", "latency_ms"}
    )
    print(f"cases: {len(scores)}/{len(expected_indices)}")
    print(
        "benchmark_coverage: "
        f"{len(seen_indices & expected_indices) / len(expected_indices):.3f}"
    )
    for key in keys:
        eligible = [score.get(key) for score in scores if score.get(key) is not None]
        if eligible:
            print(
                f"{key}: {sum(eligible) / len(eligible):.3f} "
                f"(eligible={len(eligible)})"
            )
        else:
            print(f"{key}: N/A (eligible=0)")
    print(f"clean_cases: {sum(not s['errors'] for s in scores) / len(scores):.3f}")
    latencies = [s["latency_ms"] for s in scores if s["latency_ms"] is not None]
    if latencies:
        print_distribution("wall_latency_ms", latencies)

    duration_fields = {
        "ollama_total_ms": "total_duration",
        "model_load_ms": "load_duration",
        "prompt_eval_ms": "prompt_eval_duration",
        "generation_ms": "eval_duration",
    }
    for label, field in duration_fields.items():
        values = [
            metadata[field] / 1_000_000
            for metadata in response_metadata
            if metadata.get(field) is not None
        ]
        print_distribution(label, values)

    for label, field in {
        "prompt_tokens": "prompt_eval_count",
        "output_tokens": "eval_count",
        "thinking_chars": "thinking_chars",
    }.items():
        values = [
            metadata[field]
            for metadata in response_metadata
            if metadata.get(field) is not None
        ]
        print_distribution(label, values)

    tokens_per_second = [
        metadata["eval_count"] / (metadata["eval_duration"] / 1_000_000_000)
        for metadata in response_metadata
        if metadata.get("eval_count") is not None
        and metadata.get("eval_duration", 0) > 0
    ]
    print_distribution("generation_tokens_per_second", tokens_per_second)


if __name__ == "__main__":
    main()
