import json
import unittest

from evaluator.decision_evaluator import evaluate_decision
from evaluator.ukeire import evaluate_discards
from evaluator.yaku_detector import (
    YakuRules,
    detect_yaku_opportunities,
    normalize_yaku_context,
    detect_yaku_routes,
)
from evaluator.yaku_detector.tenpai import analyze_tenpai_legality


def analyze(
    hand,
    *,
    melds=None,
    visible=None,
    bakaze="E",
    jikaze="S",
    rules=None,
):
    context = normalize_yaku_context(
        hand=hand,
        open_melds=[] if melds is None else melds,
        visible_tiles=[] if visible is None else visible,
        round_info={"bakaze": bakaze, "jikaze": jikaze},
        rules=rules,
    )
    return detect_yaku_opportunities(context).to_dict()


class ContextTests(unittest.TestCase):
    def test_ankan_preserves_menzen(self):
        value = analyze(
            ["2m", "3m", "4m"],
            melds=[{
                "type": "ankan",
                "tiles": ["E", "E", "E", "E"],
                "open": False,
            }],
        )
        self.assertTrue(value["menzen"])

    def test_open_call_breaks_menzen(self):
        value = analyze(
            ["2m", "3m", "4m"],
            melds=[{
                "type": "chi",
                "tiles": ["2p", "3p", "4p"],
                "open": True,
            }],
        )
        self.assertFalse(value["menzen"])

    def test_legacy_integer_melds_are_unknown(self):
        context = normalize_yaku_context(
            hand=["2m", "3m", "4m"],
            open_melds=1,
            visible_tiles=[],
            round_info={"bakaze": "E", "jikaze": "S"},
        )
        value = detect_yaku_opportunities(context).to_dict()
        self.assertFalse(value["input_complete"])
        self.assertIsNone(value["menzen"])
        self.assertEqual(
            value["opportunities"]["tanyao"]["feasibility"],
            "unknown",
        )


class YakuhaiDetectorTests(unittest.TestCase):
    def test_fixed_double_wind_set_is_guaranteed(self):
        value = analyze(
            ["2m", "3m", "4m"],
            melds=[{
                "type": "pon",
                "tiles": ["E", "E", "E"],
                "open": True,
            }],
            bakaze="E",
            jikaze="E",
        )
        opportunity = value["opportunities"]["yakuhai_E"]
        self.assertTrue(opportunity["guaranteed_on_completion"])
        self.assertEqual(opportunity["metrics"]["han_if_completed"], 2)
        self.assertEqual(opportunity["facts"], ("FIXED_VALUE_HONOR_SET",))
        self.assertTrue(value["has_established_yaku"])

    def test_concealed_triplet_is_present_but_not_irreversible(self):
        value = analyze(["F", "F", "F", "2m", "3m"])
        opportunity = value["opportunities"]["yakuhai_F"]
        self.assertEqual(opportunity["feasibility"], "possible")
        self.assertFalse(opportunity["guaranteed_on_completion"])
        self.assertTrue(opportunity["metrics"]["structure_present"])

    def test_exhausted_pair_route_is_impossible(self):
        value = analyze(["F", "F", "2m"], visible=["F", "F"])
        opportunity = value["opportunities"]["yakuhai_F"]
        self.assertEqual(opportunity["feasibility"], "impossible")
        self.assertEqual(opportunity["metrics"]["live_copies"], 0)

    def test_missing_winds_still_allows_dragon_analysis(self):
        value = analyze(["P", "P", "2m"], bakaze=None, jikaze=None)
        self.assertFalse(value["input_complete"])
        self.assertIn("yakuhai_P", value["opportunities"])
        self.assertNotIn("yakuhai_E", value["opportunities"])


