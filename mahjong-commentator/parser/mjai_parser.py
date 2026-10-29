import json
from pathlib import Path
from collections import Counter


def load_mjai_log(path: str | Path) -> list[dict]:
    """Load MJAI events from a JSON Lines file."""

    events = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))

    return events


class MJAIParser:
    def __init__(self, player_id: int = 0):
        self.player_id = player_id
        self.reset()

    def reset(self):
        self.hand = []
        self.visible_tiles = []
        self.open_melds = 0

        self.turn = 0
        self.round = None
        self.dora_indicators = []

        self.decisions = []

    def start_round(self, event: dict):
        """Initialize the player's state for a new round."""

        self.hand = event["tehais"][self.player_id].copy()

        if "?" in self.hand:
            raise ValueError(
                "Player's concealed hand is hidden. "
                "Use a log from the target player's perspective."
            )

        self.visible_tiles = []
        self.open_melds = 0
        self.turn = 0

        oya = event["oya"]

        winds = ["E", "S", "W", "N"]
        jikaze = winds[(self.player_id - oya) % 4]

        self.round = {
            "bakaze": event.get("bakaze"),
            "jikaze": jikaze,
            "kyoku": event.get("kyoku"),
            "honba": event.get("honba"),
            "scores": event.get("scores"),
            "oya": oya,
            "kyotaku": event.get("kyotaku"),
        }

        self.dora_indicators = []

        marker = event.get("dora_marker")

        if marker and marker != "?":
            self.dora_indicators.append(marker)
            self.visible_tiles.append(marker)

    def process_draw(self, event: dict):
        """Add a tile when the target player draws."""

        if event["actor"] != self.player_id:
            return

        tile = event["pai"]

        if tile == "?":
            raise ValueError(
                "Cannot reconstruct hand: target player's draw is hidden."
            )

        self.hand.append(tile)
        self.drawn_tile = tile

    def process_discard(self, event: dict):
        """Capture a decision and then update the hand."""

        actor = event["actor"]
        tile = event["pai"]

        if actor == self.player_id:

            # Capture the state BEFORE discarding
            decision = {
                "player": self.player_id,
                "round": self.round.copy() if self.round else None,
                "turn": self.turn + 1,
                "hand": self.hand.copy(),
                "actual_discard": tile,
                "tsumogiri": event.get("tsumogiri", False),
                "visible_tiles": self.visible_tiles.copy(),
                "open_melds": self.open_melds,
                "dora_indicators": self.dora_indicators.copy(),
                "drawn_tile": self.drawn_tile,
            }

            self.decisions.append(decision)

            # Apply the discard
            if tile not in self.hand:
                raise ValueError(
                    f"Cannot discard {tile}: tile not in hand {self.hand}"
                )

            self.hand.remove(tile)
            self.turn += 1

        # All discards are publicly visible
        if tile != "?":
            self.visible_tiles.append(tile)

    def process_call(self, event: dict):
        """
        Handle chi and pon calls made by the target player.

        MJAI chi/pon events contain consumed tiles from
        the player's hand.
        """

        if event.get("actor") != self.player_id:
            return

        for tile in event.get("consumed", []):
            if tile not in self.hand:
                raise ValueError(
                    f"Cannot consume {tile}: not in hand {self.hand}"
                )

            self.hand.remove(tile)

        self.open_melds += 1

        # Called tiles are now visible.
        # The claimed tile was already counted as a discard.
        for tile in event.get("consumed", []):
            if tile != "?":
                self.visible_tiles.append(tile)

    def process_kan(self, event: dict):
        """Handle kan events made by the target player."""

        if event.get("actor") != self.player_id:
            return

        for tile in event.get("consumed", []):
            if tile not in self.hand:
                raise ValueError(
                    f"Cannot consume {tile}: not in hand {self.hand}"
                )

            self.hand.remove(tile)

        if event["type"] in ("daiminkan", "ankan"):
            self.open_melds += 1

        for tile in event.get("consumed", []):
            if tile != "?":
                self.visible_tiles.append(tile)

    def parse(self, events: list[dict]) -> list[dict]:
        """Process an MJAI event stream."""

        self.reset()

        for event in events:
            event_type = event.get("type")

            if event_type == "start_kyoku":
                self.start_round(event)

            elif event_type == "tsumo":
                self.process_draw(event)

            elif event_type == "dahai":
                self.process_discard(event)

            elif event_type in ("chi", "pon"):
                self.process_call(event)

            elif event_type in ("daiminkan", "ankan", "kakan"):
                self.process_kan(event)

            elif event_type == "dora":
                marker = event.get("dora_marker")

                if marker and marker != "?":
                    self.dora_indicators.append(marker)
                    self.visible_tiles.append(marker)

        return self.decisions


def extract_decisions(
    events: list[dict],
    player_id: int = 0,
) -> list[dict]:
    parser = MJAIParser(player_id=player_id)
    return parser.parse(events)