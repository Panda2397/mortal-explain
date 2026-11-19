import json
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from interact.coach import InteractiveCoach
from interact.evidence import (
    build_turn_evidence,
    format_turn_summary,
    rank_discards_by_yaku_coverage,
    rank_discards_for_yaku,
    rank_efficiency_discards,
)
from interact.session import ReplaySession
from interact.cli import (
    _colorize_summary,
    _set_color_enabled,
    parser as cli_parser,
    print_yaku_discards,
)
from evaluator.decision_evaluator import best_discards_by_yaku


def evaluated(discard="1m"):
    route = {
        "shanten": {"value": 1, "measurement": "lower_bound"},
        "ukeire": {"2m": 3},
        "estimated_improving_draws": {"2m": 3},
        "feasibility": "possible",
        "yaku_blockers": [],
    }
    candidate = {
        "discard": discard,
        "shanten": 1,
        "ukeire": 3,
        "effective_tiles": {"2m": 3},
        "yaku_analysis": {"confirmed_yaku": [], "yaku": {"tanyao": route}},
    }
    return {
        "player": 0,
        "round": {"bakaze": "E", "jikaze": "S"},
        "turn": 1,
        "hand": ["1m", "2m"],
        "drawn_tile": "2m",
        "open_melds": [],
        "dora_indicators": [],
        "discards_by_player": {"0": []},
        "actual_discard": discard,
        "actual_evaluation": candidate,
        "best_efficiency_discard": discard,
        "best_evaluation": candidate,
        "all_candidates": [candidate],
        "yaku_comparison": {"deltas": []},
    }


class SessionTests(unittest.TestCase):
    def test_processed_session_navigates_and_caches(self):
        values = [evaluated("1m"), evaluated("2m")]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decisions.json"
            path.write_text(json.dumps(values), encoding="utf-8")
            session = ReplaySession.from_processed(path)
        self.assertEqual(len(session), 2)
        self.assertEqual(session.current["actual_discard"], "1m")
        self.assertEqual(session.move(1)["actual_discard"], "2m")
        self.assertEqual(session.move(10)["actual_discard"], "2m")
        self.assertEqual(session.go(0)["actual_discard"], "1m")

    def test_processed_session_backfills_call_and_clears_stale_draw(self):
        first = evaluated("1m")
        second = deepcopy(evaluated("9m"))
        second["turn"] = 2
        second["drawn_tile"] = "1m"
        second["open_melds"] = [{
            "type": "pon", "tiles": ["5m"] * 3,
            "called_tile": "5m", "from_player": 2, "open": True,
        }]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decisions.json"
            path.write_text(json.dumps([first, second]), encoding="utf-8")
            session = ReplaySession.from_processed(path)
            current = session.go(1)

        self.assertIsNone(current["drawn_tile"])
        self.assertEqual(current["preceding_action"], {
            "type": "pon", "tile": "5m", "from_player": 2,
        })

    def test_candidate_lookup(self):
        session = ReplaySession([evaluated()])
        session._cache[0] = evaluated()
        self.assertIsNotNone(session.candidate("1m"))
        self.assertIsNone(session.candidate("9s"))