class TanyaoDetectorTests(unittest.TestCase):
    def test_all_current_tiles_simple_is_possible(self):
        value = analyze(["2m", "3m", "4m", "5pr", "8s"])
        opportunity = value["opportunities"]["tanyao"]
        self.assertEqual(opportunity["feasibility"], "possible")
        self.assertTrue(opportunity["promising"])
        self.assertEqual(opportunity["metrics"]["incompatible_concealed_tiles"], 0)

    def test_concealed_outside_tile_is_obstruction_not_impossibility(self):
        value = analyze(["1m", "3m", "4m", "5p"])
        opportunity = value["opportunities"]["tanyao"]
        self.assertEqual(opportunity["feasibility"], "unknown")
        self.assertEqual(opportunity["obstructing_tiles"], ("1m",))
        self.assertEqual(
            opportunity["facts"],
            ("CONCEALED_OUTSIDE_TILES_DISCARDABLE",),
        )

    def test_fixed_outside_meld_is_impossible(self):
        value = analyze(
            ["2m", "3m", "4m"],
            melds=[{
                "type": "chi",
                "tiles": ["1p", "2p", "3p"],
                "open": True,
            }],
        )
        opportunity = value["opportunities"]["tanyao"]
        self.assertEqual(opportunity["feasibility"], "impossible")
        self.assertEqual(opportunity["fixed_meld_indices"], (0,))

    def test_closed_tanyao_rule_rejects_open_hand(self):
        value = analyze(
            ["2m", "3m", "4m"],
            melds=[{
                "type": "chi",
                "tiles": ["2p", "3p", "4p"],
                "open": True,
            }],
            rules=YakuRules(ruleset="no_kuitan", open_tanyao=False),
        )
        self.assertEqual(
            value["opportunities"]["tanyao"]["facts"],
            ("OPEN_TANYAO_DISABLED",),
        )


