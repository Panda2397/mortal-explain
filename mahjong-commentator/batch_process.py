"""Evaluate every MJAI JSONL log in data/raw.

Each ``raw/<name>.jsonl`` file is processed with the same parser and evaluator
used by ``main.py`` and written to ``processed/<name>.json``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

from evaluator.decision_evaluator import evaluate_decision
from parser.mjai_parser import extract_decisions, load_mjai_log


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_RAW_DIR = PROJECT_DIR / "data" / "raw"
DEFAULT_PROCESSED_DIR = PROJECT_DIR / "data" / "processed"


def ask_directory(prompt: str, default: Path, *, must_exist: bool) -> Path:
    """Prompt for a directory, accepting blank input for the displayed default."""
    while True:
        entered = input(f"{prompt} [{default}]: ").strip()
        path = Path(entered).expanduser() if entered else default
        path = path.resolve()
        if must_exist and not path.is_dir():
            print(f"Directory does not exist: {path}")
            continue
        if not must_exist and path.exists() and not path.is_dir():
            print(f"Path is not a directory: {path}")
            continue
        return path


def output_path_for(source: Path, processed_dir: Path) -> Path:
    """Return the matching JSON output path while preserving the full stem."""
    return processed_dir / source.with_suffix(".json").name


def process_log(source: Path, destination: Path, player_id: int = 0) -> int:
    """Evaluate one log, atomically write its JSON result, and return its count."""
    events = load_mjai_log(source)
    decisions = extract_decisions(events, player_id=player_id)

    evaluations = []
    started = perf_counter()
    for index, decision in enumerate(decisions, start=1):
        evaluations.append(evaluate_decision(decision))
        if index % 25 == 0 or index == len(decisions):
            elapsed = perf_counter() - started
            print(f"    evaluated {index}/{len(decisions)} decisions ({elapsed:.1f}s)")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as output_file:
            json.dump(evaluations, output_file, ensure_ascii=False, indent=2)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)

    return len(evaluations)


def run_batch(
    raw_dir: Path = DEFAULT_RAW_DIR,
    processed_dir: Path = DEFAULT_PROCESSED_DIR,
    player_id: int = 0,
    pattern: str = "*.jsonl",
) -> tuple[int, list[tuple[Path, Exception]]]:
    """Process matching logs in name order and continue past individual failures."""
    sources = sorted(raw_dir.glob(pattern), key=lambda path: path.name.lower())
    if not sources:
        print(f"No files matching {pattern!r} found in {raw_dir}")
        return 0, []

    processed = 0
    failures: list[tuple[Path, Exception]] = []
    batch_started = perf_counter()

    for index, source in enumerate(sources, start=1):
        destination = output_path_for(source, processed_dir)
        print(f"[{index}/{len(sources)}] {source.name} -> {destination.name}")
        try:
            count = process_log(source, destination, player_id=player_id)
        except Exception as error:  # Keep the remaining independent logs running.
            failures.append((source, error))
            print(f"    FAILED: {type(error).__name__}: {error}")
            continue

        processed += 1
        print(f"    saved {count} evaluations")

    elapsed = perf_counter() - batch_started
    print(
        f"Batch complete: {processed}/{len(sources)} files processed "
        f"in {elapsed:.1f}s; {len(failures)} failed."
    )
    return processed, failures


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate every raw MJAI JSONL log into a matching JSON file."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        help="input directory; prompts when omitted",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        help="output directory; prompts when omitted",
    )
    parser.add_argument(
        "--player",
        type=int,
        default=0,
        help="MJAI player id to evaluate (default: 0)",
    )
    parser.add_argument(
        "--pattern",
        default="*.jsonl",
        help="input filename pattern (default: *.jsonl)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    raw_dir = args.raw_dir or ask_directory(
        "Input directory", DEFAULT_RAW_DIR, must_exist=True
    )
    processed_dir = args.processed_dir or ask_directory(
        "Output directory", DEFAULT_PROCESSED_DIR, must_exist=False
    )
    _, failures = run_batch(
        raw_dir=raw_dir.resolve(),
        processed_dir=processed_dir.resolve(),
        player_id=args.player,
        pattern=args.pattern,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
