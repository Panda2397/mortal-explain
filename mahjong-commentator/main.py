from pathlib import Path

from parser.mjai_parser import (
    load_mjai_log,
    extract_decisions,
)

from evaluator.decision_evaluator import evaluate_decision


def ask_data_path(prompt, default, *, must_exist=False):
    """Ask for a path and keep it inside this project's data directory."""
    data_dir = (Path(__file__).resolve().parent / "data").resolve()
    while True:
        raw = input(f"{prompt} [{default}]: ").strip() or default
        entered = Path(raw)
        if entered.parts and entered.parts[0].lower() == "data":
            entered = Path(*entered.parts[1:])
        path = (data_dir / entered).resolve()
        try:
            path.relative_to(data_dir)
        except ValueError:
            print("Path must be inside the project's data/ directory.")
            continue
        if must_exist and not path.is_file():
            print(f"Input log does not exist: {path}")
            continue
        return path


def main():
    log_path = ask_data_path(
        "Input MJAI log path under data/",
        "raw/game_001.json",
        must_exist=True,
    )
    output_path = ask_data_path(
        "Output evaluation path under data/",
        "processed/decisions.json",
    )

    events = load_mjai_log(log_path)
    decisions = extract_decisions(events, player_id=0)

    for decision in decisions[:5]:
        result = evaluate_decision(decision)

        print("\n" + "=" * 50)
        print(f"Turn: {result['turn']}")
        print(f"Actual discard: {result['actual_discard']}")
        print(
            "Best efficiency discard:",
            result["best_efficiency_discard"],
        )

        print("\nActual evaluation:")
        print(result["actual_evaluation"])

        print("\nBest evaluation:")
        print(result["best_evaluation"])
    import json

    output_path.parent.mkdir(parents=True, exist_ok=True)

    evaluations = [
        evaluate_decision(decision)
        for decision in decisions
    ]

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(
            evaluations,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Saved {len(evaluations)} evaluations to {output_path}")


if __name__ == "__main__":
    main()
