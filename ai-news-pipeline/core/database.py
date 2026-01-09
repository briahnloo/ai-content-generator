import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
from dateutil import parser as date_parser
from core.models import ContentItem, Status

class Database:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS content (
                    id TEXT PRIMARY KEY,
                    source_url TEXT UNIQUE NOT NULL,
                    source_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    raw_content TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ingested',
                    ingested_at TIMESTAMP NOT NULL,
                    author TEXT,
                    published_at TIMESTAMP,
                    script TEXT,
                    video_url TEXT,
                    video_path TEXT,
                    youtube_id TEXT,
                    content_score REAL,
                    score_breakdown TEXT,
                    error TEXT,
                    retry_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON content(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source_url ON content(source_url)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_score ON content(content_score DESC)")

    def exists(self, url: str, hours: int = 72) -> bool:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM content WHERE source_url = ? AND ingested_at > ?",
                (url, self._format_timestamp(cutoff))
            ).fetchone()
            return row is not None

    def _format_timestamp(self, dt: Optional[datetime]) -> Optional[str]:
        """Convert datetime to ISO format string for storage."""
        if dt is None:
            return None
        # Remove timezone info to avoid parsing issues
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)
        return dt.isoformat()

    def save(self, item: ContentItem):
        with self._conn() as conn:
            score_breakdown_json = json.dumps(item.score_breakdown) if item.score_breakdown else None
            conn.execute("""
                INSERT OR REPLACE INTO content
                (id, source_url, source_name, title, raw_content, status, ingested_at,
                 author, published_at, script, video_url, video_path, youtube_id,
                 content_score, score_breakdown, error, retry_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.id, item.source_url, item.source_name, item.title, item.raw_content,
                item.status.value, self._format_timestamp(item.ingested_at), item.author,
                self._format_timestamp(item.published_at), item.script, item.video_url,
                item.video_path, item.youtube_id, item.content_score, score_breakdown_json,
                item.error, item.retry_count, self._format_timestamp(datetime.utcnow())
            ))

    def get_by_status(self, status: Status, limit: int = 10, order_by_score: bool = False) -> list[ContentItem]:
        with self._conn() as conn:
            if order_by_score:
                rows = conn.execute(
                    "SELECT * FROM content WHERE status = ? ORDER BY content_score DESC, ingested_at DESC LIMIT ?",
                    (status.value, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM content WHERE status = ? ORDER BY ingested_at DESC LIMIT ?",
                    (status.value, limit)
                ).fetchall()
            return [self._row_to_item(r) for r in rows]

    def get_by_id(self, id: str) -> Optional[ContentItem]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM content WHERE id = ?", (id,)).fetchone()
            return self._row_to_item(row) if row else None

    def _parse_timestamp(self, value: any) -> Optional[datetime]:
        """Safely parse timestamp from database."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            # Handle string timestamps
            return date_parser.parse(str(value))
        except:
            return None

    def _row_to_item(self, row: sqlite3.Row) -> ContentItem:
        score_breakdown = json.loads(row["score_breakdown"]) if row["score_breakdown"] else None
        return ContentItem(
            id=row["id"],
            source_url=row["source_url"],
            source_name=row["source_name"],
            title=row["title"],
            raw_content=row["raw_content"],
            status=Status(row["status"]),
            ingested_at=self._parse_timestamp(row["ingested_at"]),
            author=row["author"],
            published_at=self._parse_timestamp(row["published_at"]),
            script=row["script"],
            video_url=row["video_url"],
            video_path=row["video_path"],
            youtube_id=row["youtube_id"],
            content_score=row["content_score"],
            score_breakdown=score_breakdown,
            error=row["error"],
            retry_count=row["retry_count"]
        )
