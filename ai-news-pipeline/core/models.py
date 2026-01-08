from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import hashlib

class Status(Enum):
    INGESTED = "ingested"
    SCORED = "scored"
    SCRIPTED = "scripted"
    RENDERING = "rendering"
    RENDERED = "rendered"
    UPLOADED = "uploaded"
    PUBLISHED = "published"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class ContentItem:
    source_url: str
    source_name: str
    title: str
    raw_content: str
    id: str = field(default="")
    status: Status = Status.INGESTED
    ingested_at: datetime = field(default_factory=datetime.utcnow)

    # Processing outputs
    script: Optional[str] = None
    video_url: Optional[str] = None
    video_path: Optional[str] = None
    youtube_id: Optional[str] = None

    # Metadata
    author: Optional[str] = None
    published_at: Optional[datetime] = None

    # Content scoring
    content_score: Optional[float] = None
    score_breakdown: Optional[dict] = None

    # Error tracking
    error: Optional[str] = None
    retry_count: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.sha256(self.source_url.encode()).hexdigest()[:16]

@dataclass
class RenderJob:
    id: str
    content_id: str
    status: str
    video_url: Optional[str] = None
    error: Optional[str] = None
