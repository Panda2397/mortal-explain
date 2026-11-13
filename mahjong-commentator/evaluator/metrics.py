"""Lightweight, evidence-grounded checks for generated commentary."""

import argparse
import json
import re
from pathlib import Path

from utils.tile_format import tile_to_chinese


HEADINGS = [
    "### 1.",
    "### 2.",
    "### 3.",
    "### 4.",
]

VALID_COMPARISONS = {"actual_better", "recommended_better", "equal"}


def expected_structured_answer(decision: dict) -> tuple[str, set[str]]:
    """Derive the gold comparison from evaluator output, not LLM prose."""
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
    expected_comparison, expected_reasons = expected_structured_answer(decision)
    parsed = parse_structured_prediction(prediction)
    if parsed is None:
        return {
            "json_valid": 0,
            "comparison_accuracy": 0,
            "reason_code_precision": 0.0,
            "reason_code_recall": 0.0,
            "explanation_compliance": 0,
            "structured_errors": ["model response is not valid benchmark JSON"],
        }

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
        "json_valid": 1,
        "comparison_accuracy": int(parsed["comparison"] == expected_comparison),
        "reason_code_precision": precision,
        "reason_code_recall": recall,
        "explanation_compliance": int(explanation_ok),
        "structured_errors": errors,
    }


def _contains_value(text: str, value) -> bool:
    return str(value) in text


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
        "format_compliance": int(format_ok),
        "shanten_fidelity": int(shanten_ok),
        "ukeire_fidelity": int(ukeire_ok),
        "actual_discard_fidelity": int(actual_discard_ok),
        "recommended_discard_fidelity": int(best_discard_ok),
        "comparison_fidelity": int(comparison_ok),
        "ukeire_comparison_fidelity": int(ukeire_comparison_ok),
        "draw_fidelity": int(drawn_ok),
        "route_accuracy": int(route_ok),
        "effective_tile_fidelity": int(effective_ok),
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
    for line in args.predictions.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        prediction = json.loads(line)
        index = prediction["index"]
        seen_indices.add(index)
        result = check_prediction(decisions[index], prediction["commentary"])
        structured = check_structured_prediction(decisions[index], prediction)
        result.update({k: v for k, v in structured.items() if k != "structured_errors"})
        result["errors"].extend(structured["structured_errors"])
        result["llm_explanation_used"] = int(
            prediction.get("explanation_source") == "llm"
        )
        result["latency_ms"] = prediction.get("latency_ms")
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

    keys = [k for k in scores[0] if k not in {"errors", "latency_ms"}]
    print(f"cases: {len(scores)}/{len(expected_indices)}")
    print(
        "benchmark_coverage: "
        f"{len(seen_indices & expected_indices) / len(expected_indices):.3f}"
    )
    for key in keys:
        print(f"{key}: {sum(s[key] for s in scores) / len(scores):.3f}")
    print(f"clean_cases: {sum(not s['errors'] for s in scores) / len(scores):.3f}")
    latencies = [s["latency_ms"] for s in scores if s["latency_ms"] is not None]
    if latencies:
        print(f"latency_ms_mean: {sum(latencies) / len(latencies):.1f}")


if __name__ == "__main__":
    main()
