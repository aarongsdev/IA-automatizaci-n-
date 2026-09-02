#!/usr/bin/env python3
"""
Picks the next chapter to produce from content/series_queue.json and records
it as used in content/used_topics.json, so the workflow never repeats a
chapter and the two files together are a simple, auditable duplication guard.

Series are processed in file order, and within a series chapters are
processed in file order: the current series is fully exhausted (all its
chapters produced) before the next series starts. This keeps each series a
coherent mini-run of episodes with the same recurring character, then moves
on -- rather than jumping between unrelated series episode to episode.

Usage: python scripts/pick_topic.py
Prints one line of JSON on success: {"subject": "..."}
Exits 1 with an error message on stderr if every series is exhausted.

The GitHub Actions workflow commits the updated used_topics.json back to the
repo after a successful run, so state persists between runs without any
external database.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SERIES_PATH = os.path.join(ROOT, "content", "series_queue.json")
USED_PATH = os.path.join(ROOT, "content", "used_topics.json")


def _format_subject(series: str, chapter_index: int, chapter: str) -> str:
    return f"{series} - Capitulo {chapter_index}: {chapter}"


def main() -> int:
    if not os.path.exists(SERIES_PATH):
        print(f"series queue not found: {SERIES_PATH}", file=sys.stderr)
        return 1

    with open(SERIES_PATH, "r", encoding="utf-8") as fh:
        all_series = json.load(fh)

    used = []
    if os.path.exists(USED_PATH):
        with open(USED_PATH, "r", encoding="utf-8") as fh:
            try:
                used = json.load(fh)
            except json.JSONDecodeError:
                used = []
    used_set = set(used)

    for series_entry in all_series:
        series = series_entry["series"]
        chapters = series_entry["chapters"]
        for i, chapter in enumerate(chapters, start=1):
            subject = _format_subject(series, i, chapter)
            if subject not in used_set:
                used.append(subject)
                os.makedirs(os.path.dirname(USED_PATH), exist_ok=True)
                with open(USED_PATH, "w", encoding="utf-8") as fh:
                    json.dump(used, fh, ensure_ascii=False, indent=2)
                print(json.dumps({"subject": subject}, ensure_ascii=False))
                return 0
        # This series is fully used -- move on to the next one only after
        # every one of its chapters has aired.

    print(
        "every series in content/series_queue.json is exhausted -- add a new "
        "series or more chapters, or clear content/used_topics.json to start "
        "over.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
