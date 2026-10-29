import json
from llm.commentator import MahjongCommentator

commentator = MahjongCommentator(use_few_shot=True)

with open(
    "data/examples/discard_example.json",
    encoding="utf-8",
) as f:
    example = json.load(f)

with open(
    "data/processed/decisions.json",
    encoding="utf-8",
) as f:
    decisions = json.load(f)

example_evidence = commentator.build_evidence(example)
actual_evidence = commentator.build_evidence(decisions[0])

print("Example fields:", example_evidence.keys())
print("Actual fields:", actual_evidence.keys())

print("\nExample hand:", example_evidence.get("hand"))
print("Actual hand:", actual_evidence.get("hand"))