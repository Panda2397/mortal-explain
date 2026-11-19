"""Terminal interface for replay navigation and grounded coaching."""

import argparse
import json
import os
import shlex
import sys
from pathlib import Path

from interact.coach import InteractiveCoach
from interact.evidence import (
    build_turn_evidence,
    format_turn_summary,
    rank_discards_by_yaku_coverage,
    rank_discards_for_yaku,
    rank_efficiency_discards,
)
from interact.session import ReplaySession


HELP = """Commands:
  show                 Show hand, efficiency and nearby yaku
  yaku                 Show the current discard's yaku JSON
  candidates           List all discard candidates
  recommend [N]        Top N efficient discards with yaku and ukeire (default 5)
  compare TILE         Show deterministic comparison evidence for TILE
  common-yaku          Rank discards by nearby yaku routes preserved
  yaku-discard YAKU    Rank discards for one yaku route
  ask QUESTION         Ask the grounded Ollama coach
  explain              Ask why the actual discard differs from the alternative
  next / previous      Navigate decisions
  turn NUMBER          Go to a one-based decision number
  evidence [TILE]      Print compact LLM evidence JSON
  clear                Clear conversation history
  help                 Show commands
  quit                 Exit
"""


RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
_COLOR_ENABLED = False


def _set_color_enabled(enabled: bool) -> None:
    global _COLOR_ENABLED
    _COLOR_ENABLED = enabled


def _paint(text, *styles):
    value = str(text)
    if not _COLOR_ENABLED or not styles:
        return value
    return "".join(styles) + value + RESET


