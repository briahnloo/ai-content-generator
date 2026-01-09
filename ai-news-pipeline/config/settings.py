import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    # API Keys
    openai_api_key: str
    heygen_api_key: str
    heygen_avatar_id: str
    heygen_voice_id: str

    # YouTube
    youtube_client_id: str
    youtube_client_secret: str
    youtube_refresh_token: str

    # Paths
    database_path: str
    video_output_dir: Path
    prompt_path: Path

    # Pipeline
    min_content_length: int
    max_age_hours: int
    max_retries: int

    # Content Scoring
    min_content_score: float
    enable_scoring: bool
    require_hard_news: bool
    fluff_penalty_multiplier: float

    @classmethod
    def from_env(cls) -> "Settings":
        base_dir = Path(__file__).parent.parent
        return cls(
            openai_api_key=os.environ["OPENAI_API_KEY"],
            heygen_api_key=os.environ["HEYGEN_API_KEY"],
            heygen_avatar_id=os.environ["HEYGEN_AVATAR_ID"],
            heygen_voice_id=os.environ["HEYGEN_VOICE_ID"],
            youtube_client_id=os.environ["YOUTUBE_CLIENT_ID"],
            youtube_client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
            youtube_refresh_token=os.environ.get("YOUTUBE_REFRESH_TOKEN", ""),
            database_path=os.environ.get("DATABASE_PATH", "./data/pipeline.db"),
            video_output_dir=Path(os.environ.get("VIDEO_OUTPUT_DIR", "./data/videos")),
            prompt_path=base_dir / "config" / "prompts" / "news_script.txt",
            min_content_length=int(os.environ.get("MIN_CONTENT_LENGTH", "150")),
            max_age_hours=int(os.environ.get("MAX_AGE_HOURS", "24")),
            max_retries=int(os.environ.get("MAX_RETRIES", "3")),
            min_content_score=float(os.environ.get("MIN_CONTENT_SCORE", "50.0")),
            enable_scoring=os.environ.get("ENABLE_SCORING", "true").lower() == "true",
            require_hard_news=os.environ.get("REQUIRE_HARD_NEWS", "false").lower() == "true",
            fluff_penalty_multiplier=float(os.environ.get("FLUFF_PENALTY_MULTIPLIER", "1.5"))
        )
