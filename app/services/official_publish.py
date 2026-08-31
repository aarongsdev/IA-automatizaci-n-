"""
Official-API publisher: uploads finished videos to YouTube, TikTok and
Instagram using each platform's own API directly, with no paid third-party
intermediary (unlike app/services/upload_post.py, which relays through the
paid Upload-Post service).

Design goal: drop-in alternative to `upload_post.py`. `app/services/task.py`
picks whichever service is active via `config.app.official_publish_enabled`;
when true, calls in this module are used in place of `upload_post`'s, with
the same `cross_post_video(video_path, title, platforms, youtube_extra=...)`
signature and the same `{"success": bool, ...}` result shape.

Every credential below is read from config.toml / environment variables and
is expected to come from GitHub Actions Secrets in production -- nothing is
hardcoded, and nothing is logged.

Platform notes (see PLAN_IMPLEMENTACION_GITHUB.md for the full writeup):
  - YouTube: no app-review gate. Works as soon as you have OAuth credentials
    and a refresh token. Subject to the standard Data API v3 daily quota
    (10,000 units/day; one upload costs ~1,600, so roughly 6 uploads/day
    before you'd need to request a quota increase).
  - TikTok: the Content Posting API is free, but until your app passes
    TikTok's audit, every post it creates is forced to private regardless of
    the privacy_level you request. That's a TikTok-side restriction this code
    cannot bypass -- it's expected during development.
  - Instagram: requires a Business (not Creator) account, and the Graph API
    needs a public `video_url` it can fetch -- it does not accept raw file
    uploads. This module gets that public URL for free by publishing the
    rendered video as a temporary GitHub Release asset (see
    github_asset_host.py) and deleting it again once Instagram has ingested
    the video.
"""
import os
import time
from typing import Optional

import requests
from loguru import logger

from app.config import config
from app.services import github_asset_host


# ---------------------------------------------------------------------------
# YouTube Data API v3
# ---------------------------------------------------------------------------

class YouTubePublisher:
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    UPLOAD_URL = (
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status"
    )

    @property
    def client_id(self) -> str:
        return config.app.get("youtube_client_id", "") or os.environ.get(
            "YOUTUBE_CLIENT_ID", ""
        )

    @property
    def client_secret(self) -> str:
        return config.app.get("youtube_client_secret", "") or os.environ.get(
            "YOUTUBE_CLIENT_SECRET", ""
        )

    @property
    def refresh_token(self) -> str:
        return config.app.get("youtube_refresh_token", "") or os.environ.get(
            "YOUTUBE_REFRESH_TOKEN", ""
        )

    @property
    def privacy_status(self) -> str:
        return config.app.get("official_publish_youtube_privacy_status", "public")

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    def _access_token(self) -> str:
        resp = requests.post(
            self.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def upload(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: Optional[list] = None,
    ) -> dict:
        if not self.is_configured():
            return {"success": False, "error": "YouTube publisher not configured"}
        if not os.path.exists(video_path):
            return {"success": False, "error": f"video file not found: {video_path}"}

        try:
            access_token = self._access_token()
        except requests.exceptions.RequestException as exc:
            logger.error(f"YouTube token refresh failed: {exc}")
            return {"success": False, "error": f"token refresh failed: {exc}"}

        file_size = os.path.getsize(video_path)
        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": (tags or [])[:500],
            },
            "status": {
                "privacyStatus": self.privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        try:
            init_resp = requests.post(
                self.UPLOAD_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Type": "video/mp4",
                    "X-Upload-Content-Length": str(file_size),
                },
                json=body,
                timeout=30,
            )
            init_resp.raise_for_status()
            upload_url = init_resp.headers["Location"]

            with open(video_path, "rb") as fh:
                video_bytes = fh.read()

            put_resp = requests.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(file_size),
                },
                data=video_bytes,
                timeout=600,
            )
            put_resp.raise_for_status()
            result = put_resp.json()
            video_id = result.get("id")
            logger.info(f"YouTube upload succeeded: video_id={video_id}")
            return {
                "success": True,
                "video_id": video_id,
                "url": f"https://youtube.com/watch?v={video_id}" if video_id else None,
            }
        except requests.exceptions.RequestException as exc:
            logger.error(f"YouTube upload failed: {exc}")
            return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# TikTok Content Posting API
# ---------------------------------------------------------------------------