def _colorize_help(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line == "Commands:":
            lines.append(_paint(line, BOLD, CYAN))
        elif line.startswith("  ") and line.strip():
            command, separator, description = line.strip().partition(" ")
            lines.append("  " + _paint(command, CYAN) + separator + description)
        else:
            lines.append(line)
    return "\n".join(lines)


def _colorize_summary(summary: str) -> str:
    lines = []
    for line in summary.splitlines():
        if line == "=====":
            lines.append(_paint(line, DIM, CYAN))
        elif line.startswith("Decision "):
            lines.append(_paint(line, BOLD, CYAN))
        elif line.startswith("Hand:") or line.startswith("Open melds:"):
            lines.append(_paint(line, CYAN))
        elif line.startswith("Efficiency alternative:"):
            lines.append(_paint(line, BOLD, GREEN))
        elif line.startswith("Efficiency:"):
            lines.append(_paint(line, YELLOW))
        elif line.startswith(("Established components:", "Validated yaku-tenpai:")):
            lines.append(_paint(line, GREEN if not line.endswith("none") else DIM))
        elif line.startswith("Tenpai legality:"):
            style = YELLOW if "no-yaku" in line else GREEN
            lines.append(_paint(line, style))
        elif line == "Nearby yaku:":
            lines.append(_paint(line, BOLD, MAGENTA))
        elif line == "Yaku recommended discard:":
            lines.append(_paint(line, BOLD, GREEN))
        elif line.startswith("  "):
            if "(exact)" in line or "scorer_validated" in line:
                style = GREEN
            elif "(lower_bound)" in line:
                style = YELLOW
            elif "(heuristic)" in line:
                style = MAGENTA
            elif "impossible" in line:
                style = RED
            else:
                style = BLUE
            lines.append(_paint(line, style))
        else:
            lines.append(line)
    return "\n".join(lines)


def parser():
    value = argparse.ArgumentParser(description="Interactive Mahjong replay coach")
    source = value.add_mutually_exclusive_group(required=True)
    source.add_argument("--log", type=Path, help="Raw MJAI JSONL log")
    source.add_argument("--decisions", type=Path, help="Processed decisions JSON")
    value.add_argument("--player", type=int, default=0)
    value.add_argument("--model", default="qwen3:8b")
    value.add_argument("--no-llm", action="store_true", help="Disable ask/explain")
    value.add_argument(
        "--no-color", action="store_true",
        help="Disable ANSI colors (also disabled by NO_COLOR or redirected output)",
    )
    return value


def print_candidates(decision):
    for candidate in decision["all_candidates"]:
        is_actual = candidate["discard"] == decision["actual_discard"]
        is_best = candidate["discard"] == decision["best_efficiency_discard"]
        marker = "*" if is_actual else " "
        line = (f"{marker} {candidate['discard']:>3}  shanten={candidate['shanten']} "
                f"ukeire={candidate['ukeire']}")
        print(_paint(line, BOLD, GREEN) if is_best else
              _paint(line, YELLOW) if is_actual else line)


def print_yaku_coverage(decision):
    print(_paint(
        "Exploratory routes (ordinary shanten first; evidence classes are not equivalent):",
        BOLD, CYAN,
    ))
    for row in rank_discards_by_yaku_coverage(decision):
        validated = ",".join(row["validated_yaku"]) or "-"
        exact = ",".join(row["exact_routes"]) or "-"
        bounded = ",".join(row["bounded_routes"]) or "-"
        heuristic = ",".join(row["heuristic_routes"]) or "-"
        print(
            f"{row['discard']:>3}  "
            f"validated={_paint(validated, GREEN)} "
            f"exact={_paint(exact, GREEN)} "
            f"bounded={_paint(bounded, YELLOW)} "
            f"heuristic={_paint(heuristic, MAGENTA)} "
            f"ordinary={row['ordinary_shanten']}/{row['ordinary_ukeire']}"
        )


def print_yaku_discards(decision, yaku):
    rows = rank_discards_for_yaku(decision, yaku)
    for row in rows:
        blockers = "; ".join(
            f"{blocker.get('type', 'blocker')}:"
            f"{blocker.get('reason', 'unspecified')}"
            for blocker in row["yaku_blockers"]
        ) or "-"
        line = (f"{row['discard']:>3}  yaku={row['yaku_shanten']} "
              f"({row['measurement']}) ukeire={row['yaku_ukeire']} "
              f"[{row['ukeire_kind']}] "
              + (f"estimated={row['estimated_improving_draws']} "
                 if row['estimated_improving_draws'] else "")
              +
              f"{row['feasibility']} ordinary="
              f"{row['ordinary_shanten']}/{row['ordinary_ukeire']} "
              f"blockers={blockers}")
        if row["feasibility"] == "impossible":
            style = RED
        elif row["measurement"] == "exact":
            style = GREEN
        elif row["measurement"] == "lower_bound":
            style = YELLOW
        else:
            style = MAGENTA
        print(_paint(line, style))


def print_recommendations(decision, limit=5):
    for index, row in enumerate(rank_efficiency_discards(decision, limit)):
        yaku = ", ".join(row["yaku"]) or "none"
        effective = " ".join(row["effective_tiles"]) or "none"
        line = (f"{row['shanten']} shanten: discard {row['discard']} -> "
                f"[{yaku}] [{effective}] [{row['ukeire']}]")
        print(_paint(line, BOLD, GREEN) if index == 0 else _paint(line, CYAN))


def main(argv=None):
    args = parser().parse_args(argv)
    _set_color_enabled(
        not args.no_color
        and "NO_COLOR" not in os.environ
        and sys.stdout.isatty()
    )
    session = (
        ReplaySession.from_mjai(args.log, args.player)
        if args.log else ReplaySession.from_processed(args.decisions)
    )
    coach = None if args.no_llm else InteractiveCoach(args.model)
    print(_paint(f"Loaded {len(session)} decisions. Current decision is 1.", BOLD, GREEN))
    print(_colorize_help(HELP))
    print(_colorize_summary(format_turn_summary(session.current)))
    while True:
        try:
            raw = input(_paint("mahjong> ", BOLD, CYAN)).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue
        command, _, rest = raw.partition(" ")
        command = command.lower()
        try:
            if command in {"quit", "exit", "q"}:
                break
            if command == "help":
                print(_colorize_help(HELP))
            elif command == "show":
                print(_colorize_summary(format_turn_summary(session.current)))
            elif command == "yaku":
                analysis = session.current["actual_evaluation"].get("yaku_analysis")
                if analysis is None:
                    print("This processed decision has no yaku analysis; rebuild it or use --log.")
                else:
                    print(json.dumps(analysis.get("yaku", {}), indent=2))
            elif command == "candidates":
                print_candidates(session.current)
            elif command in {"recommend", "recommendations"}:
                limit = int(rest) if rest.strip() else 5
                if limit < 1:
                    raise ValueError("recommendation count must be at least 1")
                print_recommendations(session.current, limit)
            elif command == "common-yaku":
                print_yaku_coverage(session.current)
            elif command == "yaku-discard":
                if not rest.strip():
                    print("Usage: yaku-discard YAKU (example: yaku-discard tanyao)")
                else:
                    print_yaku_discards(session.current, rest.strip())
            elif command == "next":
                print(_colorize_summary(format_turn_summary(session.move(1))))
            elif command in {"previous", "prev"}:
                print(_colorize_summary(format_turn_summary(session.move(-1))))
            elif command == "turn":
                print(_colorize_summary(format_turn_summary(session.go(int(rest) - 1))))
            elif command in {"compare", "evidence"}:
                tile = shlex.split(rest)[0] if rest.strip() else None
                if tile and session.candidate(tile) is None:
                    print(f"No candidate discard {tile}")
                else:
                    print(json.dumps(build_turn_evidence(session.current, tile),
                                     ensure_ascii=False, indent=2))
            elif command in {"ask", "explain"}:
                if coach is None:
                    print("LLM is disabled; restart without --no-llm.")
                    continue
                question = rest if command == "ask" else (
                    "Explain this discard, its efficiency alternative, and the "
                    "important confirmed or nearby yaku trade-offs."
                )
                if not question.strip():
                    print("Usage: ask QUESTION")
                else:
                    print(coach.ask(session.current, question))
            elif command == "clear":
                if coach:
                    coach.clear_history()
                print("Conversation history cleared.")
            else:
                print("Unknown command. Type help.")
        except (IndexError, ValueError) as error:
            print(_paint(f"Error: {error}", BOLD, RED))


if __name__ == "__main__":
    main()
