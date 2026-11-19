import unittest

from evaluator.comparison import efficiency_reason_codes, efficiency_verdict
from evaluator.metrics import check_structured_prediction
from evaluator.human_metrics import aggregate_ratings, safe_ratio
from evaluator.python_baseline import baseline_explanation
from evaluator.decision_evaluator import candidate_rank, evaluate_decision
from evaluator.dora import analyze_hand_dora
from evaluator.shanten import hand_to_34_with_red, index_to_tile, tile_to_index
from evaluator.ukeire import calculate_ukeire, evaluate_discards
from evaluator.yaku import analyze_hand_yakuhai
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

    def test_call_decision_replaces_stale_draw_with_call_context(self):
        parser = MJAIParser(player_id=0)
        parser.hand = ["5s", "6s", "9m"]
        parser.drawn_tile = "1m"
        parser.process_call({
            "type": "chi", "actor": 0, "target": 3,
            "pai": "7s", "consumed": ["5s", "6s"],
        })
        parser.process_discard({
            "type": "dahai", "actor": 0, "pai": "9m", "tsumogiri": False,
        })

        decision = parser.decisions[-1]
        self.assertIsNone(decision["drawn_tile"])
        self.assertEqual(decision["preceding_action"], {
            "type": "chi", "tile": "7s", "from_player": 3,
        })

    def test_kan_decision_keeps_kan_and_rinshan_draw_context(self):
        parser = MJAIParser(player_id=0)
        parser.hand = ["N", "N", "N", "N"]
        parser.process_kan({
            "type": "ankan", "actor": 0, "consumed": ["N"] * 4,
        })
        parser.process_draw({"type": "tsumo", "actor": 0, "pai": "4p"})
        parser.process_discard({
            "type": "dahai", "actor": 0, "pai": "4p", "tsumogiri": True,
        })

        decision = parser.decisions[-1]
        self.assertEqual(decision["drawn_tile"], "4p")
        self.assertEqual(decision["preceding_action"]["type"], "ankan")
        self.assertEqual(decision["preceding_action"]["tile"], "N")


