"""Rules-facing yaku inventory; structural support is explicit and auditable."""

YAKU_INVENTORY = {
    # Menzen-only structural yaku.
    "pinfu": {"category": "menzen_only", "structural": True, "supported": True},
    "iipeikou": {"category": "menzen_only", "structural": True, "supported": True},
    "ryanpeikou": {"category": "menzen_only", "structural": True, "supported": True},
    "chiitoitsu": {"category": "menzen_only", "structural": True, "supported": True},
    # Menzen-only situational yaku have no structural yaku shanten.
    "riichi": {"category": "menzen_only", "structural": False, "supported": False},
    "double_riichi": {"category": "menzen_only", "structural": False, "supported": False},
    "ippatsu": {"category": "menzen_only", "structural": False, "supported": False},
    "menzen_tsumo": {"category": "menzen_only", "structural": False, "supported": False},
    # Open allowed, reduced han.
    "sanshoku_doujun": {"category": "open_reduced", "structural": True, "supported": True},
    "ittsu": {"category": "open_reduced", "structural": True, "supported": True},
    "chanta": {"category": "open_reduced", "structural": True, "supported": True},
    "junchan": {"category": "open_reduced", "structural": True, "supported": True},
    "honitsu": {"category": "open_reduced", "structural": True, "supported": True},
    "chinitsu": {"category": "open_reduced", "structural": True, "supported": True},
    # Open allowed, same han.
    "tanyao": {"category": "open_same", "structural": True, "supported": True,
                "rule": "open_tanyao"},
    "yakuhai": {"category": "open_same", "structural": True, "supported": True},
    "toitoi": {"category": "open_same", "structural": True, "supported": True},
    "sanankou": {"category": "open_same", "structural": True, "supported": True},
    "sanshoku_doukou": {"category": "open_same", "structural": True, "supported": True},
    "honroutou": {"category": "open_same", "structural": True, "supported": True},
    "sankantsu": {"category": "open_same", "structural": True, "supported": True,
                  "distance": "action_dependent_heuristic"},
    "shousangen": {"category": "open_same", "structural": True, "supported": True},
    "haitei": {"category": "open_same", "structural": False, "supported": False},
    "houtei": {"category": "open_same", "structural": False, "supported": False},
    "rinshan_kaihou": {"category": "open_same", "structural": False, "supported": False},
    "chankan": {"category": "open_same", "structural": False, "supported": False},
    # Yakuman.
    "kokushi": {"category": "yakuman_menzen", "structural": True, "supported": True},
    "suuankou": {"category": "yakuman_menzen", "structural": True, "supported": True},
    "chuuren_poutou": {"category": "yakuman_menzen", "structural": True, "supported": True},
    "tenhou": {"category": "yakuman_menzen", "structural": False, "supported": False},
    "chiihou": {"category": "yakuman_menzen", "structural": False, "supported": False},
    "daisangen": {"category": "yakuman_open", "structural": True, "supported": True},
    "shousuushii": {"category": "yakuman_open", "structural": True, "supported": True},
    "daisuushii": {"category": "yakuman_open", "structural": True, "supported": True},
    "tsuuiisou": {"category": "yakuman_open", "structural": True, "supported": True},
    "chinroutou": {"category": "yakuman_open", "structural": True, "supported": True},
    "ryuuiisou": {"category": "yakuman_open", "structural": True, "supported": True},
    "suukantsu": {"category": "yakuman_open", "structural": True, "supported": True,
                  "distance": "action_dependent_heuristic"},
}


def supported_structural_yaku() -> list[str]:
    return sorted(name for name, data in YAKU_INVENTORY.items()
                  if data["structural"] and data["supported"])