class IntegrationTests(unittest.TestCase):
    @staticmethod
    def source():
        return {
            "player": 0,
            "round": {"bakaze": "E", "jikaze": "S"},
            "turn": 1,
            "drawn_tile": "9m",
            "hand": [
                "1m", "2m", "3m", "4m", "5m", "6m", "7m",
                "8m", "9m", "2p", "3p", "4p", "5p", "6p",
            ],
            "visible_tiles": [],
            "open_melds": [],
            "open_meld_count": 0,
            "dora_indicators": [],
            "actual_discard": "1m",
        }

    def test_evaluator_adds_detector_schema_and_json_serializes(self):
        result = evaluate_decision(self.source())
        self.assertEqual(result["schema_version"], "1.4")
        self.assertIn("yakuhai", result["yaku_detector"]["supported_yaku"])
        self.assertIn("pinfu", result["yaku_detector"]["supported_yaku"])
        self.assertIn("current_yaku_analysis", result)
        self.assertIn("yaku_analysis", result["actual_evaluation"])
        route_report = result["actual_evaluation"]["yaku_analysis"]
        self.assertIn("yaku", route_report)
        for route in route_report["yaku"].values():
            self.assertTrue({
                "shanten", "ukeire", "feasibility", "yaku_blockers",
                "route_state", "proof", "outcome_scope", "availability",
                "guarantee", "legacy_feasibility", "ukeire_kind",
                "ukeire_witnesses", "estimated_improving_draws",
                "tenpai_quality",
            }.issubset(route))
        self.assertIn("yaku_comparison", result)
        self.assertIn("yaku_discard_recommendations", result)
        self.assertIn("discard_options", result)
        self.assertTrue(result["discard_options"])
        self.assertEqual(result["discard_options"][0]["efficiency_rank"], 1)
        for option in result["discard_options"]:
            for route in option["nearby_yaku"]:
                self.assertLessEqual(
                    route["yaku_shanten"] - option["ordinary_shanten"], 1
                )
        for recommendation in result["yaku_discard_recommendations"].values():
            self.assertIn(recommendation["discard"], result["hand"])
            self.assertIn("yaku_shanten", recommendation)
        json.dumps(result)

    def test_structural_route_groups_are_reported_and_sorted(self):
        routes = evaluate_decision(self.source())["actual_evaluation"]["yaku_analysis"]["yaku"]
        self.assertIn("tanyao", routes)
        self.assertIn("ittsu", routes)
        self.assertIn(routes["ittsu"]["shanten"]["measurement"], {
            "exact", "lower_bound", "upper_bound", "heuristic",
        })
        values = [
            route["shanten"]["value"]
            for route in routes.values()
            if route["shanten"]["value"] is not None
        ]
        self.assertEqual(values, sorted(values))

    def test_outside_pinfu_and_singleton_yakuhai_bounds(self):
        source = self.source()
        source["hand"] = [
            "1m", "2m", "3m", "4m", "5mr", "1p", "5s",
            "6s", "7s", "8s", "8s", "F", "F", "C",
        ]
        source["drawn_tile"] = "C"
        source["actual_discard"] = "1p"
        routes = evaluate_decision(source)["actual_evaluation"]["yaku_analysis"]["yaku"]
        self.assertNotIn("chanta", routes)
        self.assertNotIn("junchan", routes)
        self.assertEqual(routes["yakuhai_C"]["shanten"]["value"], 2)
        # Candidate output uses the processed relative cutoff. Pinfu is more
        # than one additional shanten away and is therefore not serialized.
        self.assertNotIn("pinfu", routes)

    def test_processed_routes_use_relative_extra_shanten_cutoff(self):
        source = self.source()
        source["hand"] = [
            "1m", "2m", "3m", "4m", "5mr", "1p", "5s",
            "6s", "7s", "8s", "8s", "F", "F", "C",
        ]
        source["drawn_tile"] = "C"
        source["actual_discard"] = "1p"
        result = evaluate_decision(source)["actual_evaluation"]
        routes = result["yaku_analysis"]["yaku"]
        ordinary = result["shanten"]

        for route in routes.values():
            value = route["shanten"]["value"]
            if (
                value is not None
                and route["feasibility"] != "impossible"
                and route.get("route_state") not in {
                    "component_present", "yaku_tenpai", "complete",
                }
            ):
                self.assertLessEqual(value - ordinary, 1)
        self.assertEqual(
            result["yaku_analysis"]["route_filter"]["max_extra_shanten"],
            1,
        )

    def test_concealed_yakuhai_triplet_is_confirmed_in_route_summary(self):
        source = self.source()
        source["hand"] = [
            "1m", "2m", "3m", "4m", "5mr", "5s", "6s",
            "7s", "8s", "8s", "9s", "F", "F", "F",
        ]
        source["drawn_tile"] = "9s"
        source["actual_discard"] = "9s"
        analysis = evaluate_decision(source)["actual_evaluation"]["yaku_analysis"]
        self.assertIn("yakuhai_F", analysis["confirmed_yaku"])
        self.assertIn("yakuhai_F", analysis["established_components"])
        self.assertEqual(analysis["yaku"]["yakuhai_F"]["feasibility"], "possible")
        self.assertEqual(
            analysis["yaku"]["yakuhai_F"]["legacy_feasibility"], "confirmed"
        )
        self.assertEqual(analysis["yaku"]["yakuhai_F"]["shanten"]["value"], 0)

    def test_existing_yakuhai_triplet_validates_unrelated_winning_tile(self):
        context = normalize_yaku_context(
            hand=[
                "F", "F", "F", "1p", "2p", "3p", "1s", "2s", "3s",
                "4s", "5s", "6s", "5m",
            ],
            open_melds=[],
            visible_tiles=[],
            round_info={"bakaze": "E", "jikaze": "S"},
        )

        route = detect_yaku_routes(context)["yaku"]["yakuhai_F"]

        self.assertEqual(route["shanten"]["value"], 0)
        self.assertEqual(route["ukeire"], {"5m": 3})
        self.assertEqual(route["route_state"], "yaku_tenpai")
        self.assertEqual(route["proof"]["validation"], "scorer_validated")

    def test_secured_open_yakuhai_counts_non_honor_improvements(self):
        context = normalize_yaku_context(
            hand=[
                "1m", "2m", "3m", "4m", "5m",
                "7p", "8p", "5s", "5s", "E",
            ],
            open_melds=[{
                "type": "pon", "tiles": ["F", "F", "F"], "open": True,
            }],
            visible_tiles=[],
            round_info={"bakaze": "E", "jikaze": "E"},
        )

        route = detect_yaku_routes(context)["yaku"]["yakuhai_F"]

        self.assertEqual(route["shanten"]["value"], 1)
        self.assertEqual(
            set(route["estimated_improving_draws"]),
            {"3m", "6m", "6p", "9p"},
        )
        self.assertEqual(route["tenpai_quality"]["status"], "validated_live")
        self.assertEqual(route["tenpai_quality"]["tenpai_endpoint_count"], 4)
        self.assertGreaterEqual(route["tenpai_quality"]["best_wait_type_count"], 2)

    def test_dead_exact_chiitoitsu_wait_is_impossible(self):
        context = normalize_yaku_context(
            hand=[
                "1m", "1m", "2m", "2m", "3p", "3p", "4p",
                "4p", "5s", "5s", "6s", "6s", "C",
            ],
            open_melds=[],
            visible_tiles=["C", "C", "C"],
            round_info={"bakaze": "E", "jikaze": "E"},
        )

        route = detect_yaku_routes(context)["yaku"]["chiitoitsu"]

        self.assertEqual(route["shanten"]["value"], 0)
        self.assertEqual(route["feasibility"], "impossible")
        self.assertEqual(route["availability"], "dead")
        self.assertEqual(route["tenpai_quality"]["status"], "dead")
        self.assertEqual(route["tenpai_quality"]["tenpai_endpoint_count"], 0)
        self.assertTrue(any(
            blocker["reason"] == "all_scorer_validated_waits_exhausted"
            for blocker in route["yaku_blockers"]
        ))

    def test_unsorted_called_chi_still_validates_open_tanyao_waits(self):
        context = normalize_yaku_context(
            hand=["2m", "4m", "6p", "6p", "5s", "5s", "C"],
            open_melds=[
                {"type": "chi", "tiles": ["7m", "8m", "6m"], "open": True},
                {"type": "pon", "tiles": ["8s", "8s", "8s"], "open": True},
            ],
            visible_tiles=[],
            round_info={"bakaze": "E", "jikaze": "N"},
        )

        route = detect_yaku_routes(context)["yaku"]["tanyao"]

        self.assertEqual(route["shanten"]["value"], 1)
        self.assertEqual(route["tenpai_quality"]["status"], "validated_live")
        self.assertIn("3m", route["estimated_improving_draws"])
        self.assertGreaterEqual(route["tenpai_quality"]["best_wait_type_count"], 2)

    def test_singleton_yakuhai_without_one_step_witness_is_two_away(self):
        context = normalize_yaku_context(
            hand=["2m", "4m", "6p", "6p", "5s", "5s", "C"],
            open_melds=[
                {"type": "chi", "tiles": ["6m", "7m", "8m"], "open": True},
                {"type": "pon", "tiles": ["8s", "8s", "8s"], "open": True},
            ],
            visible_tiles=[],
            round_info={"bakaze": "E", "jikaze": "S"},
        )

        route = detect_yaku_routes(context)["yaku"]["yakuhai_C"]

        self.assertEqual(route["shanten"]["value"], 2)
        self.assertEqual(route["route_state"], "none")

    def test_toitoi_tenpai_is_confirmed_and_concealed_routes_are_reported(self):
        source = self.source()
        source["hand"] = [
            "8m", "9m", "9m", "3p", "3p", "3p", "4p",
            "4p", "4p", "6p", "6p", "8p", "8p", "8p",
        ]
        source["drawn_tile"] = "9m"
        source["actual_discard"] = "8m"

        result = evaluate_decision(source)
        analysis = result["actual_evaluation"]["yaku_analysis"]

        self.assertIn("toitoi", analysis["confirmed_yaku"])
        self.assertIn("toitoi", analysis["yaku_tenpai"])
        self.assertEqual(analysis["yaku"]["toitoi"]["feasibility"], "possible")
        self.assertEqual(
            analysis["yaku"]["suuankou"]["ukeire"],
            {"9m": 2, "6p": 2},
        )
        self.assertEqual(
            analysis["yaku"]["suuankou"]["ukeire_witnesses"],
            [{
                "draws": ["9m", "6p"],
                "validation": "scorer_validated",
                "methods": ["tsumo"],
            }],
        )
        for name in ("sanankou", "suuankou", "iipeikou"):
            self.assertIn(name, analysis["yaku"])
        for name in ("sanshoku_doukou", "ryanpeikou"):
            self.assertIn(name, result["yaku_detector"]["supported_yaku"])

    def test_three_concealed_triplets_are_confirmed_but_hand_remains_one_shanten(self):
        source = self.source()
        source["hand"] = [
            "6m", "9m", "9m", "3p", "3p", "3p", "4p",
            "4p", "4p", "6p", "6p", "8p", "8p", "8p",
        ]
        source["drawn_tile"] = "6m"
        source["actual_discard"] = "9m"

        analysis = evaluate_decision(source)["actual_evaluation"]["yaku_analysis"]

        self.assertIn("sanankou", analysis["confirmed_yaku"])
        self.assertIn("sanankou", analysis["established_components"])
        self.assertEqual(analysis["yaku"]["sanankou"]["shanten"]["value"], 1)
        self.assertEqual(analysis["yaku"]["sanankou"]["feasibility"], "possible")
        self.assertEqual(
            analysis["yaku"]["suuankou"]["ukeire"],
            {"6m": 3, "9m": 2, "6p": 2},
        )
        self.assertEqual(
            analysis["yaku"]["suuankou"]["shanten"]["measurement"],
            "exact",
        )
        self.assertNotIn("pinfu", analysis["yaku"])
        self.assertEqual(
            analysis["yaku"]["iipeikou"]["shanten"]["value"], 2
        )

    def test_detector_does_not_change_efficiency_selection(self):
        source = self.source()
        expected = evaluate_discards(
            source["hand"],
            visible_tiles=source["visible_tiles"],
            open_melds=0,
        )[0]["discard"]
        result = evaluate_decision(source)
        self.assertEqual(result["best_efficiency_discard"], expected)

    def test_candidate_discard_updates_tanyao_obstructions(self):
        result = evaluate_decision(self.source())
        actual = result["actual_evaluation"]["yaku_analysis"]
        self.assertEqual(
            actual["opportunities"]["tanyao"]["metrics"]
            ["incompatible_concealed_tiles"],
            1,
        )

    def test_malformed_meld_is_isolated_from_evaluation(self):
        source = self.source()
        source["open_melds"] = [{"type": "pon", "tiles": ["F", "F"]}]
        # Keep a legal concealed tile count for one fixed meld.
        source["hand"] = source["hand"][:11]
        source["actual_discard"] = source["hand"][-1]
        result = evaluate_decision(source)
        analysis = result["actual_evaluation"]["yaku_analysis"]
        self.assertFalse(analysis["input_complete"])
        self.assertTrue(analysis["errors"])


