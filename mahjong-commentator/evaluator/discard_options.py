"""Compact discard choices shared by processed output and LLM evidence."""


MEASUREMENT_RANK = {
    "exact": 0,
    "lower_bound": 1,
    "upper_bound": 2,
    "heuristic": 3,
}


def build_discard_options(candidates: list[dict]) -> list[dict]:
    """Return efficiency-ranked options with nearby yaku summaries only."""
    options = []
    for candidate in candidates:
        ordinary = candidate.get("shanten")
        routes = candidate.get("yaku_analysis", {}).get("yaku", {})
        nearby = []
        for name, route in routes.items():
            metric = route.get("shanten", {})
            yaku_shanten = metric.get("value")
            if (
                ordinary is None
                or yaku_shanten is None
                or route.get("feasibility") not in {"confirmed", "possible"}
                or route.get("availability") == "dead"
                or yaku_shanten - ordinary > 1
            ):
                continue
            nearby.append({
                "name": name,
                "yaku_shanten": yaku_shanten,
                "measurement": metric.get("measurement"),
                "route_state": route.get("route_state", "none"),
                "validation": route.get("proof", {}).get("validation"),
                "tenpai_quality": route.get("tenpai_quality", {}),
            })
        nearby.sort(key=lambda route: (
            route["yaku_shanten"],
            MEASUREMENT_RANK.get(route["measurement"], 9),
            route["name"],
        ))
        options.append({
            "discard": candidate.get("discard"),
            "ordinary_shanten": ordinary,
            "ordinary_ukeire": candidate.get("ukeire"),
            "effective_tiles": candidate.get("effective_tiles", {}),
            "nearby_yaku": nearby,
        })

    options.sort(key=lambda option: (
        option["ordinary_shanten"]
        if option["ordinary_shanten"] is not None else 99,
        -(option["ordinary_ukeire"] or 0),
        option["discard"] or "",
    ))
    for rank, option in enumerate(options, start=1):
        option["efficiency_rank"] = rank
    return options
