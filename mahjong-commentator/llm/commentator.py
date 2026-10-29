
import json
from pathlib import Path
from ollama import Client

from llm.prompts import SYSTEM_PROMPT
from llm.examples import EXAMPLE_OUTPUT

from utils.tile_format import sort_hand, format_hand


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
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        if self.use_few_shot:
            with EXAMPLE_PATH.open(encoding="utf-8") as f:
                example_decision = json.load(f)

            example_evidence = self.build_evidence(
                example_decision
            )

            messages.extend([
                {
                    "role": "user",
                    "content": json.dumps(
                        example_evidence,
                        ensure_ascii=False,
                    ),
                },
                {
                    "role": "assistant",
                    "content": EXAMPLE_OUTPUT,
                },
            ])

        actual_evidence = self.build_evidence(decision)

        messages.append({
            "role": "user",
            "content": (
                "Generate commentary for this NEW decision. "
                "Follow the example's format, not its facts.\n\n"
                + json.dumps(
                    actual_evidence,
                    ensure_ascii=False,
                )
            ),
        })

        return messages

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

        return response.message.content
