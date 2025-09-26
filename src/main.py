"""Entry point for the Cloudflare Blog automation workflow."""

from __future__ import annotations

import logging
from typing import Iterable, Sequence, Tuple

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


def persist_entries_without_summary(
    entries: Iterable[rss.FeedEntry], settings: config.Settings
) -> None:
    """Persist entries without generating summaries or sending notifications."""

    for entry in entries:
        LOGGER.info("Storing entry without summary: %s", entry.title)
        record = storage.ArticleRecord(
            id=entry.id,
            title=entry.title,
            link=entry.link,
            published=entry.published,
            summary_zh=None,
        )
        storage.save_article(settings.database_path, record)


def split_initial_entries(
    entries: Sequence[rss.FeedEntry],
    limit: int,
) -> Tuple[Sequence[rss.FeedEntry], Sequence[rss.FeedEntry]]:
    """Return entries that should be summarised and those only persisted."""

    if limit <= 0:
        return (), entries

    sorted_entries = sorted(entries, key=lambda entry: entry.published, reverse=True)
    to_summarise = sorted_entries[:limit]
    to_archive = sorted_entries[limit:]
    return to_summarise, to_archive


def main() -> None:
    settings = config.Settings.from_env()
    storage.initialize_database(settings.database_path)

    entries = rss.parse_feed(settings.feed_url)
    known_ids = storage.get_known_ids(settings.database_path)
    new_entries = rss.filter_new_entries(entries, known_ids)
    LOGGER.info("Found %d new entries", len(new_entries))

    if not known_ids and new_entries:
        to_process, to_store_only = split_initial_entries(
            new_entries, settings.initial_summary_limit
        )
        if to_store_only:
            LOGGER.info(
                "Initial sync: persisting %d additional entries without summaries",
                len(to_store_only),
            )
            persist_entries_without_summary(to_store_only, settings)
        process_entries(to_process, settings)
        return

    process_entries(new_entries, settings)


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    main()
