"""Preview one baseline or LLM commentary from any processed decision file."""

import argparse
import json
import sys
from pathlib import Path

from llm.commentator import MahjongCommentator


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--decisions",
        type=Path,
        default=Path("data/processed/decisions.json"),
    )
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument(
        "--think",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-ctx", type=int, default=8192)
    parser.add_argument("--num-predict", type=int, default=1024)
    parser.add_argument(
        "--treatment",
        choices=("python_baseline", "structured_copy", "independent_grounded"),
        default="independent_grounded",
    )
    parser.add_argument(
        "--show",
        choices=("commentary", "raw", "both", "prompt"),
        default="both",
    )
    args = parser.parse_args()

    decisions = json.loads(args.decisions.read_text(encoding="utf-8"))
    if not 0 <= args.index < len(decisions):
        raise SystemExit(
            f"Index {args.index} is outside 0..{len(decisions) - 1}"
        )
    decision = decisions[args.index]
    commentator = MahjongCommentator(
        model=args.model,
        use_few_shot=False,
        treatment=(
            "structured_copy"
            if args.treatment == "python_baseline"
            else args.treatment
        ),
        think=args.think,
        temperature=args.temperature,
        seed=args.seed,
        num_ctx=args.num_ctx,
        num_predict=args.num_predict,
    )

    if args.show == "prompt":
        if args.treatment == "python_baseline":
            print("The Python baseline has no LLM prompt.")
            return
        print(json.dumps(
            commentator.build_messages(decision),
            ensure_ascii=False,
            indent=2,
        ))
        return

    if args.treatment == "python_baseline":
        commentary = commentator.generate_python_baseline(decision)
    else:
        commentary = commentator.generate(decision)

    print(
        f"decision={args.decisions} index={args.index} "
        f"treatment={args.treatment} model={args.model} think={args.think}"
    )
    if args.show in {"raw", "both"}:
        print("\n=== RAW MODEL RESPONSE ===\n")
        if args.treatment == "python_baseline":
            print("N/A — the Python baseline makes no model call.")
        else:
            try:
                raw = json.loads(commentator.last_raw_response)
                print(json.dumps(raw, ensure_ascii=False, indent=2))
            except json.JSONDecodeError:
                print(commentator.last_raw_response)
            print(f"\nexplanation_source={commentator.last_explanation_source}")
            print(f"fallback_reason={commentator.last_fallback_reason}")
    if args.show in {"commentary", "both"}:
        print("\n=== FINAL COMMENTARY ===\n")
        print(commentary)


if __name__ == "__main__":
    main()
