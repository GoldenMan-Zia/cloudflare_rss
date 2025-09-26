"""Entry point for the Cloudflare Blog automation workflow."""

from __future__ import annotations

import logging
from typing import Iterable

from cloudflare_bot import article, config, notifier, rss, storage, summarizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
LOGGER = logging.getLogger(__name__)


def process_entries(entries: Iterable[rss.FeedEntry], settings: config.Settings) -> None:
    """Process RSS entries, persisting new ones and notifying WeCom."""

    for entry in entries:
        LOGGER.info("Processing entry: %s", entry.title)
        content = article.get_article_text(entry.link)
        if not content:
            LOGGER.warning("Skipping %s due to missing content", entry.link)
            continue

        summary = summarizer.generate_brief(entry.title, content, settings.openai_api_key)
        record = storage.ArticleRecord(
            id=entry.id,
            title=entry.title,
            link=entry.link,
            published=entry.published,
            summary_zh=summary,
        )
        storage.save_article(settings.database_path, record)

        try:
            notifier.send_wecom_message(summary, entry.link, settings.wecom_webhook)
        except notifier.NotificationError as exc:
            LOGGER.error("Failed to send notification for %s: %s", entry.link, exc)


def main() -> None:
    settings = config.Settings.from_env()
    storage.initialize_database(settings.database_path)

    entries = rss.parse_feed(settings.feed_url)
    known_ids = storage.get_known_ids(settings.database_path)
    new_entries = rss.filter_new_entries(entries, known_ids)
    LOGGER.info("Found %d new entries", len(new_entries))
    process_entries(new_entries, settings)


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    main()
