"""Shared efficiency-comparison labels for evaluation and prompting."""

from __future__ import annotations


VERDICTS = {
    "same_action",
    "equal_efficiency_distinct_actions",
    "actual_more_efficient",
    "alternative_more_efficient",
}


def efficiency_verdict(decision: dict) -> str:
    """Classify only shanten/ukeire efficiency, not overall strategy."""
    if decision["actual_discard"] == decision["best_efficiency_discard"]:
        return "same_action"

    actual = decision["actual_evaluation"]
    alternative = decision["best_evaluation"]
    actual_rank = (actual["shanten"], -actual["ukeire"])
    alternative_rank = (alternative["shanten"], -alternative["ukeire"])
    if actual_rank == alternative_rank:
        return "equal_efficiency_distinct_actions"
    if actual_rank < alternative_rank:
        return "actual_more_efficient"
    return "alternative_more_efficient"


def efficiency_reason_codes(decision: dict) -> list[str]:
    """Return deterministic reasons supporting :func:`efficiency_verdict`."""
    verdict = efficiency_verdict(decision)
    actual = decision["actual_evaluation"]
    alternative = decision["best_evaluation"]
    if verdict == "same_action":
        return ["ACTUAL_EQUALS_RECOMMENDATION"]
    if verdict == "equal_efficiency_distinct_actions":
        return ["SAME_SHANTEN", "SAME_UKEIRE", "DISTINCT_ACTIONS"]
    if alternative["shanten"] < actual["shanten"]:
        return ["ALTERNATIVE_LOWER_SHANTEN"]
    if actual["shanten"] < alternative["shanten"]:
        return ["ACTUAL_LOWER_SHANTEN"]
    if alternative["ukeire"] > actual["ukeire"]:
        return ["SAME_SHANTEN", "ALTERNATIVE_HIGHER_UKEIRE"]
    return ["SAME_SHANTEN", "ACTUAL_HIGHER_UKEIRE"]


def legacy_verdict(verdict: str) -> str:
    """Map the richer taxonomy to the original three-label schema."""
    if verdict in {"same_action", "equal_efficiency_distinct_actions"}:
        return "equal"
    if verdict == "alternative_more_efficient":
        return "recommended_better"
    return "actual_better"
