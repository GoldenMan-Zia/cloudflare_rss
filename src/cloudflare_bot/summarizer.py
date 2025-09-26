"""Summarisation utilities for generating Chinese briefs of Cloudflare posts."""

from __future__ import annotations

import os
import re
from typing import Any, Optional

import requests

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore


def generate_brief(
    title: str,
    content: str,
    openai_api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
    custom_api_url: Optional[str] = None,
    custom_api_key: Optional[str] = None,
    custom_model: Optional[str] = None,
    custom_message_key: str = "messages",
) -> str:
    """Generate a concise Chinese brief for the article."""

    # Prefer LLM if credentials are provided
    prompt = (
        "请阅读以下 Cloudflare 博客文章内容，"
        "用简洁的中文撰写一段 3-5 句的摘要，突出核心问题、解决方案和影响。"
        "摘要应包含一个合适的标题。文章标题："
        f"{title}\n\n正文：\n{content[:6000]}"
    )

    api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    custom_url = custom_api_url or os.getenv("LLM_API_URL")
    custom_key = custom_api_key or os.getenv("LLM_API_KEY")
    custom_model_name = custom_model or os.getenv("LLM_MODEL") or model
    message_key = custom_message_key or os.getenv("LLM_MESSAGE_KEY") or "messages"

    if custom_url:
        completion = _call_custom_llm(
            prompt,
            custom_url,
            custom_key,
            custom_model_name,
            message_key,
        )
        if completion:
            return completion

    if api_key and OpenAI is not None:
        client = OpenAI(api_key=api_key)
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


def _call_custom_llm(
    prompt: str,
    api_url: str,
    api_key: Optional[str],
    model: str,
    message_key: str,
) -> Optional[str]:
    """Send the prompt to a custom LLM HTTP endpoint."""

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload: dict[str, Any] = {"model": model, message_key: [{"role": "user", "content": prompt}]}

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    completion = _extract_text_from_response(data)
    if completion:
        return completion.strip()
    return None


def _extract_text_from_response(data: Any) -> Optional[str]:
    """Extract assistant text from a generic chat completion response."""

    if isinstance(data, dict):
        output_text = data.get("output_text")
        if isinstance(output_text, str):
            return output_text

        choices = data.get("choices")
        if isinstance(choices, list):
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                message = choice.get("message") or choice.get("delta")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        return content
                    if isinstance(content, list):
                        parts = [part.get("text") for part in content if isinstance(part, dict)]
                        joined = "".join(part for part in parts if isinstance(part, str))
                        if joined:
                            return joined
                content = choice.get("text")
                if isinstance(content, str):
                    return content

        result = data.get("result")
        if isinstance(result, str):
            return result

    return None