class CorrectnessRegressionTests(unittest.TestCase):
    def context(self, hand, melds=None, visible=None, bakaze="E", jikaze="S"):
        return normalize_yaku_context(
            hand=hand,
            open_melds=[] if melds is None else melds,
            visible_tiles=[] if visible is None else visible,
            round_info={"bakaze": bakaze, "jikaze": jikaze},
        )

    def test_pinfu_rejects_value_wind_pair_and_accepts_nonvalue_pair(self):
        base = [
            "1m", "2m", "3m", "1p", "2p", "3p", "1s", "2s", "3s",
            "4m", "5m",
        ]
        value = detect_yaku_routes(self.context(base + ["E", "E"]))["yaku"]["pinfu"]
        self.assertEqual(value["feasibility"], "impossible")

        nonvalue = detect_yaku_routes(self.context(base + ["W", "W"]))
        self.assertIn("pinfu", nonvalue["yaku_tenpai"])
        self.assertEqual(set(nonvalue["yaku"]["pinfu"]["ukeire"]), {"3m", "6m"})

    def test_chiitoitsu_quad_counts_as_one_pair_not_two(self):
        routes = detect_yaku_routes(self.context([
            "1m", "1m", "1m", "1m", "2m", "2m", "3m", "3m",
            "4m", "4m", "5m", "5m", "6m",
        ]))["yaku"]
        self.assertEqual(routes["chiitoitsu"]["shanten"]["value"], 2)

    def test_honroutou_uses_chiitoitsu_shape(self):
        routes = detect_yaku_routes(self.context([
            "1m", "1m", "9m", "9m", "1p", "1p", "9p", "9p",
            "1s", "1s", "E", "E", "C",
        ]))["yaku"]
        self.assertEqual(routes["honroutou"]["shanten"]["value"], 0)

    def test_two_open_melds_make_sanankou_impossible(self):
        routes = detect_yaku_routes(self.context(
            ["3s", "3s", "3s", "4s", "4s", "5s", "6s"],
            melds=[
                {"type": "pon", "tiles": ["1m"] * 3, "open": True},
                {"type": "pon", "tiles": ["2p"] * 3, "open": True},
            ],
        ))["yaku"]
        self.assertEqual(routes["sanankou"]["feasibility"], "impossible")

    def test_sanankou_does_not_treat_two_pairs_as_one_shanten(self):
        routes = detect_yaku_routes(self.context([
            "1m", "2m", "3m", "4m", "4m", "5m", "7m", "8m", "9m",
            "1s", "1s", "2s", "3s",
        ]))["yaku"]
        self.assertEqual(routes["sanankou"]["shanten"]["value"], 3)

    def test_ankan_preserves_menzen_but_blocks_ryanpeikou(self):
        routes = detect_yaku_routes(self.context(
            ["1m", "2m", "3m", "1p", "2p", "3p", "4s", "5s", "5s", "6s"],
            melds=[{
                "type": "ankan", "tiles": ["9m"] * 4, "open": False,
            }],
        ))["yaku"]
        self.assertEqual(routes["ryanpeikou"]["feasibility"], "impossible")

    def test_legacy_meld_count_does_not_emit_confident_routes(self):
        ctx = normalize_yaku_context(
            hand=["1m", "2m", "3m", "4p", "5p", "6p", "7s", "8s", "9s", "E"],
            open_melds=1,
            visible_tiles=[],
            round_info={"bakaze": "E", "jikaze": "S"},
        )
        result = detect_yaku_routes(ctx)
        self.assertEqual(result["route_evidence_status"], "unknown_incomplete_meld_context")
        self.assertEqual(result["yaku"], {})

    def test_semantically_invalid_meld_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "valid chi"):
            self.context(
                ["2m"] * 10,
                melds=[{
                    "type": "chi", "tiles": ["1m", "1m", "1m"], "open": True,
                }],
            )

    def test_open_no_yaku_tenpai_is_explicit(self):
        ctx = self.context(
            ["2p", "3p", "4p", "4s", "5s", "6s", "7s", "8s", "5m", "5m"],
            melds=[{
                "type": "chi", "tiles": ["1m", "2m", "3m"], "open": True,
            }],
        )
        result = analyze_tenpai_legality(ctx)
        self.assertTrue(result["structural_tenpai"])
        self.assertTrue(result["open_no_yaku_tenpai"])
        self.assertEqual(set(result["waits"]), {"3s", "6s", "9s"})

    def test_open_hand_blocks_menzen_only_routes_but_not_open_routes(self):
        ctx = self.context(
            ["2p", "3p", "4p", "4s", "5s", "6s", "7s", "8s", "5m", "5m"],
            melds=[{
                "type": "chi", "tiles": ["1m", "2m", "3m"], "open": True,
            }],
        )
        routes = detect_yaku_routes(ctx)["yaku"]
        for name in ("pinfu", "iipeikou", "ryanpeikou", "chiitoitsu",
                     "kokushi", "suuankou", "chuuren_poutou"):
            self.assertEqual(routes[name]["feasibility"], "impossible", name)
            self.assertTrue(routes[name]["menzen_required"], name)
        self.assertTrue(routes["ittsu"]["open_allowed"])
        self.assertTrue(routes["ittsu"]["open_han_reduced"])

    def test_daisangen_zero_route_has_scorer_validated_wait(self):
        result = detect_yaku_routes(self.context([
            "P", "P", "P", "F", "F", "F", "C", "C",
            "1m", "2m", "3m", "7s", "7s",
        ]))
        route = result["yaku"]["daisangen"]
        self.assertEqual(route["shanten"]["value"], 0)
        self.assertEqual(route["ukeire"], {"C": 2})
        self.assertEqual(route["proof"]["validation"], "scorer_validated")
        self.assertIn("daisangen", result["yaku_tenpai"])

    def test_tsuuiisou_supports_seven_pairs_and_validates_wait(self):
        result = detect_yaku_routes(self.context([
            "E", "E", "S", "S", "W", "W", "N", "N",
            "P", "P", "F", "F", "C",
        ]))
        route = result["yaku"]["tsuuiisou"]
        self.assertEqual(route["shanten"]["value"], 0)
        self.assertEqual(route["ukeire"], {"C": 3})
        self.assertIn("tsuuiisou", result["yaku_tenpai"])

    def test_exact_transition_witnesses_are_grouped_by_target(self):
        route = detect_yaku_routes(self.context([
            "1m", "1m", "2m", "2m", "3p", "3p", "4p", "4p",
            "5s", "5s", "E", "S", "C",
        ]))["yaku"]["chiitoitsu"]
        witnesses = route["ukeire_witnesses"]
        self.assertIsInstance(witnesses, list)
        self.assertTrue(all("draws" in group for group in witnesses))
        self.assertTrue(all("post_draw_hand" not in group for group in witnesses))
        self.assertEqual(
            {draw for group in witnesses for draw in group["draws"]},
            set(route["ukeire"]),
        )
        self.assertLess(len(witnesses), len(route["ukeire"]))


if __name__ == "__main__":
    unittest.main()
