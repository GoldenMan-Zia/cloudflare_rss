"""Utilities for retrieving and parsing the Cloudflare Blog RSS feed."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

import feedparser


@dataclass(slots=True)
class FeedEntry:
    """Structured representation of a single RSS feed entry."""

    id: str
    title: str
    link: str
    published: datetime


def parse_feed(feed_url: str) -> List[FeedEntry]:
    """Fetch and parse the RSS feed, returning the most recent entries."""

    parsed = feedparser.parse(feed_url)
    entries: List[FeedEntry] = []
    for entry in parsed.entries:
        published = _normalise_published(entry)
        entries.append(
            FeedEntry(
                id=getattr(entry, "id", entry.link),
                title=entry.title,
                link=entry.link,
                published=published,
            )
        )
    return entries


def _normalise_published(entry: feedparser.FeedParserDict) -> datetime:
    """Convert the RSS published metadata into a ``datetime`` object."""

    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6])
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6])
    return datetime.utcnow()


def filter_new_entries(entries: Iterable[FeedEntry], existing_ids: Iterable[str]) -> List[FeedEntry]:
    """Return feed entries that do not already exist in the provided IDs."""

    existing = set(existing_ids)
    return [entry for entry in entries if entry.id not in existing]
