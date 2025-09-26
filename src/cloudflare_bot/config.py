"""Configuration helpers for the Cloudflare Blog automation bot."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


DEFAULT_FEED_URL = "https://blog.cloudflare.com/rss/"
DEFAULT_DATABASE_PATH = "cloudflare_blog.db"
DEFAULT_INITIAL_SUMMARY_LIMIT = 5

load_dotenv()


@dataclass(slots=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    feed_url: str = DEFAULT_FEED_URL
    database_path: str = DEFAULT_DATABASE_PATH
    openai_api_key: Optional[str] = None
    llm_api_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    llm_message_key: str = "messages"
    wecom_webhook: Optional[str] = None
    initial_summary_limit: int = DEFAULT_INITIAL_SUMMARY_LIMIT

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""

        return cls(
            feed_url=os.getenv("CF_BLOG_FEED", DEFAULT_FEED_URL),
            database_path=os.getenv("CF_BLOG_DB", DEFAULT_DATABASE_PATH),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            llm_api_url=os.getenv("LLM_API_URL"),
            llm_api_key=os.getenv("LLM_API_KEY"),
            llm_model=os.getenv("LLM_MODEL"),
            llm_message_key=os.getenv("LLM_MESSAGE_KEY", "messages"),
            wecom_webhook=os.getenv("WECOM_WEBHOOK"),
            initial_summary_limit=_get_int(
                "CF_BLOG_INITIAL_SUMMARY_LIMIT", DEFAULT_INITIAL_SUMMARY_LIMIT
            ),
        )


def _get_int(var_name: str, default: int) -> int:
    """Read an integer environment variable, falling back to ``default``."""

    raw_value = os.getenv(var_name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return max(0, value)
