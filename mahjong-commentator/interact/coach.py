"""Grounded conversational wrapper around Ollama."""

import json

from ollama import Client

from interact.evidence import build_turn_evidence


SYSTEM_PROMPT = """You are an interactive Riichi Mahjong coach.
Use only the verified JSON evidence supplied for the current decision.
Python, not you, calculates hand contents, shanten, ukeire, yaku feasibility,
yaku blockers, and remaining copies. Never invent tiles, probabilities,
expected value, or Mortal's internal reasoning. Treat `lower_bound` and
`heuristic` yaku distances as estimates and say so when relevant. Dora is
bonus value, not a qualifying yaku. Answer the user's question directly and
concisely. You may explain strategic trade-offs, but do not claim an overall
optimal discard when defense, score situation, or exact yaku search is absent.
"""

MAX_ESTIMATED_INPUT_TOKENS = 6500


def _estimated_tokens(text: str) -> int:
    """Conservatively estimate mixed JSON/English/CJK prompt tokens."""
    ascii_count = sum(ord(character) < 128 for character in text)
    non_ascii_count = len(text) - ascii_count
    return (ascii_count + 3) // 4 + non_ascii_count


def _message_tokens(messages: list[dict]) -> int:
    return sum(_estimated_tokens(message.get("content", "")) for message in messages)


class InteractiveCoach:
    def __init__(self, model="qwen3:8b", host="http://localhost:11434"):
        self.model = model
        self.client = Client(host=host)
        self.history: list[dict] = []

    def clear_history(self):
        self.history.clear()

    def ask(self, decision: dict, question: str, comparison_discard: str | None = None) -> str:
        evidence = build_turn_evidence(decision, comparison_discard)
        prompt = (
            f"User question: {question}\n\nVerified current-turn evidence:\n"
            + json.dumps(evidence, ensure_ascii=False)
        )
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self.history[-6:])
        messages.append({"role": "user", "content": prompt})
        # Prefer dropping old conversation pairs over truncating verified
        # current-turn evidence. Leave context space for the model's answer.
        while len(messages) > 2 and _message_tokens(messages) > MAX_ESTIMATED_INPUT_TOKENS:
            del messages[1:3]
        estimated = _message_tokens(messages)
        if estimated > MAX_ESTIMATED_INPUT_TOKENS:
            raise ValueError(
                "Current question and evidence are too large for the 8192-token "
                f"context (estimated input: {estimated} tokens)."
            )
        response = self.client.chat(
            model=self.model,
            messages=messages,
            options={"temperature": 0.0, "seed": 42, "num_ctx": 8192},
        )
        answer = response.message.content.strip()
        self.history.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ])
        return answer
