"""Webhook integration for sending summaries to a WeCom robot."""

from __future__ import annotations

from typing import Optional

import requests


class NotificationError(RuntimeError):
    """Raised when the WeCom webhook call fails."""


def send_wecom_message(summary: str, link: str, webhook_url: Optional[str]) -> None:
    """Send the generated summary to the configured WeCom webhook."""

    if not webhook_url:
        raise NotificationError("WeCom webhook URL is not configured")

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": f"{summary}\n\n[阅读原文]({link})",
        },
    }
    response = requests.post(webhook_url, json=payload, timeout=10)
    if response.status_code != 200 or response.json().get("errcode") != 0:
        raise NotificationError(
            f"Failed to send notification: {response.status_code} {response.text}"
        )
