import json

from llm.commentator import MahjongCommentator


def prepare_llm_input(evaluation):

    return {
        "player": evaluation["player"],
        "turn": evaluation["turn"],
        "round": evaluation.get("round"),
        "hand": evaluation.get("hand"),
        "dora_indicators": evaluation.get("dora_indicators"),
        "open_melds": evaluation.get("open_melds"),
        "blocks": evaluation.get("blocks"),

        "actual_discard": evaluation["actual_discard"],
        "actual_evaluation": evaluation["actual_evaluation"],

        "best_efficiency_discard":
            evaluation["best_efficiency_discard"],

        "best_evaluation": evaluation["best_evaluation"],

        "actual_shanten_minus_alternative": 
            evaluation["actual_shanten_minus_alternative"],
        "actual_ukeire_minus_alternative":
            evaluation["actual_ukeire_minus_alternative"],
    }


def main():

    with open(
        "data/processed/decisions.json",
        encoding="utf-8"
    ) as f:
        decisions = json.load(f)

    commentator = MahjongCommentator()

    # Test one decision first
    for i in range(17,20):
        decision = decisions[i]

        evidence = prepare_llm_input(decision)

        commentary = commentator.generate(evidence)

        print("\n=== LLM COMMENTARY ===\n")
        print(commentary)
        print("\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    main()