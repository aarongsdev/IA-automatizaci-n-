#!/usr/bin/env python3
"""
Synchronous, explicit publish step for the GitHub Actions workflow.

MoneyPrinterTurbo's built-in auto-upload (config.app.official_publish_auto_upload
/ upload_post_auto_upload) schedules cross-posting on a background thread pool
inside the same long-lived API process it was designed for. That still works
from a one-shot CLI run -- Python's ThreadPoolExecutor registers an atexit
hook that blocks process exit until pending uploads finish -- but a CI job is
easier to debug when each step is explicit, synchronous, and has its own
visible logs and exit code. This script does the publish step directly
instead of relying on that background scheduling.

Usage:
    python cli.py --video-subject "$SUBJECT" --stop-at video > result.json
    python scripts/publish_video.py result.json "$SUBJECT"

Exits 0 only if every configured platform (per official_publish_platforms in
config.toml) succeeded. Exits 1 otherwise, with a JSON summary on stdout
either way so the workflow can surface it in the job log.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, ROOT)

from app.services import official_publish  # noqa: E402


def main(argv: list) -> int:
    if len(argv) < 3:
        print(
            "usage: publish_video.py <cli-result.json> <title>",
            file=sys.stderr,
        )
        return 2

    result_path, title = argv[1], argv[2]
    with open(result_path, "r", encoding="utf-8") as fh:
        cli_output = json.load(fh)

    videos = (cli_output.get("result") or {}).get("videos") or []
    if not videos:
        print(
            json.dumps(
                {"success": False, "error": "no videos in CLI result", "raw": cli_output}
            )
        )
        return 1

    video_path = videos[0]

    if not official_publish.official_publish_service.enabled:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": "official_publish_enabled is false in config.toml; nothing to do",
                }
            )
        )
        return 1

    result = official_publish.cross_post_video(video_path=video_path, title=title)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
