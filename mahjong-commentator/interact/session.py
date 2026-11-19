"""Lazy evaluated navigation over one target player's MJAI decisions."""

import json
from copy import deepcopy
from pathlib import Path

from evaluator.decision_evaluator import evaluate_decision
from parser.mjai_parser import extract_decisions, load_mjai_log


def _backfill_action_context(decisions: list[dict]) -> None:
    """Recover call labels in processed files created before call metadata."""
    previous_melds: list[dict] = []
    previous_round = None
    for decision in decisions:
        round_info = decision.get("round") or {}
        round_key = (
            round_info.get("bakaze"), round_info.get("kyoku"),
            round_info.get("honba"), decision.get("player"),
        )
        if round_key != previous_round:
            previous_melds = []
            previous_round = round_key

        current = decision.get("open_melds") or []
        changed = None
        if len(current) > len(previous_melds):
            changed = current[-1]
        elif len(current) == len(previous_melds):
            changed = next((
                meld for index, meld in enumerate(current)
                if index < len(previous_melds)
                and meld.get("type") != previous_melds[index].get("type")
            ), None)

        if changed and not decision.get("preceding_action"):
            tiles = changed.get("tiles") or []
            decision["preceding_action"] = {
                "type": changed.get("type"),
                "tile": changed.get("called_tile") or (tiles[0] if tiles else None),
                "from_player": changed.get("from_player"),
            }
            if changed.get("type") in {"chi", "pon"}:
                decision["drawn_tile"] = None
        previous_melds = deepcopy(current)


class ReplaySession:
    def __init__(self, decisions: list[dict], *, source: Path | None = None):
        if not decisions:
            raise ValueError("Replay contains no discard decisions for this player")
        self.raw_decisions = decisions
        self.source = source
        self.index = 0
        self._cache: dict[int, dict] = {}

    @classmethod
    def from_mjai(cls, path: str | Path, player_id: int = 0):
        source = Path(path)
        return cls(extract_decisions(load_mjai_log(source), player_id), source=source)

    @classmethod
    def from_processed(cls, path: str | Path):
        source = Path(path)
        with source.open(encoding="utf-8") as file:
            decisions = json.load(file)
        _backfill_action_context(decisions)
        session = cls(decisions, source=source)
        # Processed decisions are already evaluated.
        session._cache = {index: value for index, value in enumerate(decisions)}
        return session

    def __len__(self):
        return len(self.raw_decisions)

    @property
    def current(self) -> dict:
        if self.index not in self._cache:
            self._cache[self.index] = evaluate_decision(self.raw_decisions[self.index])
        return self._cache[self.index]

    def move(self, offset: int) -> dict:
        self.index = min(max(0, self.index + offset), len(self) - 1)
        return self.current

    def go(self, index: int) -> dict:
        if not 0 <= index < len(self):
            raise IndexError(f"Decision must be between 1 and {len(self)}")
        self.index = index
        return self.current

    def candidate(self, discard: str) -> dict | None:
        return next((candidate for candidate in self.current["all_candidates"]
                     if candidate["discard"] == discard), None)
