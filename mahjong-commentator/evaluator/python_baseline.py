"""Deterministic explanation baseline with no model inference."""

from evaluator.comparison import efficiency_verdict


def baseline_explanation(decision: dict) -> str:
    verdict = efficiency_verdict(decision)
    if verdict == "same_action":
        return (
            "實際棄牌與牌效推薦是同一個動作，因此不存在另一個棄牌方案可供比較。"
        )
    if verdict == "equal_efficiency_distinct_actions":
        return (
            "兩個不同棄牌在目前評估器下具有相同向聽數與入章數，"
            "因此牌效證據不足以判定其中一個在整體策略上較好。"
        )
    actual = decision["actual_evaluation"]
    alternative = decision["best_evaluation"]
    if alternative["shanten"] < actual["shanten"]:
        return "替代棄牌可降低向聽數，因此在目前牌效排序中優先。"
    if actual["shanten"] < alternative["shanten"]:
        return "實際棄牌可降低向聽數，因此在目前牌效排序中優先。"
    if alternative["ukeire"] > actual["ukeire"]:
        return "兩者向聽數相同，但替代棄牌的入章數較高，因此牌效較佳。"
    return "兩者向聽數相同，但實際棄牌的入章數較高，因此牌效較佳。"