class EvidenceTests(unittest.TestCase):
    def test_yaku_discard_ranking_prefers_exact_route_over_shorter_bound(self):
        estimated = evaluated("1m")["actual_evaluation"]
        estimated["yaku_analysis"]["yaku"]["tanyao"].update({
            "route_state": "none",
            "availability": "unknown",
            "proof": {"validation": "unvalidated"},
        })
        exact = deepcopy(estimated)
        exact["discard"] = "2m"
        exact["yaku_analysis"]["yaku"]["tanyao"].update({
            "shanten": {"value": 2, "measurement": "exact"},
            "proof": {"validation": "exact_transition"},
        })

        result = best_discards_by_yaku([estimated, exact])

        self.assertEqual(result["tanyao"]["discard"], "2m")

    def test_dead_route_is_excluded_from_discard_options(self):
        decision = evaluated()
        route = decision["actual_evaluation"]["yaku_analysis"]["yaku"]["tanyao"]
        route.update({
            "availability": "dead",
            "tenpai_quality": {"status": "dead"},
        })

        evidence = build_turn_evidence(decision)

        self.assertEqual(evidence["discard_options"][0]["nearby_yaku"], [])

    def test_cli_color_can_be_enabled_and_disabled(self):
        try:
            _set_color_enabled(True)
            colored = _colorize_summary(
                "Decision 1 | draw 2m | discard 1m\n"
                "Efficiency: 1 shanten, 4 ukeire"
            )
            self.assertIn("\033[", colored)
            _set_color_enabled(False)
            plain = _colorize_summary("Decision 1 | discard 1m")
            self.assertNotIn("\033[", plain)
        finally:
            _set_color_enabled(False)

    def test_cli_accepts_no_color_option(self):
        args = cli_parser().parse_args([
            "--decisions", "decisions.json", "--no-color",
        ])
        self.assertTrue(args.no_color)

    def test_compact_evidence_contains_yaku_not_all_candidates(self):
        evidence = build_turn_evidence(evaluated())
        self.assertIn("nearby_yaku", evidence["actual"])
        self.assertNotIn("all_candidates", evidence)
        self.assertEqual(evidence["actual"]["discard"], "1m")
        self.assertIsNone(evidence["comparison"])
        self.assertTrue(evidence["comparison_same_as_actual"])
        self.assertIn("discard_options", evidence)
        self.assertLessEqual(len(evidence["discard_options"]), 5)

    def test_llm_discard_options_are_compact_and_limited_to_five(self):
        decision = evaluated()
        decision["all_candidates"] = [
            {**deepcopy(decision["actual_evaluation"]), "discard": f"{rank}m"}
            for rank in range(1, 8)
        ]

        options = build_turn_evidence(decision)["discard_options"]

        self.assertEqual(len(options), 5)
        self.assertTrue(all("nearby_yaku" in option for option in options))
        self.assertTrue(all(
            "ukeire_witnesses" not in route
            for option in options for route in option["nearby_yaku"]
        ))

    def test_llm_evidence_only_contains_yaku_within_one_shanten(self):
        decision = evaluated()
        routes = decision["actual_evaluation"]["yaku_analysis"]["yaku"]
        routes["toitoi"] = {
            "shanten": {"value": 3, "measurement": "exact"},
            "feasibility": "possible",
            "ukeire": {"9m": 2},
            "ukeire_witnesses": [{"draws": ["9m"]}],
            "yaku_blockers": [],
        }
        routes["sanankou"] = {
            "shanten": {"value": 2, "measurement": "lower_bound"},
            "feasibility": "possible",
            "ukeire": {},
            "estimated_improving_draws": {"3p": 3},
            "ukeire_witnesses": [{"draws": ["3p"]}],
            "yaku_blockers": [],
        }

        nearby = build_turn_evidence(decision)["actual"]["nearby_yaku"]

        self.assertNotIn("toitoi", nearby)
        self.assertIn("sanankou", nearby)
        self.assertNotIn("ukeire_witnesses", nearby["sanankou"])

    def test_summary_shows_measurement(self):
        summary = format_turn_summary(evaluated())
        self.assertIn("tanyao: 1 (lower_bound)", summary)
        self.assertIn("[2m - 3] 3 ukeire", summary)
        self.assertIn("yaku-discard=1m", summary)
        self.assertIn("estimated-improving=[2m - 3] 3", summary)
        nearby = summary.split("Nearby yaku:", 1)[1]
        self.assertNotIn("ukeire=", nearby)
        self.assertIn("\n\n=====\n\n", summary)
        self.assertIn("Yaku recommended discard:", summary)
        self.assertLess(
            summary.index("Yaku recommended discard:"),
            summary.index("Nearby yaku:"),
        )
        self.assertIn("#1 discard 1m", summary)

    def test_summary_shows_live_tenpai_quality(self):
        decision = evaluated()
        decision["actual_evaluation"]["yaku_analysis"]["yaku"]["tanyao"][
            "tenpai_quality"
        ] = {
            "status": "validated_live",
            "tenpai_endpoint_count": 3,
            "best_wait_type_count": 2,
            "best_live_wait_copies": 7,
        }

        summary = format_turn_summary(decision)

        self.assertIn("live-tenpai=3", summary)
        self.assertIn("best-wait=2 types/7 copies", summary)

    def test_summary_uses_yaku_specific_current_hand_discard(self):
        decision = evaluated("2m")
        yaku_candidate = deepcopy(decision["actual_evaluation"])
        yaku_candidate["discard"] = "1m"
        yaku_candidate["yaku_analysis"]["yaku"]["tanyao"]["shanten"]["value"] = 0
        decision["all_candidates"] = [decision["actual_evaluation"], yaku_candidate]
        decision["yaku_discard_recommendations"] = best_discards_by_yaku(
            decision["all_candidates"]
        )

        summary = format_turn_summary(decision)

        self.assertIn("yaku-discard=1m", summary)
        self.assertNotIn("yaku-discard=2m", summary)

    def test_summary_places_latest_draw_at_right_of_hand(self):
        decision = evaluated()
        decision["hand"] = ["9m", "1m", "2m", "3p"]
        decision["drawn_tile"] = "1m"

        summary = format_turn_summary(decision)

        self.assertIn("Hand: 2m 9m 3p 1m", summary)

    def test_summary_shows_call_and_open_melds(self):
        decision = evaluated("9m")
        decision["drawn_tile"] = None
        decision["preceding_action"] = {
            "type": "chi", "tile": "7s", "from_player": 3,
        }
        decision["open_melds"] = [{
            "type": "chi", "tiles": ["5s", "6s", "7s"],
            "called_tile": "7s", "from_player": 3, "open": True,
        }]

        summary = format_turn_summary(decision)

        self.assertIn("Decision 1 | chi 7s from player 3 | discard 9m", summary)
        self.assertIn(
            "Open melds: chi [5s 6s 7s] called 7s from player 3", summary
        )
        self.assertNotIn("| draw ", summary.splitlines()[0])

    def test_summary_ignores_yaku_more_than_one_shanten_away(self):
        decision = evaluated()
        decision["actual_evaluation"]["yaku_analysis"]["yaku"]["tanyao"]["shanten"]["value"] = 3

        summary = format_turn_summary(decision)

        self.assertNotIn("tanyao:", summary)

    def test_specific_yaku_ranks_all_discards_and_marks_missing_route(self):
        decision = evaluated()
        worse = evaluated("9m")["actual_evaluation"]
        worse["shanten"] = 0
        worse["ukeire"] = 8
        worse["yaku_analysis"]["yaku"] = {}
        better = evaluated("2m")["actual_evaluation"]
        better["yaku_analysis"]["yaku"]["tanyao"]["shanten"]["value"] = 0
        decision["all_candidates"] = [worse, decision["actual_evaluation"], better]

        rows = rank_discards_for_yaku(decision, "TANYAO")

        self.assertEqual([row["discard"] for row in rows], ["2m", "1m", "9m"])
        self.assertEqual(rows[-1]["feasibility"], "not_reported")

    def test_yaku_coverage_prefers_lower_shanten_before_more_routes(self):
        decision = evaluated()
        broad = evaluated("2m")["actual_evaluation"]
        broad["yaku_analysis"]["yaku"]["toitoi"] = {
            "shanten": {"value": 2, "measurement": "exact"},
            "ukeire": {},
            "feasibility": "possible",
            "yaku_blockers": [],
        }
        efficient = evaluated("9m")["actual_evaluation"]
        efficient["shanten"] = 0
        efficient["ukeire"] = 20
        decision["all_candidates"] = [efficient, broad]

        rows = rank_discards_by_yaku_coverage(decision)

        self.assertEqual(rows[0]["discard"], "9m")
        self.assertEqual(rows[0]["ordinary_shanten"], 0)

    def test_yaku_coverage_breaks_equal_shanten_by_more_routes(self):
        decision = evaluated()
        broad = evaluated("2m")["actual_evaluation"]
        broad["yaku_analysis"]["yaku"]["toitoi"] = {
            "shanten": {"value": 2, "measurement": "exact"},
            "ukeire": {},
            "feasibility": "possible",
            "yaku_blockers": [],
        }
        decision["all_candidates"] = [decision["actual_evaluation"], broad]

        rows = rank_discards_by_yaku_coverage(decision)

        self.assertEqual(rows[0]["discard"], "2m")
        self.assertEqual(rows[0]["yaku_count"], 2)

    def test_efficiency_recommendations_include_yaku_and_respect_limit(self):
        decision = evaluated()
        high_ukeire = evaluated("2m")["actual_evaluation"]
        high_ukeire["ukeire"] = 8
        lower_shanten = evaluated("3m")["actual_evaluation"]
        lower_shanten["shanten"] = 0
        lower_shanten["ukeire"] = 2
        decision["all_candidates"] = [decision["actual_evaluation"], high_ukeire, lower_shanten]

        rows = rank_efficiency_discards(decision, 2)

        self.assertEqual([row["discard"] for row in rows], ["3m", "2m"])
        self.assertEqual(rows[0]["yaku"], ["tanyao"])
        self.assertEqual(rows[0]["effective_tiles"], ["2m"])

    def test_recommendations_ignore_distant_yaku(self):
        decision = evaluated()
        route = decision["actual_evaluation"]["yaku_analysis"]["yaku"]["tanyao"]
        route["shanten"]["value"] = 3

        rows = rank_efficiency_discards(decision)

        self.assertEqual(rows[0]["shanten"], 1)
        self.assertEqual(rows[0]["yaku"], [])

    def test_recommendations_do_not_present_pinfu_with_value_honor_pair(self):
        decision = evaluated()
        pinfu = {
            "shanten": {"value": 2, "measurement": "lower_bound"},
            "ukeire": {"3m": 3},
            "feasibility": "possible",
            "yaku_blockers": [
                {"type": "concealed_tile", "severity": "removable",
                 "reason": "value_honor_cannot_be_pinfu_pair", "tile": "F"},
                {"type": "concealed_tile", "severity": "removable",
                 "reason": "value_honor_cannot_be_pinfu_pair", "tile": "F"},
            ],
        }
        decision["actual_evaluation"]["yaku_analysis"]["yaku"]["pinfu"] = pinfu

        rows = rank_efficiency_discards(decision)

        self.assertNotIn("pinfu", rows[0]["yaku"])

    def test_yaku_discard_formats_structured_blockers(self):
        decision = evaluated()
        route = decision["actual_evaluation"]["yaku_analysis"]["yaku"]["tanyao"]
        route["yaku_blockers"] = [{
            "type": "fixed_meld", "reason": "contains_terminal_or_honor",
        }]
        output = io.StringIO()
        with redirect_stdout(output):
            print_yaku_discards(decision, "tanyao")
        self.assertIn("fixed_meld:contains_terminal_or_honor", output.getvalue())

    def test_selected_comparison_recomputes_yaku_changes(self):
        decision = evaluated("1m")
        alternative = {
            **decision["actual_evaluation"],
            "discard": "2m",
            "yaku_analysis": {
                "opportunities": {},
                "yaku": {
                    "tanyao": {
                        **decision["actual_evaluation"]["yaku_analysis"]["yaku"]["tanyao"],
                        "shanten": {"value": 0, "measurement": "lower_bound"},
                    }
                },
            },
        }
        decision["all_candidates"].append(alternative)
        decision["yaku_comparison"] = {"deltas": [{"yaku": "stale"}]}
        evidence = build_turn_evidence(decision, "2m")
        self.assertNotIn("stale", [item["yaku"] for item in evidence["yaku_changes"]])
        self.assertIn("tanyao", [item["yaku"] for item in evidence["yaku_changes"]])


