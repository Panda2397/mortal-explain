import unittest

from evaluator.comparison import efficiency_reason_codes, efficiency_verdict
from evaluator.metrics import check_structured_prediction
from evaluator.human_metrics import aggregate_ratings, safe_ratio
from evaluator.python_baseline import baseline_explanation
from evaluator.decision_evaluator import evaluate_decision
from parser.mjai_parser import MJAIParser


def decision(
    actual_discard="1m",
    alternative_discard="1m",
    actual=(2, 20),
    alternative=(2, 20),
):
    return {
        "actual_discard": actual_discard,
        "best_efficiency_discard": alternative_discard,
        "actual_evaluation": {"shanten": actual[0], "ukeire": actual[1]},
        "best_evaluation": {
            "shanten": alternative[0],
            "ukeire": alternative[1],
        },
    }


class ComparisonTests(unittest.TestCase):
    def test_same_action_is_not_a_distinct_tie(self):
        value = decision()
        self.assertEqual(efficiency_verdict(value), "same_action")
        self.assertEqual(
            efficiency_reason_codes(value), ["ACTUAL_EQUALS_RECOMMENDATION"]
        )

    def test_distinct_efficiency_tie(self):
        value = decision(alternative_discard="2m")
        self.assertEqual(
            efficiency_verdict(value), "equal_efficiency_distinct_actions"
        )

    def test_lower_shanten_has_priority(self):
        value = decision(
            alternative_discard="2m", actual=(2, 30), alternative=(1, 5)
        )
        self.assertEqual(efficiency_verdict(value), "alternative_more_efficient")
        self.assertIn("降低向聽數", baseline_explanation(value))

    def test_higher_ukeire_breaks_equal_shanten(self):
        value = decision(
            alternative_discard="2m", actual=(1, 8), alternative=(1, 12)
        )
        self.assertEqual(efficiency_verdict(value), "alternative_more_efficient")
        self.assertIn("ALTERNATIVE_HIGHER_UKEIRE", efficiency_reason_codes(value))


class RawMetricTests(unittest.TestCase):
    def test_rich_structured_prediction(self):
        value = decision(alternative_discard="2m")
        prediction = {
            "parsed_response": {
                "comparison": "equal_efficiency_distinct_actions",
                "reason_codes_used": [
                    "SAME_SHANTEN",
                    "SAME_UKEIRE",
                    "DISTINCT_ACTIONS",
                ],
                "explanation": "兩個不同選擇在目前牌效標準下相同。",
            }
        }
        result = check_structured_prediction(value, prediction)
        self.assertEqual(result["raw_json_format_compliance"], 1)
        self.assertEqual(result["raw_comparison_verdict_accuracy"], 1)
        self.assertEqual(result["raw_reason_code_recall"], 1.0)

    def test_invalid_schema_is_not_perfect(self):
        result = check_structured_prediction(decision(), {"raw_response": "{}"})
        self.assertEqual(result["raw_json_format_compliance"], 0)
        self.assertEqual(result["raw_comparison_verdict_accuracy"], 0)


class HumanMetricTests(unittest.TestCase):
    def test_empty_denominator_is_na(self):
        self.assertIsNone(safe_ratio(0, 0))
        result = aggregate_ratings([])
        self.assertIsNone(result["atomic_recall_micro"])
        self.assertIsNone(result["comparative_relevance"])

    def test_claim_denominators_are_explicit(self):
        result = aggregate_ratings([{
            "insight_coverage": {"g1": True, "g2": False},
            "supported_comparative_claims": 1,
            "assessed_comparative_claims": 2,
            "unsupported_or_contradicted_claims": 1,
            "assessed_claims": 4,
            "clarity_rating": 4,
        }])
        self.assertEqual(result["atomic_recall_micro"], 0.5)
        self.assertEqual(result["comparative_relevance"], 0.5)
        self.assertEqual(result["unsupported_claim_rate"], 0.25)


class OpenMeldTests(unittest.TestCase):
    def test_parser_preserves_meld_tiles_and_count(self):
        parser = MJAIParser(player_id=0)
        parser.hand = ["8s", "8s", "1m"]
        parser.process_call({
            "type": "pon",
            "actor": 0,
            "target": 1,
            "pai": "8s",
            "consumed": ["8s", "8s"],
        })
        self.assertEqual(len(parser.open_melds), 1)
        self.assertEqual(parser.open_melds[0]["tiles"], ["8s", "8s", "8s"])
        self.assertEqual(parser.open_melds[0]["from_player"], 1)

    def test_evaluator_preserves_structured_melds(self):
        source = {
            "player": 0,
            "round": {"bakaze": "E", "jikaze": "S"},
            "turn": 1,
            "drawn_tile": "9m",
            "hand": [
                "1m", "2m", "3m", "4m", "5m", "6m",
                "7m", "8m", "9m", "1p", "1p",
            ],
            "visible_tiles": [],
            "open_melds": [{
                "type": "pon",
                "tiles": ["F", "F", "F"],
                "called_tile": "F",
                "consumed": ["F", "F"],
                "from_player": 1,
                "actor": 0,
                "open": True,
            }],
            "open_meld_count": 1,
            "dora_indicators": [],
            "actual_discard": "9m",
        }
        result = evaluate_decision(source)
        self.assertEqual(result["open_meld_count"], 1)
        self.assertEqual(result["open_melds"][0]["type"], "pon")


if __name__ == "__main__":
    unittest.main()
