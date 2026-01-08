import feedparser
from datetime import datetime
from dateutil import parser as date_parser
from typing import Iterator
from core.models import ContentItem
from core.database import Database

class RSSIngestor:
    def __init__(self, db: Database, min_length: int = 150, max_age_hours: int = 24):
        self.db = db
        self.min_length = min_length
        self.max_age_hours = max_age_hours

    def fetch(self, feed_url: str, source_name: str) -> Iterator[ContentItem]:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries:
            content = self._extract_content(entry)

            if len(content) < self.min_length:
                continue

            if self.db.exists(entry.link):
                continue

            published = self._parse_date(entry.get("published"))
            if published and self._is_too_old(published):
                continue

            yield ContentItem(
                source_url=entry.link,
                source_name=source_name,
                title=entry.title,
                raw_content=content,
                author=entry.get("author"),
                published_at=published
            )

    def _extract_content(self, entry) -> str:
        if "content" in entry and entry.content:
            return entry.content[0].get("value", "")
        return entry.get("summary", "") or entry.get("description", "")

    def _parse_date(self, date_str: str) -> datetime | None:
        if not date_str:
            return None
        try:
            return date_parser.parse(date_str)
        except:
            return None

    def _is_too_old(self, dt: datetime) -> bool:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=self.max_age_hours)
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)
        return dt < cutoff
