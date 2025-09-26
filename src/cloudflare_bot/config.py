"""Configuration helpers for the Cloudflare Blog automation bot."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


DEFAULT_FEED_URL = "https://blog.cloudflare.com/rss/"
DEFAULT_DATABASE_PATH = "cloudflare_blog.db"


@dataclass(slots=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    feed_url: str = DEFAULT_FEED_URL
    database_path: str = DEFAULT_DATABASE_PATH
    openai_api_key: Optional[str] = None
    wecom_webhook: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""

        return cls(
            feed_url=os.getenv("CF_BLOG_FEED", DEFAULT_FEED_URL),
            database_path=os.getenv("CF_BLOG_DB", DEFAULT_DATABASE_PATH),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            wecom_webhook=os.getenv("WECOM_WEBHOOK"),
        )
