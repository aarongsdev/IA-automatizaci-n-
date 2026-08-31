#!/usr/bin/env python3
"""
Picks the next unused topic from content/topics_queue.txt and records it as
used in content/used_topics.json, so the daily workflow never repeats a
subject and the two files together are a simple, auditable duplication guard
(brief point 29's SimilarityChecker, MVP version).

Usage: python scripts/pick_topic.py
Prints one line of JSON on success: {"subject": "..."}
Exits 1 with an error message on stderr if the queue is exhausted.

The GitHub Actions workflow commits the updated used_topics.json back to the
repo after a successful run, so state persists between daily runs without
any external database.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
QUEUE_PATH = os.path.join(ROOT, "content", "topics_queue.txt")
USED_PATH = os.path.join(ROOT, "content", "used_topics.json")


def main() -> int:
    if not os.path.exists(QUEUE_PATH):
        print(f"topics queue not found: {QUEUE_PATH}", file=sys.stderr)
        return 1

    with open(QUEUE_PATH, "r", encoding="utf-8") as fh:
        candidates = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

    used = []
    if os.path.exists(USED_PATH):
        with open(USED_PATH, "r", encoding="utf-8") as fh:
            try:
                used = json.load(fh)
            except json.JSONDecodeError:
                used = []
    used_set = set(used)

    remaining = [c for c in candidates if c not in used_set]
    if not remaining:
        print(
            "topics_queue.txt is exhausted -- add more lines to content/topics_queue.txt "
            "(one topic per line) or clear content/used_topics.json to start over.",
            file=sys.stderr,
        )
        return 1

    chosen = remaining[0]
    used.append(chosen)
    os.makedirs(os.path.dirname(USED_PATH), exist_ok=True)
    with open(USED_PATH, "w", encoding="utf-8") as fh:
        json.dump(used, fh, ensure_ascii=False, indent=2)

    print(json.dumps({"subject": chosen}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