class _FakeClient:
    def __init__(self):
        self.messages = None

    def chat(self, **kwargs):
        self.messages = kwargs["messages"]
        return SimpleNamespace(message=SimpleNamespace(content="Grounded answer"))


class CoachTests(unittest.TestCase):
    def test_coach_sends_verified_evidence_and_keeps_short_history(self):
        coach = InteractiveCoach()
        fake = _FakeClient()
        coach.client = fake
        answer = coach.ask(evaluated(), "Which yaku is close?")
        self.assertEqual(answer, "Grounded answer")
        prompt = fake.messages[-1]["content"]
        self.assertIn("Verified current-turn evidence", prompt)
        self.assertIn("lower_bound", prompt)
        self.assertEqual(len(coach.history), 2)
        coach.clear_history()
        self.assertEqual(coach.history, [])

    def test_coach_drops_old_history_to_preserve_current_evidence(self):
        coach = InteractiveCoach()
        fake = _FakeClient()
        coach.client = fake
        coach.history = [
            {"role": "user" if index % 2 == 0 else "assistant",
             "content": "x" * 9000}
            for index in range(6)
        ]

        coach.ask(evaluated(), "What is close?")

        self.assertLess(len(fake.messages), 8)
        self.assertIn("Verified current-turn evidence", fake.messages[-1]["content"])


if __name__ == "__main__":
    unittest.main()
