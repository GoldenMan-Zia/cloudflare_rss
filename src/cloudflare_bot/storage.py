"""SQLite persistence for tracking processed Cloudflare Blog posts."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, Optional


@dataclass(slots=True)
class ArticleRecord:
    """Representation of an article stored in the database."""

    id: str
    title: str
    link: str
    published: datetime
    summary_zh: Optional[str]


SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    link TEXT NOT NULL,
    published TEXT NOT NULL,
    summary_zh TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


@contextmanager
def connect(path: str) -> Iterator[sqlite3.Connection]:
    """Context manager returning a SQLite connection with foreign keys enabled."""

    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON;")
        yield connection
    finally:
        connection.commit()
        connection.close()


def initialize_database(path: str) -> None:
    """Create the necessary database tables if they do not exist."""

    with connect(path) as conn:
        conn.executescript(SCHEMA)


def get_known_ids(path: str) -> Iterable[str]:
    """Return the IDs of articles that already exist in storage."""

    with connect(path) as conn:
        cursor = conn.execute("SELECT id FROM articles")
        return [row[0] for row in cursor.fetchall()]


def save_article(path: str, article: ArticleRecord) -> None:
    """Persist a processed article to the database."""

    with connect(path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO articles (id, title, link, published, summary_zh)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                article.id,
                article.title,
                article.link,
                article.published.isoformat(),
                article.summary_zh,
            ),
        )
