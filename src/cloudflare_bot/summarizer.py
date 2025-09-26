"""Summarisation utilities for generating Chinese briefs of Cloudflare posts."""

from __future__ import annotations

import os
import re
from typing import Optional

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore


def generate_brief(
    title: str,
    content: str,
    openai_api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> str:
    """Generate a concise Chinese brief for the article."""

    # Prefer LLM if credentials are provided
    api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    if api_key and OpenAI is not None:
        client = OpenAI(api_key=api_key)
        prompt = (
            "请阅读以下 Cloudflare 博客文章内容，"
            "用简洁的中文撰写一段 3-5 句的摘要，突出核心问题、解决方案和影响。"
            "摘要应包含一个合适的标题。文章标题："
            f"{title}\n\n正文：\n{content[:6000]}"
        )
        response = client.responses.create(
            model=model,
            input=[{"role": "user", "content": prompt}],
        )
        completion = response.output_text.strip()
        if completion:
            return completion

    # Fallback heuristic summarisation if no API key is available
    sentences = _split_sentences(content)
    preview = "".join(sentences[:3]).strip()
    if not preview:
        preview = content[:280]
    return f"《{title}》摘要：{preview}"


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences by punctuation for the fallback summariser."""

    parts = re.split(r"(?<=[。！？])\s+", text)
    return [part.strip() for part in parts if part.strip()]
