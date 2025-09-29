"""Webhook integration for sending summaries to a WeCom robot."""

from __future__ import annotations

from typing import Optional

import requests

from . import summarizer


class NotificationError(RuntimeError):
    """Raised when the WeCom webhook call fails."""


def send_wecom_message(
    brief: summarizer.Brief,
    title: str,
    link: str,
    webhook_url: Optional[str],
) -> None:
    """Send the generated summary to the configured WeCom webhook."""

    if not webhook_url:
        raise NotificationError("WeCom webhook URL is not configured")

    category_block = (
        f"【<font color=\"red\">{brief.category}</font>】" if brief.category else ""
    )
    header = f"{category_block}<font color=\"info\">{title}</font>"
    content_lines = [
        header,
        "**简报**",
        brief.summary,
        "",
        f"[原文链接]({link})",
    ]
    markdown_content = "\n".join(line for line in content_lines if line is not None)

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": markdown_content,
        },
    }
    response = requests.post(webhook_url, json=payload, timeout=10)
    if response.status_code != 200 or response.json().get("errcode") != 0:
        raise NotificationError(
            f"Failed to send notification: {response.status_code} {response.text}"
        )
