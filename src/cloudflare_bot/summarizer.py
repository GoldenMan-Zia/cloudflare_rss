"""Summarisation utilities for generating Chinese briefs of Cloudflare posts."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Optional

import requests

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore


@dataclass(slots=True)
class Brief:
    """Structured information for a single article brief."""

    category: str
    summary: str

    def format_plaintext(self, title: str) -> str:
        """Return a human-readable representation without colour markup."""

        prefix = f"【{self.category}】" if self.category else ""
        header = f"{prefix}{title}".strip()
        if not self.summary:
            return header
        return f"{header}\n{self.summary}" if header else self.summary


def generate_brief(
    title: str,
    content: str,
    openai_api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
    custom_api_url: Optional[str] = None,
    custom_api_key: Optional[str] = None,
    custom_model: Optional[str] = None,
    custom_message_key: str = "messages",
) -> Brief:
    """Generate a concise Chinese brief for the article."""

    # Prefer LLM if credentials are provided
    prompt = (
        "请阅读以下 Cloudflare 博客文章内容，"
        "用简洁的中文撰写一段 3-5 句的摘要，突出核心问题、解决方案和影响。"
        "请输出 JSON，包含两个字段：category（2-6 字的中文标签，概括文章类型，例"
        "如“技术分享”“功能更新”“新闻”等），summary（摘要正文，不包含 Markdown 或"
        "多余引号）。文章标题："
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
            parsed = _parse_structured_brief(completion)
            if parsed:
                return parsed

    if api_key and OpenAI is not None:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=model,
            input=[{"role": "user", "content": prompt}],
        )
        completion = response.output_text.strip()
        parsed = _parse_structured_brief(completion)
        if parsed:
            return parsed

    # Fallback heuristic summarisation if no API key is available
    sentences = _split_sentences(content)
    preview = "".join(sentences[:3]).strip()
    if not preview:
        preview = content[:280]
    if not preview:
        preview = "本文暂无可用摘要，请查看原文。"
    category = _infer_category(title, content)
    return Brief(category=category, summary=preview)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences by punctuation for the fallback summariser."""

    parts = re.split(r"(?<=[。！？])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def _parse_structured_brief(text: str) -> Optional[Brief]:
    """Attempt to parse the LLM response into a :class:`Brief`."""

    if not text:
        return None

    data = _loads_json_safely(text)
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                brief = _brief_from_mapping(item)
                if brief:
                    return brief
    elif isinstance(data, dict):
        brief = _brief_from_mapping(data)
        if brief:
            return brief

    # Fallback heuristic parsing when LLM returns plain text
    category_match = re.search(r"类别[：:]\s*([\w\u4e00-\u9fff]+)", text)
    summary_match = re.search(r"摘要[：:](.*)", text, re.S)
    category = category_match.group(1).strip() if category_match else ""
    summary = summary_match.group(1).strip() if summary_match else text.strip()
    if category and summary:
        return Brief(category=category, summary=_normalise_summary(summary))
    return None


def _loads_json_safely(text: str) -> Any:
    """Load JSON while being tolerant to stray characters."""

    import json

    cleaned = text.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Attempt to trim leading/trailing noise
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and start < end:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def _brief_from_mapping(data: dict[str, Any]) -> Optional[Brief]:
    """Create a :class:`Brief` from a mapping if possible."""

    category = str(
        data.get("category")
        or data.get("标签")
        or data.get("type")
        or ""
    ).strip()
    summary = str(data.get("summary") or data.get("摘要") or "").strip()
    if not category or not summary:
        return None
    return Brief(category=category, summary=_normalise_summary(summary))


def _normalise_summary(text: str) -> str:
    """Normalise whitespace in summary text."""

    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    return cleaned.strip()


def _infer_category(title: str, content: str) -> str:
    """Infer a best-effort category when no LLM is available."""

    text = f"{title}\n{content[:600]}".lower()
    heuristics = [
        (("security", "vulnerability", "漏洞", "攻击"), "安全更新"),
        (("tutorial", "guide", "how to", "指南", "教程"), "技术分享"),
        (("beta", "launch", "new", "update", "发布", "上线"), "功能更新"),
        (("report", "trend", "analysis", "洞察", "报告"), "趋势洞察"),
        (("event", "webinar", "conference", "活动", "峰会"), "活动预告"),
    ]
    for keywords, category in heuristics:
        if any(keyword in text for keyword in keywords):
            return category
    return "新闻"


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
