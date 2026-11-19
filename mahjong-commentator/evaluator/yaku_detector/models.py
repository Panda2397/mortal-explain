"""JSON-safe data contracts for pre-completion yaku evidence."""

from dataclasses import asdict, dataclass, field
from typing import Literal


Feasibility = Literal["impossible", "possible", "unknown"]


@dataclass(frozen=True)
class YakuRules:
    ruleset: str = "riichi_4p_kuitan_aka"
    open_tanyao: bool = True


@dataclass(frozen=True)
class FixedMeld:
    type: str
    tiles: tuple[str, ...]
    is_open: bool
    source_index: int


@dataclass(frozen=True)
class YakuContext:
    concealed_tiles: tuple[str, ...]
    melds: tuple[FixedMeld, ...]
    visible_tiles: tuple[str, ...]
    round_wind: str | None
    seat_wind: str | None
    rules: YakuRules
    melds_complete: bool
    menzen: bool | None
    declared_meld_count: int

    @property
    def input_complete(self) -> bool:
        return self.melds_complete


@dataclass(frozen=True)
class YakuOpportunity:
    yaku: str
    feasibility: Feasibility
    promising: bool | None
    guaranteed_on_completion: bool | None
    completed: None = None
    supporting_tiles: tuple[str, ...] = ()
    obstructing_tiles: tuple[str, ...] = ()
    fixed_meld_indices: tuple[int, ...] = ()
    facts: tuple[str, ...] = ()
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class YakuAnalysis:
    menzen: bool | None
    input_complete: bool
    has_established_yaku: bool | None
    opportunities: dict[str, YakuOpportunity]
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "menzen": self.menzen,
            "input_complete": self.input_complete,
            "has_established_yaku": self.has_established_yaku,
            "opportunities": {
                key: value.to_dict()
                for key, value in self.opportunities.items()
            },
            "errors": list(self.errors),
        }
