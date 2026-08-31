"""
Temporary public hosting for the rendered video via a GitHub Release asset.

Why this exists: the Instagram Graph API's Reels publishing endpoint requires a
publicly reachable `video_url` it can fetch itself -- it does not accept a raw
file upload. This project has no paid storage/CDN (COST_MODE=ZERO), so instead
of standing up S3/Cloudflare R2/etc., we reuse something already free and
already available inside the GitHub Actions workflow: the repository's own
Releases, which serve asset files over plain HTTPS with no authentication
required *as long as the repository is public*.

This only works for a public repository. GitHub Actions Secrets are never
exposed to workflow logs or to visitors of a public repo, so making the repo
public to unlock this (and unlimited free Actions minutes) does not leak your
API keys -- it only makes your *code* and *released video files* public.
If you'd rather keep the repo private, skip Instagram publishing or point
`instagram_video_url_override` at your own public storage instead.

Uses the `GITHUB_TOKEN` that GitHub Actions injects automatically into every
job -- no extra secret needed for this helper.
"""
import os
import time
from typing import Optional

import requests
from loguru import logger

GITHUB_API = "https://api.github.com"


class GithubAssetHostError(RuntimeError):
    pass


def _repo_slug() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        raise GithubAssetHostError(
            "GITHUB_REPOSITORY is not set; this helper only works inside a "
            "GitHub Actions job."
        )
    return repo


def _token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "") or os.environ.get("GH_TOKEN", "")
    if not token:
        raise GithubAssetHostError(
            "GITHUB_TOKEN is not set. Add 'permissions: contents: write' to the "
            "workflow job so GitHub injects a token that can create releases."
        )
    return token


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def publish_temp_asset(file_path: str, *, tag_prefix: str = "episode") -> dict:
    """
    Upload `file_path` as the sole asset of a brand-new draft-free release, and
    return its public download URL.

    Returns: {"success": True, "url": ..., "release_id": ..., "tag": ...}
             {"success": False, "error": ...} on failure.
    """
    if not os.path.exists(file_path):
        return {"success": False, "error": f"file not found: {file_path}"}

    repo = _repo_slug()
    tag = f"{tag_prefix}-{int(time.time())}"
    file_name = os.path.basename(file_path)

    try:
        create_resp = requests.post(
            f"{GITHUB_API}/repos/{repo}/releases",
            headers=_headers(),
            json={
                "tag_name": tag,
                "name": tag,
                "body": (
                    "Temporary asset used to give the Instagram Graph API a "
                    "public video_url. Safe to delete once publishing succeeds; "
                    "the daily workflow prunes these automatically."
                ),
                "draft": False,
                "prerelease": True,
            },
            timeout=30,
        )
        create_resp.raise_for_status()
        release = create_resp.json()
        release_id = release["id"]
        upload_url_template = release["upload_url"]  # has {?name,label} suffix
        upload_url = upload_url_template.split("{")[0]

        with open(file_path, "rb") as fh:
            data = fh.read()

        upload_resp = requests.post(
            upload_url,
            headers={**_headers(), "Content-Type": "video/mp4"},
            params={"name": file_name},
            data=data,
            timeout=300,
        )
        upload_resp.raise_for_status()
        asset = upload_resp.json()

        return {
            "success": True,
            "url": asset["browser_download_url"],
            "release_id": release_id,
            "tag": tag,
        }
    except requests.exceptions.RequestException as exc:
        logger.error(f"failed to publish temp GitHub release asset: {exc}")
        return {"success": False, "error": str(exc)}


def delete_temp_asset(release_id: int, tag: Optional[str] = None) -> None:
    """Best-effort cleanup: delete the release (and its tag ref) after use."""
    repo = _repo_slug()
    try:
        requests.delete(
            f"{GITHUB_API}/repos/{repo}/releases/{release_id}",
            headers=_headers(),
            timeout=30,
        ).raise_for_status()
    except requests.exceptions.RequestException as exc:
        logger.warning(f"failed to delete temp release {release_id}: {exc}")

    if tag:
        try:
            requests.delete(
                f"{GITHUB_API}/repos/{repo}/git/refs/tags/{tag}",
                headers=_headers(),
                timeout=30,
            ).raise_for_status()
        except requests.exceptions.RequestException as exc:
            logger.warning(f"failed to delete temp tag {tag}: {exc}")
