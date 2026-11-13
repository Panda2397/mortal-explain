"""Aggregate reviewed insight/claim ratings without treating drafts as gold."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


def safe_ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def aggregate_ratings(rows: list[dict]) -> dict[str, float | int | None]:
    insight_hits = insight_total = 0
    comparison_supported = comparison_total = 0
    unsupported = assessed_claims = 0
    per_decision_recall = []
    clarity = []

    for row in rows:
        coverage = row.get("insight_coverage", {})
        hits = sum(bool(value) for value in coverage.values())
        total = len(coverage)
        insight_hits += hits
        insight_total += total
        if total:
            per_decision_recall.append(hits / total)
        comparison_supported += row.get("supported_comparative_claims", 0)
        comparison_total += row.get("assessed_comparative_claims", 0)
        unsupported += row.get("unsupported_or_contradicted_claims", 0)
        assessed_claims += row.get("assessed_claims", 0)
        if row.get("clarity_rating") is not None:
            clarity.append(row["clarity_rating"])

    return {
        "atomic_recall_micro": safe_ratio(insight_hits, insight_total),
        "atomic_recall_macro": (
            statistics.mean(per_decision_recall) if per_decision_recall else None
        ),
        "comparative_relevance": safe_ratio(
            comparison_supported, comparison_total
        ),
        "unsupported_claim_rate": safe_ratio(unsupported, assessed_claims),
        "clarity_mean": statistics.mean(clarity) if clarity else None,
        "insight_eligible": insight_total,
        "comparative_eligible": comparison_total,
        "claim_eligible": assessed_claims,
    }


def incremental_insight_coverage(
    baseline_rows: list[dict], model_rows: list[dict]
) -> float | None:
    baseline = {
        (row["decision_index"], insight_id): bool(covered)
        for row in baseline_rows
        for insight_id, covered in row.get("insight_coverage", {}).items()
    }
    model = {
        (row["decision_index"], insight_id): bool(covered)
        for row in model_rows
        for insight_id, covered in row.get("insight_coverage", {}).items()
    }
    shared = baseline.keys() & model.keys()
    if not shared:
        return None
    added = sum(model[key] and not baseline[key] for key in shared)
    return added / len(shared)


def display(value) -> str:
    return "N/A" if value is None else (f"{value:.3f}" if isinstance(value, float) else str(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ratings", required=True, type=Path)
    args = parser.parse_args()
    rows = [
        json.loads(line)
        for line in args.ratings.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_system = defaultdict(list)
    for row in rows:
        by_system[row["system"]].append(row)
    for system, system_rows in sorted(by_system.items()):
        print(f"[{system}] cases={len(system_rows)}")
        for key, value in aggregate_ratings(system_rows).items():
            print(f"{key}: {display(value)}")
    baseline = by_system.get("python_baseline")
    if baseline:
        for system, system_rows in sorted(by_system.items()):
            if system == "python_baseline":
                continue
            value = incremental_insight_coverage(baseline, system_rows)
            print(f"incremental_insight_coverage[{system}]: {display(value)}")


if __name__ == "__main__":
    main()
