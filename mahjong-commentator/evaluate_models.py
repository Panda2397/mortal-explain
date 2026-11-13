"""Generate one LLM prediction per gold decision for benchmarking."""

import argparse
import json
import time
from pathlib import Path

from llm.commentator import MahjongCommentator


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decisions", type=Path, default=Path("data/processed/decisions.json"))
    parser.add_argument("--indices", type=Path, default=Path("data/metrics/gold_indices.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    decisions = json.loads(args.decisions.read_text(encoding="utf-8"))
    indices = json.loads(args.indices.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)

    completed = set()
    if args.resume and args.output.exists():
        for line in args.output.read_text(encoding="utf-8").splitlines():
            if line.strip():
                completed.add(json.loads(line)["index"])

    commentator = MahjongCommentator(model=args.model, use_few_shot=False)
    mode = "a" if args.resume else "w"
    with args.output.open(mode, encoding="utf-8") as output:
        for index in indices:
            if index in completed:
                continue
            started = time.perf_counter()
            commentary = commentator.generate(decisions[index])
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            record = {
                "index": index,
                "model": args.model,
                "latency_ms": elapsed_ms,
                "explanation_source": commentator.last_explanation_source,
                "json_valid": commentator.last_parsed_response is not None,
                "raw_response": commentator.last_raw_response,
                "parsed_response": commentator.last_parsed_response,
                "commentary": commentary,
            }
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            output.flush()
            print(f"{index}: {elapsed_ms} ms")


if __name__ == "__main__":
    main()
