#!/usr/bin/env python3
"""
Builds config.toml for one GitHub Actions run from config.example.toml plus
environment variables (populated from repository Secrets in the workflow).

Two categories of credentials are handled differently on purpose:
  - Pexels/Pixabay/Groq keys have no env-var fallback anywhere else in this
    codebase, so they must be written into config.toml for MoneyPrinterTurbo's
    existing config loader to see them. That's fine: config.toml lives only
    in the ephemeral GitHub Actions runner's filesystem and is never
    committed (see .gitignore) or logged.
  - YouTube/TikTok/Instagram credentials are read directly from the process
    environment by app/services/official_publish.py (see its *_env fallback
    properties), so the workflow should pass those as step-level `env:`
    straight from secrets and this script does not need to touch them at
    all -- one fewer place a secret could accidentally end up on disk.

Run this after `uv sync`, before `cli.py`. Fails loudly (non-zero exit) if a
required secret is missing, rather than silently generating a config.toml
that will fail deep inside video generation.
"""
import os
import sys

import toml

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
EXAMPLE_PATH = os.path.join(ROOT, "config.example.toml")
OUTPUT_PATH = os.path.join(ROOT, "config.toml")


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def main() -> int:
    with open(EXAMPLE_PATH, "r", encoding="utf-8") as fh:
        cfg = toml.load(fh)

    app = cfg.setdefault("app", {})

    # --- Stock footage sources -------------------------------------------------
    app["video_source"] = "pexels"
    app["pexels_api_keys"] = [_require("PEXELS_API_KEY")]
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if pixabay_key:
        app["pixabay_api_keys"] = [pixabay_key]

    # --- LLM (Groq free tier by default; fast enough for a short CI job) -------
    app["llm_provider"] = "groq"
    app["groq_api_key"] = _require("GROQ_API_KEY")
    app["groq_base_url"] = os.environ.get(
        "GROQ_BASE_URL", "https://api.groq.com/openai/v1"
    )
    app["groq_model_name"] = os.environ.get(
        "GROQ_MODEL_NAME", "llama-3.3-70b-versatile"
    )

    # --- Voice / subtitles: free, no key required -------------------------------
    # edge TTS and its default voice are already config.example.toml's defaults;
    # left untouched here on purpose.

    # --- Official-API publishing: enable + non-secret pipeline settings --------
    # The actual YouTube/TikTok/Instagram credentials are read from the process
    # environment directly by app/services/official_publish.py -- pass them as
    # step `env:` in the workflow, not through this file.
    app["official_publish_enabled"] = True
    app["official_publish_auto_upload"] = False  # workflow calls publish_video.py explicitly
    platforms = os.environ.get("OFFICIAL_PUBLISH_PLATFORMS", "youtube")
    app["official_publish_platforms"] = [p.strip() for p in platforms.split(",") if p.strip()]
    app["official_publish_youtube_privacy_status"] = os.environ.get(
        "YOUTUBE_PRIVACY_STATUS", "public"
    )
    app["tiktok_privacy_level"] = os.environ.get("TIKTOK_PRIVACY_LEVEL", "SELF_ONLY")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        toml.dump(cfg, fh)

    print(f"wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