class TikTokPublisher:
    TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
    INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

    @property
    def client_key(self) -> str:
        return config.app.get("tiktok_client_key", "") or os.environ.get(
            "TIKTOK_CLIENT_KEY", ""
        )

    @property
    def client_secret(self) -> str:
        return config.app.get("tiktok_client_secret", "") or os.environ.get(
            "TIKTOK_CLIENT_SECRET", ""
        )

    @property
    def refresh_token(self) -> str:
        return config.app.get("tiktok_refresh_token", "") or os.environ.get(
            "TIKTOK_REFRESH_TOKEN", ""
        )

    @property
    def privacy_level(self) -> str:
        return config.app.get("tiktok_privacy_level", "SELF_ONLY")

    def is_configured(self) -> bool:
        return bool(self.client_key and self.client_secret and self.refresh_token)

    def _access_token(self) -> str:
        resp = requests.post(
            self.TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key": self.client_key,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def upload(self, video_path: str, title: str) -> dict:
        if not self.is_configured():
            return {"success": False, "error": "TikTok publisher not configured"}
        if not os.path.exists(video_path):
            return {"success": False, "error": f"video file not found: {video_path}"}

        try:
            access_token = self._access_token()
        except requests.exceptions.RequestException as exc:
            logger.error(f"TikTok token refresh failed: {exc}")
            return {"success": False, "error": f"token refresh failed: {exc}"}

        file_size = os.path.getsize(video_path)
        chunk_size = file_size

        try:
            init_resp = requests.post(
                self.INIT_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                },
                json={
                    "post_info": {
                        "title": title[:150],
                        "privacy_level": self.privacy_level,
                        "disable_duet": False,
                        "disable_comment": False,
                        "disable_stitch": False,
                    },
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": file_size,
                        "chunk_size": chunk_size,
                        "total_chunk_count": 1,
                    },
                },
                timeout=30,
            )
            init_resp.raise_for_status()
            init_data = init_resp.json().get("data", {})
            upload_url = init_data.get("upload_url")
            publish_id = init_data.get("publish_id")
            if not upload_url or not publish_id:
                return {
                    "success": False,
                    "error": f"unexpected init response: {init_resp.text[:500]}",
                }

            with open(video_path, "rb") as fh:
                video_bytes = fh.read()

            put_resp = requests.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
                },
                data=video_bytes,
                timeout=600,
            )
            put_resp.raise_for_status()

            logger.info(
                f"TikTok upload accepted: publish_id={publish_id} "
                f"(privacy_level={self.privacy_level}; forced private until "
                f"your app passes TikTok's audit)"
            )
            return {"success": True, "publish_id": publish_id}
        except requests.exceptions.RequestException as exc:
            logger.error(f"TikTok upload failed: {exc}")
            return {"success": False, "error": str(exc)}

    def check_status(self, publish_id: str) -> dict:
        try:
            access_token = self._access_token()
            resp = requests.post(
                self.STATUS_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                },
                json={"publish_id": publish_id},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as exc:
            return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Instagram Graph API (Reels, Business accounts only)
# ---------------------------------------------------------------------------

