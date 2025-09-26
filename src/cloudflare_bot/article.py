"""Utilities for downloading Cloudflare Blog posts and extracting clean text."""

from __future__ import annotations

import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)


def fetch_article_html(url: str, timeout: int = 20) -> str:
    """Download the raw HTML for a blog post."""

    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def extract_main_text(html: str) -> str:
    """Extract readable article text from a Cloudflare Blog HTML page."""

    soup = BeautifulSoup(html, "html.parser")
    article_tag = soup.find("article") or soup.find("main") or soup

    paragraphs = []
    for element in article_tag.find_all(["p", "li"]):
        text = element.get_text(strip=True)
        if text:
            paragraphs.append(text)

    # Fallback to any paragraph content if the article tag did not produce text
    if not paragraphs:
        for element in soup.find_all("p"):
            text = element.get_text(strip=True)
            if text:
                paragraphs.append(text)

    return "\n\n".join(paragraphs)


def get_article_text(url: str, timeout: int = 20) -> Optional[str]:
    """Convenience helper to retrieve and extract article text."""

    try:
        html = fetch_article_html(url, timeout=timeout)
    except requests.RequestException as exc:  # pragma: no cover - network failure
        LOGGER.warning("Failed to download article %s: %s", url, exc)
        return None

    text = extract_main_text(html)
    if not text:
        LOGGER.warning("No textual content extracted from %s", url)
        return None
    return text
