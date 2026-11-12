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

        actual_ukeire = actual_eval["ukeire"]
        best_ukeire = best_eval["ukeire"]
        if best_ukeire > actual_ukeire:
            expected_words = ("較高", "更高", "優於")
        elif best_ukeire < actual_ukeire:
            expected_words = ("較低", "更低", "不如")
        else:
            expected_words = ("相同", "一樣", "沒有差異", "效率相同")
        ukeire_comparison_ok = any(word in commentary for word in expected_words)
        if not ukeire_comparison_ok:
            errors.append("ukeire comparison direction is missing or incorrect")

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
    args = parser.parse_args()

    decisions = json.loads(args.decisions.read_text(encoding="utf-8"))
    scores = []
    for line in args.predictions.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        prediction = json.loads(line)
        index = prediction["index"]
        result = check_prediction(decisions[index], prediction["commentary"])
        result["latency_ms"] = prediction.get("latency_ms")
        scores.append(result)
        if result["errors"]:
            print(f"{index}: {'; '.join(result['errors'])}")

    if not scores:
        raise SystemExit("No predictions found")

    keys = [k for k in scores[0] if k not in {"errors", "latency_ms"}]
    print(f"cases: {len(scores)}")
    for key in keys:
        print(f"{key}: {sum(s[key] for s in scores) / len(scores):.3f}")
    print(f"clean_cases: {sum(not s['errors'] for s in scores) / len(scores):.3f}")
    latencies = [s["latency_ms"] for s in scores if s["latency_ms"] is not None]
    if latencies:
        print(f"latency_ms_mean: {sum(latencies) / len(latencies):.1f}")


if __name__ == "__main__":
    main()
