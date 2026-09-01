#!/usr/bin/env python3
"""
Generates a clickable-looking vertical thumbnail for the episode, built
entirely with free/local tools -- no thumbnail-generation API, no stock
image service.

Format decision: 1080x1920 (9:16), matching the video itself. The pipeline
only ever publishes to YouTube Shorts / TikTok / Instagram Reels, all of
which display a *vertical* thumbnail in their vertical feeds; a standard
1280x720 YouTube thumbnail would just get cropped by those surfaces, and
YouTube itself accepts (and prefers) a vertical custom thumbnail for
Shorts. So: one 1080x1920 image, not the classic 16:9 thumbnail.

What it does:
  1. Grabs a frame from the middle of the rendered video with ffmpeg as a
     blurred, darkened backdrop for visual context (falls back to a plain
     bold color if ffmpeg or the frame extraction is unavailable).
  2. Reuses the exact mascot PNG scripts/overlay_mascot.py picked for this
     run (via the mascot_used.json state file it writes) so the character
     on the thumbnail always matches the one on the video -- never a
     re-rolled random pick that could show a different cast member.
  3. Draws a large, high-contrast hook line derived from the episode's
     script (its first sentence) or, if that isn't available, from the
     video subject/title -- using DejaVu Sans Bold, which ships by default
     on ubuntu-latest GitHub Actions runners (package fonts-dejavu-core),
     so no font file needs to be committed to the repo.
  4. Writes thumbnail.jpg next to the episode's mp4 in storage/tasks/.

Usage: python scripts/generate_thumbnail.py result.json "<video subject>"
No-ops (exit 0) on any missing piece (Pillow, ffmpeg, video file, mascot,
script text) -- this step must never fail the workflow, same convention as
scripts/overlay_mascot.py.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
CHARACTERS_DIR = os.path.join(ROOT, "assets", "characters")
MASCOT_STATE_FILENAME = "mascot_used.json"

THUMB_W, THUMB_H = 1080, 1920

# Ships by default on ubuntu-latest (fonts-dejavu-core); also commonly
# present on Debian/Ubuntu desktops for local testing. No font file is
# bundled in the repo to keep this dependency-free.
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]

# A punchy, high-contrast backdrop color used when no video frame can be
# extracted (e.g. ffmpeg missing). Warm orange reads well behind the
# hand-drawn mascots and white bold text, and is distinct across all series.
FALLBACK_BG = (230, 92, 40)


def _series_name(subject: str) -> str:
    return subject.split(" - Capitulo", 1)[0].strip()


def _find_output_video() -> str | None:
    candidates = glob.glob(
        os.path.join(ROOT, "storage", "tasks", "**", "*.mp4"), recursive=True
    )
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def _load_mascot_choice(video_dir: str, subject: str) -> str | None:
    """Reuses the mascot picked by overlay_mascot.py for this exact run."""
    state_path = os.path.join(video_dir, MASCOT_STATE_FILENAME)
    try:
        with open(state_path, "r", encoding="utf-8") as fh:
            state = json.load(fh)
    except (OSError, ValueError):
        return None
    if state.get("series") != _series_name(subject):
        return None  # stale state from a previous run in the same dir
    mascot_file = state.get("mascot_file")
    if not mascot_file:
        return None
    path = os.path.join(CHARACTERS_DIR, mascot_file)
    return path if os.path.exists(path) else None


def _hook_text(video_dir: str, subject: str) -> str:
    """First sentence of the generated script, falling back to the subject."""
    script_path = os.path.join(video_dir, "script.json")
    try:
        with open(script_path, "r", encoding="utf-8") as fh:
            script_data = json.load(fh)
        script = str(script_data.get("script") or "").strip()
        if script:
            # Split on sentence-ending punctuation; keep the first sentence.
            match = re.split(r"(?<=[.!?])\s+", script, maxsplit=1)
            hook = match[0].strip()
            if hook:
                return hook
    except (OSError, ValueError):
        pass

    # Fall back to the chapter title portion of the subject, e.g.
    # "Luna, la zorrita curiosa - Capitulo 3: El bosque dormido" -> the
    # part after "Capitulo N: ".
    tail = subject.split(":", 1)
    return tail[1].strip() if len(tail) > 1 else subject


def _pick_font():
    from PIL import ImageFont

    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def _extract_background(video_path: str, out_path: str) -> bool:
    """Grabs a frame from the middle of the clip as a blurred backdrop."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return False
    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", video_path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        duration = float(probe.stdout.strip())
    except (subprocess.SubprocessError, ValueError, OSError):
        duration = 0.0

    midpoint = max(duration / 2.0, 0.1)
    cmd = [
        "ffmpeg", "-y", "-ss", str(midpoint), "-i", video_path,
        "-frames:v", "1",
        # Slight blur + darken so foreground text/mascot stay legible over
        # busy stock footage, without needing any compositing logic here.
        "-vf", "scale=1080:1920,boxblur=8:2,eq=brightness=-0.12",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return result.returncode == 0 and os.path.exists(out_path)


def _wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: generate_thumbnail.py result.json <video subject>", file=sys.stderr)
        return 0

    subject = sys.argv[2]

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not available, skipping thumbnail generation")
        return 0

    video_path = _find_output_video()
    if not video_path:
        print("no rendered mp4 found, skipping thumbnail generation")
        return 0
    video_dir = os.path.dirname(video_path)

    # 1. Background: extracted frame, or a flat brand-color fallback.
    frame_path = os.path.join(video_dir, "_thumb_frame.jpg")
    background = None
    if _extract_background(video_path, frame_path):
        try:
            background = Image.open(frame_path).convert("RGB").resize((THUMB_W, THUMB_H))
        except OSError:
            background = None
        finally:
            if os.path.exists(frame_path):
                os.remove(frame_path)
    if background is None:
        background = Image.new("RGB", (THUMB_W, THUMB_H), FALLBACK_BG)

    canvas = background.convert("RGBA")

    # A darkening gradient behind the bottom third makes the hook text
    # readable no matter what's in the extracted frame there.
    gradient = Image.new("RGBA", (THUMB_W, THUMB_H), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(gradient)
    band_top = int(THUMB_H * 0.62)
    for y in range(band_top, THUMB_H):
        alpha = int(200 * (y - band_top) / (THUMB_H - band_top))
        gdraw.line([(0, y), (THUMB_W, y)], fill=(0, 0, 0, alpha))
    canvas = Image.alpha_composite(canvas, gradient)

    # 2. Mascot in the foreground, large, bottom-anchored so it reads as
    # the "star" of the thumbnail (matches overlay_mascot.py's cast pick).
    mascot_path = _load_mascot_choice(video_dir, subject)
    if mascot_path:
        try:
            mascot = Image.open(mascot_path).convert("RGBA")
            target_w = int(THUMB_W * 0.62)
            scale = target_w / mascot.width
            mascot = mascot.resize((target_w, int(mascot.height * scale)))
            mx = THUMB_W - mascot.width - 20
            my = THUMB_H - mascot.height - 40
            canvas.alpha_composite(mascot, (mx, my))
        except OSError as exc:
            print(f"could not composite mascot onto thumbnail: {exc}")

    # 3. Hook text, big and bold, top-left so it doesn't collide with the
    # mascot anchored bottom-right.
    draw = ImageDraw.Draw(canvas)
    font_path = _pick_font()
    hook = _hook_text(video_dir, subject)
    if font_path and hook:
        font_size = 96
        font = ImageFont.truetype(font_path, font_size)
        max_width = THUMB_W - 100
        lines = _wrap_text(draw, hook, font, max_width)
        # Shrink if it still doesn't fit within a reasonable number of lines.
        while len(lines) > 5 and font_size > 48:
            font_size -= 8
            font = ImageFont.truetype(font_path, font_size)
            lines = _wrap_text(draw, hook, font, max_width)
        lines = lines[:6]

        line_height = int(font_size * 1.2)
        y = 80
        for line in lines:
            # Simple black outline for legibility over any background.
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
                draw.text((50 + dx, y + dy), line, font=font, fill=(0, 0, 0, 255))
            draw.text((50, y), line, font=font, fill=(255, 221, 0, 255))
            y += line_height
    elif not font_path:
        print("no system font found, thumbnail generated without hook text")

    out_path = os.path.join(video_dir, "thumbnail.jpg")
    canvas.convert("RGB").save(out_path, "JPEG", quality=90)
    print(f"thumbnail generated: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
