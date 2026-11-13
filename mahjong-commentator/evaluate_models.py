"""Generate one LLM prediction per gold decision for benchmarking."""

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from llm.commentator import MahjongCommentator
from llm.prompts import PROMPT_VERSION


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decisions", type=Path, default=Path("data/processed/decisions.json"))
    parser.add_argument("--indices", type=Path, default=Path("data/metrics/gold_indices.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="python-baseline")
    parser.add_argument(
        "--think",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use --think or --no-think for Ollama thinking mode",
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-ctx", type=int, default=8192)
    parser.add_argument("--num-predict", type=int, default=1024)
    parser.add_argument(
        "--treatment",
        choices=("python_baseline", "structured_copy", "independent_grounded"),
        default="structured_copy",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--store-messages",
        action="store_true",
        help="Store full prompts in every JSONL row for audit/debug runs",
    )
    args = parser.parse_args()

    decisions = json.loads(args.decisions.read_text(encoding="utf-8"))
    indices = json.loads(args.indices.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)

    completed = set()
    if args.resume and args.output.exists():
        for line in args.output.read_text(encoding="utf-8").splitlines():
            if line.strip():
                completed.add(json.loads(line)["index"])

    commentator = MahjongCommentator(
        model=args.model,
        use_few_shot=False,
        treatment=args.treatment,
        think=args.think,
        temperature=args.temperature,
        seed=args.seed,
        num_ctx=args.num_ctx,
        num_predict=args.num_predict,
    )
    generation_options = commentator.generation_options()
    mode = "a" if args.resume else "w"
    with args.output.open(mode, encoding="utf-8") as output:
        for index in indices:
            if index in completed:
                continue
            messages = (
                []
                if args.treatment == "python_baseline"
                else commentator.build_messages(decisions[index])
            )
            started = time.perf_counter()
            if args.treatment == "python_baseline":
                commentary = commentator.generate_python_baseline(decisions[index])
            else:
                commentary = commentator.generate(decisions[index])
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            canonical_messages = json.dumps(
                messages, ensure_ascii=False, sort_keys=True
            )
            record = {
                "index": index,
                "model": args.model,
                "treatment": args.treatment,
                "prompt_version": PROMPT_VERSION,
                "prompt_sha256": hashlib.sha256(
                    canonical_messages.encode("utf-8")
                ).hexdigest(),
                "generation_options": generation_options,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "latency_ms": elapsed_ms,
                "explanation_source": commentator.last_explanation_source,
                "fallback_reason": commentator.last_fallback_reason,
                "response_metadata": commentator.last_response_metadata,
                "json_valid": commentator.last_parsed_response is not None,
                "raw_response": commentator.last_raw_response,
                "parsed_response": commentator.last_parsed_response,
                "commentary": commentary,
            }
            if args.store_messages:
                record["messages"] = messages
            output.write(
                json.dumps(record, ensure_ascii=False, default=str) + "\n"
            )
            output.flush()
            print(f"{index}: {elapsed_ms} ms")


if __name__ == "__main__":
    main()
