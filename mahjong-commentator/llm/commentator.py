
import json
import re
from pathlib import Path
from ollama import Client

from llm.prompts import INDEPENDENT_SYSTEM_PROMPT, SYSTEM_PROMPT
from llm.examples import EXAMPLE_OUTPUT
from evaluator.comparison import (
    VERDICTS,
    efficiency_reason_codes,
    efficiency_verdict,
)
from evaluator.python_baseline import baseline_explanation

from utils.tile_format import sort_hand, format_hand, tile_to_chinese


EXAMPLE_PATH = Path("data/examples/discard_example.json")


class MahjongCommentator:
    def __init__(
        self,
        model="deepseek-r1:8b",
        use_few_shot=True,
        treatment="structured_copy",
        think=True,
        temperature=0.0,
        seed=42,
        num_ctx=8192,
        num_predict=1024,
    ):
        self.model = model
        self.use_few_shot = use_few_shot
        self.treatment = treatment
        self.think = think
        self.temperature = temperature
        self.seed = seed
        self.num_ctx = num_ctx
        self.num_predict = num_predict
        self.client = Client(host="http://localhost:11434")
        self.last_explanation_source = "unknown"
        self.last_raw_response = ""
        self.last_parsed_response = None
        self.last_fallback_reason = None
        self.last_response_metadata = {}

    def generation_options(self) -> dict:
        return {
            "temperature": self.temperature,
            "seed": self.seed,
            "num_ctx": self.num_ctx,
            "num_predict": self.num_predict,
            "format": "json",
            "think": self.think,
        }

    @staticmethod
    def comparison_evidence(decision: dict) -> tuple[str, list[str]]:
        return efficiency_verdict(decision), efficiency_reason_codes(decision)

    def build_evidence(self, decision: dict) -> dict:
        fields = [
            "player",
            "round",
            "turn",
            "hand",
            "drawn_tile",
            "open_melds",
            "open_meld_count",
            "visible_tiles",
            "dora_indicators",
            "actual_discard",
            "actual_evaluation",
            "best_efficiency_discard",
            "best_evaluation",
            "equally_efficient_discards",
        ]

        evidence = {
            key: decision[key]
            for key in fields
            if key in decision
        }

        if isinstance(evidence.get("hand"), list):
            evidence["hand"] = sort_hand(evidence["hand"])
            evidence["hand_display"] = format_hand(
                evidence["hand"]
            )

        return evidence

    def build_messages(self, decision: dict) -> list:
        actual_evidence = self.build_evidence(decision)
        expected_comparison, reasons = self.comparison_evidence(actual_evidence)
        actual_routes = actual_evidence["actual_evaluation"].get(
            "shanten_by_type", {}
        ).get("best_routes", [])
        raw_melds = actual_evidence.get("open_melds", [])
        meld_count = actual_evidence.get(
            "open_meld_count",
            len(raw_melds) if isinstance(raw_melds, list) else int(raw_melds),
        )
        meld_context = {
            "open_meld_count": meld_count,
            "open_melds": raw_melds if isinstance(raw_melds, list) else [],
        }
        alternative_routes = actual_evidence["best_evaluation"].get(
            "shanten_by_type", {}
        ).get("best_routes", [])

        if self.treatment == "independent_grounded":
            actual = actual_evidence["actual_evaluation"]
            alternative = actual_evidence["best_evaluation"]
            payload = {
                "actual_discard": actual_evidence["actual_discard"],
                "alternative_discard": actual_evidence["best_efficiency_discard"],
                "actual": {
                    "shanten": actual["shanten"],
                    "ukeire": actual["ukeire"],
                },
                "alternative": {
                    "shanten": alternative["shanten"],
                    "ukeire": alternative["ukeire"],
                },
                "route_context": {
                    "actual_best_routes": actual_routes,
                    "alternative_best_routes": alternative_routes,
                },
                "meld_context": meld_context,
            }
            return [
                {"role": "system", "content": INDEPENDENT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": "Classify and explain this evidence.\n\n"
                    + json.dumps(payload, ensure_ascii=False),
                },
            ]

        if self.treatment != "structured_copy":
            raise ValueError(f"Unknown LLM treatment: {self.treatment}")

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        messages.append({
            "role": "user",
            "content": (
                "Return JSON only. Explain the supplied verified conclusion. "
                "Copy every allowed_reason_codes value exactly once into "
                "reason_codes_used.\n\n"
                + json.dumps({
                    "expected_comparison": expected_comparison,
                    "allowed_reason_codes": reasons,
                    "route_context": {
                        "actual_best_routes": actual_routes,
                        "alternative_best_routes": alternative_routes,
                    },
                    "meld_context": meld_context,
                }, ensure_ascii=False)
            ),
        })

        return messages

    @staticmethod
    def parse_llm_response(raw: str) -> dict | None:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        required = {"comparison", "reason_codes_used", "explanation"}
        if not isinstance(parsed, dict) or set(parsed) != required:
            return None
        legacy_verdicts = {"actual_better", "recommended_better", "equal"}
        if parsed["comparison"] not in VERDICTS | legacy_verdicts:
            return None
        if not isinstance(parsed["reason_codes_used"], list) or not all(
            isinstance(code, str) for code in parsed["reason_codes_used"]
        ):
            return None
        if not isinstance(parsed["explanation"], str):
            return None
        return parsed

    @staticmethod
    def _tiles(tiles: list[str]) -> str:
        return "、".join(tile_to_chinese(t) for t in tiles) or "未提供"

    @classmethod
    def _melds(cls, melds, meld_count: int) -> str:
        if not meld_count:
            return "無"
        if not isinstance(melds, list) or not melds:
            return f"{meld_count}組（牌張未提供）"
        names = {
            "chi": "吃",
            "pon": "碰",
            "daiminkan": "大明槓",
            "ankan": "暗槓",
            "kakan": "加槓",
        }
        return "；".join(
            f"{names.get(meld.get('type'), meld.get('type', '副露'))}"
            f"（{cls._tiles(sort_hand(meld.get('tiles', [])))}）"
            for meld in melds
        )

    def render_grounded_commentary(self, decision: dict, explanation: str) -> str:
        """Render factual fields in Python; only prose comes from the LLM."""
        evidence = self.build_evidence(decision)
        round_info = evidence.get("round", {})
        actual = evidence["actual_evaluation"]
        best = evidence["best_evaluation"]
        drawn = evidence.get("drawn_tile")
        drawn_text = tile_to_chinese(drawn) if drawn else "未提供"
        open_melds = evidence.get("open_melds", [])
        open_meld_count = evidence.get(
            "open_meld_count",
            len(open_melds) if isinstance(open_melds, list) else int(open_melds),
        )
        open_text = self._melds(open_melds, open_meld_count)
        wind_names = {
            "E": "東風",
            "S": "南風",
            "W": "西風",
            "N": "北風",
        }
        wind_short_names = {
            "E": "東",
            "S": "南",
            "W": "西",
            "N": "北",
        }
        bakaze = round_info.get("bakaze")
        jikaze = round_info.get("jikaze")
        bakaze_text = wind_names.get(bakaze, bakaze or "未提供")
        jikaze_text = wind_names.get(jikaze, jikaze or "未提供")
        kyoku = round_info.get("kyoku")
        kyoku_text = (
            f"{wind_short_names.get(bakaze, bakaze or '未提供')}{kyoku}局"
            if kyoku is not None
            else "未提供"
        )
        actual_discard = tile_to_chinese(evidence["actual_discard"])
        best_discard = tile_to_chinese(evidence["best_efficiency_discard"])
        effective = self._tiles(list(actual.get("effective_tiles", {}).keys()))
        best_effective = self._tiles(list(best.get("effective_tiles", {}).keys()))

        best_routes = actual.get("shanten_by_type", {}).get("best_routes", [])
        route_names = {
            "regular": "一般型",
            "chiitoitsu": "七對子",
            "kokushi": "國士無雙",
        }
        route_text = "、".join(
            route_names.get(route, route) for route in best_routes
        ) or "未提供"

        if evidence["actual_discard"] == evidence["best_efficiency_discard"]:
            decision_text = f"實際棄牌與牌效推薦均為{actual_discard}。"
            alternative = "沒有不同的替代棄牌可供比較。"
        else:
            decision_text = f"實際棄牌：{actual_discard}；牌效推薦：{best_discard}。"
            alternative = f"替代棄牌：{best_discard}，向聽數{best['shanten']}，入章數{best['ukeire']}，有效牌為{best_effective}。"

        explanation, source = self._safe_strategy_explanation(
            explanation,
            actual=actual,
            best=best,
            same_discard=(evidence["actual_discard"] == evidence["best_efficiency_discard"]),
            allowed_routes=set(best_routes),
        )
        self.last_explanation_source = source

        fixed = f"""### 1. 局面背景

場風：{bakaze_text}
自風：{jikaze_text}
局數：{kyoku_text}
本場：{round_info.get('honba', '未提供')}本場
巡目：第{evidence.get('turn', '未提供')}巡
分數：{' / '.join(map(str, round_info.get('scores', []))) or '未提供'}
手牌：{evidence.get('hand_display', '未提供')}
摸牌：{drawn_text}
副露：{open_text}
牌型路線：{route_text}

### 2. 棄牌決策

{decision_text}
推薦依據：向聽數{best['shanten']}，入章數{best['ukeire']}；有效牌為{best_effective}。

### 3. 棄牌分析

**實際棄牌：{actual_discard}**
牌效結果：{actual['shanten']}向聽，入章數{actual['ukeire']}；有效牌為{effective}。

**替代棄牌**
{alternative}

### 4. 綜合解釋

{explanation.strip()}
"""
        return fixed

    @staticmethod
    def _safe_strategy_explanation(
        explanation: str,
        *,
        actual: dict,
        best: dict,
        same_discard: bool,
        allowed_routes: set[str],
    ) -> str:
        """Reject prose that tries to reproduce evaluator facts inaccurately."""
        text = explanation.strip()
        # The model is not allowed to restate tile identities or numbers. Those
        # are rendered above from verified evidence.
        contains_tile = bool(re.search(
            r"[1-9][mps萬筒索]|(?:東風|南風|西風|北風|白板|發財|紅中)",
            text,
        ))
        contains_number = bool(re.search(r"\d", text))
        route_terms = {
            "一般型": "regular",
            "七對子": "chiitoitsu",
            "國士無雙": "kokushi",
        }
        contains_wrong_route = any(
            term in text and route not in allowed_routes
            for term, route in route_terms.items()
        )
        if (
            text
            and not contains_tile
            and not contains_number
            and not contains_wrong_route
        ):
            return text, "llm"

        if same_discard:
            return "實際棄牌與評估器推薦一致；在目前評估規則下，沒有不同棄牌需要比較。", "fallback"

        if best["ukeire"] > actual["ukeire"]:
            relation = "推薦棄牌的入章數較高"
        elif best["ukeire"] < actual["ukeire"]:
            relation = "推薦棄牌的入章數較低"
        else:
            relation = "兩種棄牌的入章數相同"

        if best["shanten"] < actual["shanten"]:
            shanten_relation = "推薦棄牌的向聽數較低"
        elif best["shanten"] > actual["shanten"]:
            shanten_relation = "推薦棄牌的向聽數較高"
        else:
            shanten_relation = "兩種棄牌的向聽數相同"

        return f"{shanten_relation}，而且{relation}；因此應以評估器的效率推薦為準。", "fallback"

    def generate(self, decision: dict) -> str:
        messages = self.build_messages(decision)
        response = self.client.chat(
            model=self.model,
            messages=messages,
            format="json",
            options={
                "temperature": self.temperature,
                "seed": self.seed,
                "num_ctx": self.num_ctx,
                "num_predict": self.num_predict,
            },
            think=self.think,
        )

        raw = response.message.content
        parsed = self.parse_llm_response(raw)
        self.last_raw_response = raw
        self.last_parsed_response = parsed
        self.last_response_metadata = {
            key: getattr(response, key, None)
            for key in (
                "model",
                "created_at",
                "total_duration",
                "load_duration",
                "prompt_eval_count",
                "prompt_eval_duration",
                "eval_count",
                "eval_duration",
            )
        }
        thinking = getattr(response.message, "thinking", None)
        self.last_response_metadata["thinking_chars"] = len(thinking or "")
        expected_comparison, allowed_reasons = self.comparison_evidence(decision)
        response_is_grounded = (
            parsed is not None
            and parsed["comparison"] == expected_comparison
            and set(parsed["reason_codes_used"]) == set(allowed_reasons)
        )
        if parsed is None:
            self.last_fallback_reason = "invalid_json_or_schema"
        elif parsed["comparison"] != expected_comparison:
            self.last_fallback_reason = "incorrect_efficiency_verdict"
        elif set(parsed["reason_codes_used"]) != set(allowed_reasons):
            self.last_fallback_reason = "reason_code_mismatch"
        else:
            self.last_fallback_reason = None
        explanation = parsed["explanation"] if response_is_grounded else ""
        commentary = self.render_grounded_commentary(decision, explanation)
        if self.last_explanation_source == "fallback" and self.last_fallback_reason is None:
            self.last_fallback_reason = "unsafe_explanation_content"
        return commentary

    def generate_python_baseline(self, decision: dict) -> str:
        """Render the no-LLM baseline using the production factual sections."""
        self.last_raw_response = ""
        self.last_parsed_response = None
        self.last_fallback_reason = None
        self.last_response_metadata = {}
        commentary = self.render_grounded_commentary(
            decision,
            baseline_explanation(decision),
        )
        self.last_explanation_source = "python_baseline"
        return commentary