class InstagramPublisher:
    GRAPH_BASE = "https://graph.facebook.com/v21.0"
    POLL_INTERVAL_SECONDS = 5
    POLL_TIMEOUT_SECONDS = 300

    @property
    def ig_user_id(self) -> str:
        return config.app.get("instagram_business_account_id", "") or os.environ.get(
            "INSTAGRAM_BUSINESS_ACCOUNT_ID", ""
        )

    @property
    def access_token(self) -> str:
        return config.app.get("instagram_access_token", "") or os.environ.get(
            "INSTAGRAM_ACCESS_TOKEN", ""
        )

    def is_configured(self) -> bool:
        return bool(self.ig_user_id and self.access_token)

    def upload(self, video_path: str, caption: str) -> dict:
        if not self.is_configured():
            return {"success": False, "error": "Instagram publisher not configured"}
        if not os.path.exists(video_path):
            return {"success": False, "error": f"video file not found: {video_path}"}

        hosted = github_asset_host.publish_temp_asset(video_path)
        if not hosted.get("success"):
            return {
                "success": False,
                "error": f"could not host video for Instagram to fetch: {hosted.get('error')}",
            }
        video_url = hosted["url"]
        release_id = hosted.get("release_id")
        tag = hosted.get("tag")

        try:
            create_resp = requests.post(
                f"{self.GRAPH_BASE}/{self.ig_user_id}/media",
                data={
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": caption[:2200],
                    "access_token": self.access_token,
                },
                timeout=60,
            )
            create_resp.raise_for_status()
            creation_id = create_resp.json().get("id")
            if not creation_id:
                return {
                    "success": False,
                    "error": f"unexpected container response: {create_resp.text[:500]}",
                }

            deadline = time.time() + self.POLL_TIMEOUT_SECONDS
            status_code = None
            while time.time() < deadline:
                status_resp = requests.get(
                    f"{self.GRAPH_BASE}/{creation_id}",
                    params={
                        "fields": "status_code",
                        "access_token": self.access_token,
                    },
                    timeout=30,
                )
                status_resp.raise_for_status()
                status_code = status_resp.json().get("status_code")
                if status_code == "FINISHED":
                    break
                if status_code == "ERROR":
                    return {
                        "success": False,
                        "error": "Instagram container processing failed",
                    }
                time.sleep(self.POLL_INTERVAL_SECONDS)

            if status_code != "FINISHED":
                return {
                    "success": False,
                    "error": f"timed out waiting for Instagram container, last status={status_code}",
                }

            publish_resp = requests.post(
                f"{self.GRAPH_BASE}/{self.ig_user_id}/media_publish",
                data={"creation_id": creation_id, "access_token": self.access_token},
                timeout=60,
            )
            publish_resp.raise_for_status()
            media_id = publish_resp.json().get("id")
            logger.info(f"Instagram Reel published: media_id={media_id}")
            return {"success": True, "media_id": media_id}
        except requests.exceptions.RequestException as exc:
            logger.error(f"Instagram publish failed: {exc}")
            return {"success": False, "error": str(exc)}
        finally:
            if release_id is not None:
                github_asset_host.delete_temp_asset(release_id, tag)


# ---------------------------------------------------------------------------
# Unified service, mirrors upload_post.UploadPostService's public interface
# ---------------------------------------------------------------------------

class OfficialPublishService:
    def __init__(self) -> None:
        self.youtube = YouTubePublisher()
        self.tiktok = TikTokPublisher()
        self.instagram = InstagramPublisher()

    @property
    def enabled(self) -> bool:
        return bool(config.app.get("official_publish_enabled", False))

    @property
    def auto_upload(self) -> bool:
        return bool(config.app.get("official_publish_auto_upload", False))

    @property
    def platforms(self) -> list:
        return config.app.get("official_publish_platforms", ["youtube"])

    @property
    def youtube_privacy_status(self) -> str:
        return self.youtube.privacy_status

    def is_configured(self) -> bool:
        return self.enabled and (
            self.youtube.is_configured()
            or self.tiktok.is_configured()
            or self.instagram.is_configured()
        )


official_publish_service = OfficialPublishService()


def cross_post_video(
    video_path: str,
    title: str,
    platforms: Optional[list] = None,
    youtube_extra: Optional[dict] = None,
) -> dict:
    """
    Same contract as upload_post.cross_post_video: returns a single dict
    summarizing every platform attempted, with a top-level "success" that is
    True only if every attempted platform succeeded.
    """
    if platforms is None:
        platforms = official_publish_service.platforms

    per_platform: dict = {}
    attempted = False

    if any(p.startswith("youtube") for p in platforms):
        if official_publish_service.youtube.is_configured():
            attempted = True
            extra = youtube_extra or {}
            per_platform["youtube"] = official_publish_service.youtube.upload(
                video_path,
                title=extra.get("youtube_title", title),
                description=extra.get("youtube_description", ""),
                tags=extra.get("tags", []),
            )
        else:
            logger.warning("YouTube requested but not configured; skipping")

    if "tiktok" in platforms:
        if official_publish_service.tiktok.is_configured():
            attempted = True
            per_platform["tiktok"] = official_publish_service.tiktok.upload(
                video_path, title=title
            )
        else:
            logger.warning("TikTok requested but not configured; skipping")

    if "instagram" in platforms:
        if official_publish_service.instagram.is_configured():
            attempted = True
            per_platform["instagram"] = official_publish_service.instagram.upload(
                video_path, caption=title
            )
        else:
            logger.warning("Instagram requested but not configured; skipping")

    if not attempted:
        return {
            "success": False,
            "error": "no requested platform is configured for official publishing",
            "platforms": per_platform,
        }

    all_succeeded = all(r.get("success") for r in per_platform.values())
    return {"success": all_succeeded, "platforms": per_platform}