class DiscardHistoryTests(unittest.TestCase):
    def test_decision_lists_discards_by_every_player_in_order(self):
        parser = MJAIParser(player_id=0)
        parser.start_round({
            "type": "start_kyoku", "oya": 0, "bakaze": "E",
            "kyoku": 1, "honba": 0, "kyotaku": 0,
            "scores": [25000] * 4,
            "tehais": [
                ["1m", "2m", "3m", "4m", "5m", "6m", "7m",
                 "8m", "9m", "1p", "2p", "3p", "4p", "5p"],
                ["?"] * 13, ["?"] * 13, ["?"] * 13,
            ],
        })
        parser.process_discard({
            "type": "dahai", "actor": 0, "pai": "1m", "tsumogiri": False,
        })
        parser.process_discard({
            "type": "dahai", "actor": 2, "pai": "9s", "tsumogiri": True,
        })
        parser.process_draw({"type": "tsumo", "actor": 0, "pai": "6p"})
        parser.process_discard({
            "type": "dahai", "actor": 0, "pai": "6p", "tsumogiri": True,
        })

        decision = parser.decisions[-1]
        self.assertNotIn("discard_history", decision)
        self.assertNotIn("tsumogiri", decision)
        self.assertEqual(decision["visible_tiles"], ["1m", "9s"])
        self.assertEqual(decision["discards_by_player"][0], ["1m"])
        self.assertEqual(decision["discards_by_player"][2], ["9s"])

    def test_called_discard_remains_in_throwers_river(self):
        parser = MJAIParser(player_id=0)
        parser.process_discard({
            "type": "dahai", "actor": 1, "pai": "5p", "tsumogiri": False,
        })
        parser.process_call({
            "type": "pon", "actor": 2, "target": 1,
            "pai": "5p", "consumed": ["5p", "5p"],
        })
        self.assertEqual(parser.discards_by_player[1], ["5p"])
        self.assertEqual(parser.known_public_tiles.count("5p"), 3)

    def test_opponent_kan_tiles_become_known_public_tiles(self):
        parser = MJAIParser(player_id=0)
        parser.process_kan({
            "type": "ankan", "actor": 2,
            "consumed": ["N", "N", "N", "N"],
        })
        self.assertEqual(parser.known_public_tiles.count("N"), 4)

    def test_candidate_furiten_history_includes_candidate_discard(self):
        source = {
            "player": 0, "round": {"bakaze": "E", "jikaze": "S"},
            "turn": 2, "drawn_tile": "9m",
            "hand": [
                "1m", "2m", "3m", "4m", "5m", "6m", "7m",
                "8m", "9m", "1p", "1p", "2p", "3p", "4p",
            ],
            "visible_tiles": ["E"],
            "discards_by_player": {
                0: ["E"],
                1: [], 2: [], 3: [],
            },
            "open_melds": [], "open_meld_count": 0,
            "dora_indicators": [], "actual_discard": "9m",
        }
        result = evaluate_decision(source)
        self.assertEqual(result["own_discards"], ["E"])
        self.assertEqual(
            result["actual_evaluation"]["own_discard_tiles_after_candidate"],
            ["E", "9m"],
        )

    def test_parser_preserves_chi_tiles(self):
        parser = MJAIParser(player_id=0)
        parser.hand = ["2m", "3m", "9p"]
        parser.process_call({
            "type": "chi", "actor": 0, "target": 3,
            "pai": "1m", "consumed": ["2m", "3m"],
        })
        self.assertEqual(parser.open_melds[0]["tiles"], ["2m", "3m", "1m"])
        self.assertEqual(parser.hand, ["9p"])

    def test_parser_preserves_daiminkan_tiles(self):
        parser = MJAIParser(player_id=0)
        parser.hand = ["5p", "5p", "5p", "9s"]
        parser.process_kan({
            "type": "daiminkan", "actor": 0, "target": 1,
            "pai": "5p", "consumed": ["5p", "5p", "5p"],
        })
        self.assertEqual(parser.open_melds[0]["tiles"], ["5p"] * 4)
        self.assertTrue(parser.open_melds[0]["open"])
        self.assertEqual(parser.hand, ["9s"])

    def test_parser_marks_ankan_closed(self):
        parser = MJAIParser(player_id=0)
        parser.hand = ["N", "N", "N", "N", "9s"]
        parser.process_kan({
            "type": "ankan", "actor": 0,
            "consumed": ["N", "N", "N", "N"],
        })
        self.assertEqual(parser.open_melds[0]["tiles"], ["N"] * 4)
        self.assertFalse(parser.open_melds[0]["open"])
        self.assertEqual(parser.hand, ["9s"])

    def test_parser_kakan_consumes_only_added_tile_and_upgrades_pon(self):
        parser = MJAIParser(player_id=0)
        parser.hand = ["5s", "9m"]
        parser.open_melds = [{
            "type": "pon", "tiles": ["5s", "5s", "5s"],
            "consumed": ["5s", "5s"], "called_tile": "5s",
            "from_player": 2, "actor": 0, "open": True,
        }]
        parser.known_public_tiles = ["5s", "5s", "5s"]
        parser.process_kan({
            "type": "kakan", "actor": 0, "pai": "5s",
            "consumed": ["5s", "5s", "5s"],
        })
        self.assertEqual(parser.hand, ["9m"])
        self.assertEqual(len(parser.open_melds), 1)
        self.assertEqual(parser.open_melds[0]["type"], "kakan")
        self.assertEqual(parser.open_melds[0]["tiles"], ["5s"] * 4)
        self.assertEqual(parser.known_public_tiles.count("5s"), 4)

    def test_structured_meld_list_is_authoritative_over_stale_count(self):
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
                "type": "pon", "tiles": ["F", "F", "F"],
                "called_tile": "F", "consumed": ["F", "F"],
                "from_player": 1, "actor": 0, "open": True,
            }],
            "open_meld_count": 3,
            "dora_indicators": [],
            "actual_discard": "9m",
        }
        result = evaluate_decision(source)
        self.assertEqual(result["open_meld_count"], 1)


class EvaluatorCompatibilityTests(unittest.TestCase):
    def test_candidate_rank_uses_efficiency_only(self):
        result = {
            "shanten": 1,
            "ukeire": 12,
        }
        self.assertEqual(candidate_rank(result), (1, -12))

    def test_missing_winds_do_not_abort_evaluation(self):
        source = {
            "player": 0, "round": {}, "turn": 1, "drawn_tile": "9m",
            "hand": [
                "1m", "2m", "3m", "4m", "5m", "6m", "7m",
                "8m", "9m", "1p", "1p", "2p", "3p", "4p",
            ],
            "visible_tiles": [], "open_melds": [],
            "open_meld_count": 0, "dora_indicators": [],
            "actual_discard": "9m",
        }
        result = evaluate_decision(source)
        self.assertEqual(result["round"], {})

    def test_legacy_visible_tiles_are_read_and_preserved(self):
        source = {
            "player": 0, "round": {"bakaze": "E", "jikaze": "S"},
            "turn": 1, "drawn_tile": "9m",
            "hand": [
                "1m", "2m", "3m", "4m", "5m", "6m", "7m",
                "8m", "9m", "1p", "1p", "2p", "3p", "4p",
            ],
            "visible_tiles": ["E", "E", "E"],
            "open_melds": [], "open_meld_count": 0,
            "dora_indicators": [], "actual_discard": "9m",
        }
        result = evaluate_decision(source)
        self.assertEqual(result["visible_tiles"], ["E", "E", "E"])

    def test_private_visibility_key_is_supported_during_migration(self):
        source = {
            "player": 0, "round": {"bakaze": "E", "jikaze": "S"},
            "turn": 1, "drawn_tile": "9m",
            "hand": [
                "1m", "2m", "3m", "4m", "5m", "6m", "7m",
                "8m", "9m", "1p", "1p", "2p", "3p", "4p",
            ],
            "_known_public_tiles": ["N"],
            "open_melds": [], "open_meld_count": 0,
            "dora_indicators": [], "actual_discard": "9m",
        }
        result = evaluate_decision(source)
        self.assertEqual(result["visible_tiles"], ["N"])

    def test_calculate_ukeire_accepts_both_visibility_keywords(self):
        hand = [
            "1m", "2m", "3m", "4m", "5m", "6m", "7m",
            "8m", "9m", "1p", "1p", "2p", "3p",
        ]
        legacy = calculate_ukeire(hand, visible_tiles=["4p"])
        migration = calculate_ukeire(hand, known_public_tiles=["4p"])
        self.assertEqual(legacy, migration)

    def test_evaluate_discards_accepts_both_visibility_keywords(self):
        hand = [
            "1m", "2m", "3m", "4m", "5m", "6m", "7m",
            "8m", "9m", "1p", "1p", "2p", "3p", "4p",
        ]
        legacy = evaluate_discards(hand, visible_tiles=["E"])
        migration = evaluate_discards(hand, known_public_tiles=["E"])
        self.assertEqual(legacy, migration)


