import json
from copy import deepcopy
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
        self.known_public_tiles = []
        self.discards_by_player = {player: [] for player in range(4)}
        self.open_melds = []

        self.turn = 0
        self.round = None
        self.dora_indicators = []
        self.drawn_tile = None
        self.pending_action = None

        self.decisions = []

    def start_round(self, event: dict):
        """Initialize the player's state for a new round."""

        self.hand = event["tehais"][self.player_id].copy()

        if "?" in self.hand:
            raise ValueError(
                "Player's concealed hand is hidden. "
                "Use a log from the target player's perspective."
            )

        self.known_public_tiles = []
        self.discards_by_player = {player: [] for player in range(4)}
        self.open_melds = []
        self.turn = 0
        self.drawn_tile = None
        self.pending_action = None

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
            self.known_public_tiles.append(marker)

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
                "drawn_tile": self.drawn_tile,
                "preceding_action": deepcopy(self.pending_action),
                "hand": self.hand.copy(),
                "actual_discard": tile,
                "visible_tiles": self.known_public_tiles.copy(),
                "discards_by_player": deepcopy(self.discards_by_player),
                "open_melds": deepcopy(self.open_melds),
                "open_meld_count": len(self.open_melds),
                "dora_indicators": self.dora_indicators.copy(),
                
            }

            self.decisions.append(decision)

            # Apply the discard
            if tile not in self.hand:
                raise ValueError(
                    f"Cannot discard {tile}: tile not in hand {self.hand}"
                )

            self.hand.remove(tile)
            self.turn += 1
            # A draw or call applies only to this discard decision. Keeping
            # it beyond the discard made later chi/pon turns display a stale
            # tile as though it had just been drawn.
            self.drawn_tile = None
            self.pending_action = None

        # All discards are publicly visible
        if tile != "?":
            self.known_public_tiles.append(tile)
            self.discards_by_player.setdefault(actor, []).append(tile)

    def process_call(self, event: dict):
        """
        Handle chi and pon calls made by the target player.

        MJAI chi/pon events contain consumed tiles from
        the player's hand.
        """

        # The claimed tile is already counted as a discard. Consumed tiles
        # become public no matter which player made the call.
        for tile in event.get("consumed", []):
            if tile != "?":
                self.known_public_tiles.append(tile)

        if event.get("actor") != self.player_id:
            return

        called_tile = event.get("pai")
        self.drawn_tile = None
        self.pending_action = {
            "type": event["type"],
            "tile": called_tile,
            "from_player": event.get("target"),
        }

        for tile in event.get("consumed", []):
            if tile not in self.hand:
                raise ValueError(
                    f"Cannot consume {tile}: not in hand {self.hand}"
                )

            self.hand.remove(tile)

        consumed = event.get("consumed", []).copy()
        self.open_melds.append({
            "type": event["type"],
            "tiles": consumed + ([called_tile] if called_tile else []),
            "consumed": consumed,
            "called_tile": called_tile,
            "from_player": event.get("target"),
            "actor": event.get("actor"),
            "open": True,
        })

    def process_kan(self, event: dict):
        """Handle kan events made by the target player."""

        kan_type = event["type"]
        called_tile = event.get("pai")
        consumed = event.get("consumed", []).copy()
        newly_visible = [called_tile] if kan_type == "kakan" else consumed
        for tile in newly_visible:
            if tile and tile != "?":
                self.known_public_tiles.append(tile)

        if event.get("actor") != self.player_id:
            return

        representative_tile = called_tile or (consumed[0] if consumed else None)
        self.drawn_tile = None
        self.pending_action = {
            "type": kan_type,
            "tile": representative_tile,
            "from_player": event.get("target"),
        }

        # In MJAI kakan events, ``consumed`` identifies the existing pon and
        # ``pai`` is the fourth tile being added from the concealed hand.
        # Other kan types consume all tiles listed in ``consumed``.
        removed_tiles = [called_tile] if kan_type == "kakan" else consumed

        for tile in removed_tiles:
            if tile is None:
                raise ValueError(f"{kan_type} event is missing a tile")
            if tile not in self.hand:
                raise ValueError(
                    f"Cannot consume {tile}: not in hand {self.hand}"
                )

            self.hand.remove(tile)

        meld = {
            "type": kan_type,
            "tiles": consumed + ([called_tile] if called_tile else []),
            "consumed": consumed,
            "called_tile": called_tile,
            "from_player": event.get("target"),
            "actor": event.get("actor"),
            "open": kan_type != "ankan",
        }

        if kan_type == "kakan":
            normalized = (called_tile or (consumed[0] if consumed else "")).replace(
                "r", ""
            )
            upgraded = next((
                existing
                for existing in self.open_melds
                if existing["type"] == "pon"
                and existing["tiles"]
                and existing["tiles"][0].replace("r", "") == normalized
            ), None)
            if upgraded is not None:
                upgraded.update(meld)
            else:
                self.open_melds.append(meld)
        else:
            self.open_melds.append(meld)

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
                    self.known_public_tiles.append(marker)

        return self.decisions


def extract_decisions(
    events: list[dict],
    player_id: int = 0,
) -> list[dict]:
    parser = MJAIParser(player_id=player_id)
    return parser.parse(events)
