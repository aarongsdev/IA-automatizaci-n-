#!/usr/bin/env python3
"""
Burns the hook line and the cliffhanger line into the video itself as bold
on-screen text, at the start and end respectively.

Why: roughly 85% of Shorts/TikTok viewers watch with the sound off at
first, and a hook that only exists as spoken audio is invisible to most of
the audience in the exact window (the first ~1-3 seconds) that decides
whether they keep watching. Short-form platforms measure this as "intro
retention", and creators who stack visual text with the spoken hook see
meaningfully higher click-through and completion. This is the single
highest-leverage, lowest-cost change available in this pipeline for that
metric -- no new dependency, just ffmpeg drawtext on text this project
already generates.

Runs after scripts/overlay_mascot.py (so the mascot is already composited)
and before scripts/generate_thumbnail.py (its background frame comes from
the middle of the clip, unaffected by text confined to the first/last 3s).

Usage: python scripts/burn_hook_text.py result.json "<video subject>"
No-ops (exit 0) on any missing piece (ffmpeg/ffprobe, video, script text,
font) -- same convention as every other post-processing step here, so a
missing tool never breaks an unattended run.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]

MAX_CHARS_PER_LINE = 26


def _find_output_video() -> str | None:
    candidates = glob.glob(
        os.path.join(ROOT, "storage", "tasks", "**", "*.mp4"), recursive=True
    )
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def _pick_font() -> str | None:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def _script_sentences(video_dir: str) -> list[str] | None:
    script_path = os.path.join(video_dir, "script.json")
    try:
        with open(script_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        script = str(data.get("script") or "").strip()
    except (OSError, ValueError):
        return None
    if not script:
        return None
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script) if s.strip()]
    return sentences or None


def _wrap(text: str, max_chars: int) -> str:
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return "\n".join(lines)


def _probe_duration(video_path: str) -> float | None:
    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", video_path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        return float(probe.stdout.strip())
    except (subprocess.SubprocessError, ValueError, OSError):
        return None


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: burn_hook_text.py result.json [video subject]", file=sys.stderr)
        return 0

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("ffmpeg/ffprobe not found, skipping hook text overlay")
        return 0

    font_path = _pick_font()
    if not font_path:
        print("no system font found, skipping hook text overlay")
        return 0

    video_path = _find_output_video()
    if not video_path:
        print("no rendered mp4 found, skipping hook text overlay")
        return 0
    video_dir = os.path.dirname(video_path)

    sentences = _script_sentences(video_dir)
    if not sentences:
        print("no script text found, skipping hook text overlay")
        return 0

    hook = _wrap(sentences[0], MAX_CHARS_PER_LINE)
    cliffhanger = _wrap(sentences[-1], MAX_CHARS_PER_LINE)

    duration = _probe_duration(video_path)
    if not duration or duration <= 6:
        # Too short for a distinct start/end window without the two
        # cards overlapping -- skip rather than produce a garbled result.
        print("video too short for a start/end text overlay, skipping")
        return 0

    tail_start = duration - 3

    with tempfile.TemporaryDirectory() as tmp:
        hook_path = os.path.join(tmp, "hook.txt")
        cliff_path = os.path.join(tmp, "cliff.txt")
        with open(hook_path, "w", encoding="utf-8") as fh:
            fh.write(hook)
        with open(cliff_path, "w", encoding="utf-8") as fh:
            fh.write(cliffhanger)

        common = (
            f"fontfile={font_path}:fontcolor=yellow:fontsize=68:"
            "bordercolor=black:borderw=6:line_spacing=10:"
            "x=(w-text_w)/2:y=140"
        )
        filter_complex = (
            f"drawtext=textfile={hook_path}:{common}:enable='lt(t,3)',"
            f"drawtext=textfile={cliff_path}:{common}:enable='gte(t,{tail_start:.2f})'"
        )

        tmp_output = video_path + ".with_hooktext.mp4"
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", filter_complex,
            # Explicit codecs, not "-c:a copy" -- see the same note in
            # overlay_mascot.py: MP3-in-MP4 audio (common from the TTS step)
            # trips up Windows' built-in player with an "unsupported
            # encoding configuration" error. H.264 + AAC + yuv420p plays
            # everywhere.
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            tmp_output,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            print(f"ffmpeg hook text overlay failed, keeping original video:\n{result.stderr[-2000:]}")
            if os.path.exists(tmp_output):
                os.remove(tmp_output)
            return 0

        os.replace(tmp_output, video_path)
        print(f"hook/cliffhanger text burned into: {video_path}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