class TileValidationTests(unittest.TestCase):
    def test_red_five_normalizes(self):
        self.assertEqual(tile_to_index("5mr"), tile_to_index("5m"))

    def test_red_five_identity_can_be_retained_with_structural_counts(self):
        result = hand_to_34_with_red(["5mr", "5m", "5pr", "1s"])
        self.assertEqual(result["counts"][tile_to_index("5m")], 2)
        self.assertEqual(result["red_fives"], {"m": 1, "p": 1, "s": 0})
        self.assertEqual(result["red_dora_count"], 2)

    def test_invalid_tiles_raise_value_error(self):
        for tile in ("0m", "10m", "5x", "4mr", "", None):
            with self.subTest(tile=tile):
                with self.assertRaises(ValueError):
                    tile_to_index(tile)

    def test_invalid_indices_raise_value_error(self):
        for index in (-1, 34, "1"):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    index_to_tile(index)


class CurrentHandValueTests(unittest.TestCase):
    def test_yakuhai_reports_value_honor_pair_as_potential(self):
        result = analyze_hand_yakuhai(
            concealed_tiles=["F", "F", "1m"],
            melds=[], bakaze="E", jikaze="S",
            known_public_tiles=["F"],
        )
        self.assertFalse(result["has_yakuhai"])
        self.assertEqual(result["potential_sets"], [{
            "tile": "F",
            "concealed_count": 2,
            "copies_needed": 1,
            "live_copies": 1,
            "feasible_from_known_tiles": True,
            "promising": True,
            "reasons": ["dragon"],
            "han_if_completed": 1,
        }])

    def test_yakuhai_reports_existing_concealed_and_meld_sets(self):
        result = analyze_hand_yakuhai(
            concealed_tiles=["F", "F", "F", "E", "E", "E"],
            melds=[{"type": "pon", "tiles": ["P", "P", "P"], "open": True}],
            bakaze="E",
            jikaze="E",
        )
        self.assertTrue(result["has_yakuhai"])
        self.assertEqual(result["total_han"], 4)
        self.assertEqual({value["tile"] for value in result["sets"]}, {"E", "F", "P"})

    def test_hand_dora_counts_red_indicator_and_open_meld_tiles(self):
        result = analyze_hand_dora(
            concealed_tiles=["5mr", "5m", "3p"],
            melds=[{"type": "pon", "tiles": ["4p", "4p", "4p"], "open": True}],
            dora_indicators=["4m", "3p"],
        )
        # Both 5m tiles are indicator dora; the red five stacks one aka han.
        # All three open 4p tiles are indicator dora.
        self.assertEqual(result["aka_dora_han"], 1)
        self.assertEqual(result["indicator_dora_han"], 5)
        self.assertEqual(result["total_dora_han"], 6)

    def test_evaluator_emits_dora_and_uses_detector_for_yakuhai(self):
        source = {
            "player": 0,
            "round": {"bakaze": "E", "jikaze": "S"},
            "turn": 1,
            "drawn_tile": "9m",
            "hand": [
                "F", "F", "F", "5mr", "1m", "2m", "3m",
                "4m", "5m", "6m", "7m", "8m", "9m", "1p",
            ],
            "visible_tiles": [], "open_melds": [], "open_meld_count": 0,
            "dora_indicators": ["4m"], "actual_discard": "1p",
        }
        result = evaluate_decision(source)["actual_evaluation"]
        self.assertNotIn("discarded_tile_yaku_potential", result)
        self.assertNotIn("discarded_tile_dora", result)
        self.assertNotIn("hand_yakuhai", result)
        yakuhai = result["yaku_analysis"]["opportunities"]["yakuhai_F"]
        self.assertTrue(yakuhai["metrics"]["structure_present"])
        self.assertEqual(result["hand_dora"]["total_dora_han"], 3)


if __name__ == "__main__":
    unittest.main()
