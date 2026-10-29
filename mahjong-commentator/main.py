from pathlib import Path

from parser.mjai_parser import (
    load_mjai_log,
    extract_decisions,
)

from evaluator.decision_evaluator import evaluate_decision


def main():
    log_path = (
        Path(__file__).resolve().parent
        / "data/raw/game_001.json"
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

    output_path = (
        Path(__file__).resolve().parent
        / "data/processed/decisions.json"
    )

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

    print(f"Saved {len(evaluations)} evaluations")


if __name__ == "__main__":
    main()