
import json
import re
from pathlib import Path
from ollama import Client

from llm.prompts import SYSTEM_PROMPT
from llm.examples import EXAMPLE_OUTPUT

from utils.tile_format import sort_hand, format_hand, tile_to_chinese


EXAMPLE_PATH = Path("data/examples/discard_example.json")


class MahjongCommentator:
    def __init__(
        self,
        model="deepseek-r1:8b",
        use_few_shot=True,
    ):
        self.model = model
        self.use_few_shot = use_few_shot
        self.client = Client(host="http://localhost:11434")
        self.last_explanation_source = "unknown"

    def build_evidence(self, decision: dict) -> dict:
        fields = [
            "player",
            "round",
            "turn",
            "hand",
            "drawn_tile",
            "open_melds",
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
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        actual_evidence = self.build_evidence(decision)
        actual = actual_evidence["actual_evaluation"]
        best = actual_evidence["best_evaluation"]
        reasons = []
        if best["shanten"] < actual["shanten"]:
            reasons.append("RECOMMENDED_LOWER_SHANTEN")
        elif best["shanten"] == actual["shanten"]:
            reasons.append("SAME_SHANTEN")
        if best["ukeire"] > actual["ukeire"]:
            reasons.append("RECOMMENDED_HIGHER_UKEIRE")
        elif best["ukeire"] == actual["ukeire"]:
            reasons.append("SAME_UKEIRE")
        if actual_evidence["actual_discard"] == actual_evidence["best_efficiency_discard"]:
            reasons.append("ACTUAL_EQUALS_RECOMMENDATION")

        messages.append({
            "role": "user",
            "content": (
                "Generate only one short Traditional Chinese strategy paragraph. "
                "Do not output headings, tiles, numbers, or background fields; "
                "Python will render those from verified evidence. Paraphrase only "
                "these evaluator reason codes: " + ", ".join(reasons) + ".\n\n"
                + json.dumps(
                    actual_evidence,
                    ensure_ascii=False,
                )
            ),
        })

        return messages

    @staticmethod
    def _tiles(tiles: list[str]) -> str:
        return "、".join(tile_to_chinese(t) for t in tiles) or "未提供"

    def render_grounded_commentary(self, decision: dict, explanation: str) -> str:
        """Render factual fields in Python; only prose comes from the LLM."""
        evidence = self.build_evidence(decision)
        round_info = evidence.get("round", {})
        actual = evidence["actual_evaluation"]
        best = evidence["best_evaluation"]
        drawn = evidence.get("drawn_tile")
        drawn_text = tile_to_chinese(drawn) if drawn else "未提供"
        open_melds = evidence.get("open_melds", 0)
        open_text = "無" if not open_melds else str(open_melds)
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

        blocks = actual.get("blocks", [])
        route = blocks[0].get("route") if blocks else None
        route_text = {"regular": "一般型", "chiitoitsu": "七對子", "kokushi": "國士無雙"}.get(route, "未提供")

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
牌效結果：{actual['shanten']}向聽，入章數{actual['ukeire']}。

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
        if text and not contains_tile and not contains_number:
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
        response = self.client.chat(
            model=self.model,
            messages=self.build_messages(decision),
            options={
                "temperature": 0,
                "seed": 42,
                "num_ctx": 8192,
            },
            think=True,
        )

        return self.render_grounded_commentary(decision, response.message.content)
