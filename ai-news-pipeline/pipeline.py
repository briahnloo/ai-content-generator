import yaml
from pathlib import Path
from dataclasses import dataclass
from core.models import ContentItem, Status
from core.database import Database
from services.ingestor import RSSIngestor
from services.script_generator import ScriptGenerator
from services.renderer import HeyGenRenderer, HeyGenConfig
from services.distributor import YouTubeDistributor, YouTubeCredentials
from services.content_scorer import ContentScorer
from config.settings import Settings

class Pipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database(settings.database_path)
        self.ingestor = RSSIngestor(self.db, settings.min_content_length, settings.max_age_hours)
        self.scorer = ContentScorer()
        self.script_gen = ScriptGenerator(settings.openai_api_key, settings.prompt_path)
        self.renderer = HeyGenRenderer(
            HeyGenConfig(settings.heygen_api_key, settings.heygen_avatar_id, settings.heygen_voice_id),
            settings.video_output_dir
        )
        self.distributor = YouTubeDistributor(YouTubeCredentials(
            settings.youtube_client_id,
            settings.youtube_client_secret,
            settings.youtube_refresh_token
        ))
        self.feeds = self._load_feeds()

    def _load_feeds(self) -> list[dict]:
        feeds_path = Path(__file__).parent / "config" / "feeds.yaml"
        with open(feeds_path) as f:
            return yaml.safe_load(f)["feeds"]

    def ingest(self, limit: int = 10) -> list[ContentItem]:
        items = []
        for feed in sorted(self.feeds, key=lambda f: f.get("priority", 99)):
            for item in self.ingestor.fetch(feed["url"], feed["name"]):
                self.db.save(item)
                items.append(item)
                print(f"[INGESTED] {item.title[:60]}...")
                if len(items) >= limit:
                    return items
        return items

    def score_content(self, limit: int = 20) -> list[ContentItem]:
        """
        Score ingested content to determine production worthiness.
        Items meeting the threshold move to SCORED status; others are marked SKIPPED.
        """
        if not self.settings.enable_scoring:
            print("[SCORING DISABLED] Skipping content scoring")
            return []

        items = self.db.get_by_status(Status.INGESTED, limit)
        scored = []
        skipped_count = 0

        for item in items:
            try:
                score, breakdown = self.scorer.score(item.title, item.raw_content, item.published_at)
                item.content_score = score
                item.score_breakdown = breakdown

                if self.scorer.is_worthy(score, self.settings.min_content_score):
                    item.status = Status.SCORED
                    self.db.save(item)
                    print(f"[SCORED] {score:.1f}/100 - {item.title[:50]}...")
                    scored.append(item)
                else:
                    item.status = Status.SKIPPED
                    self.db.save(item)
                    skipped_count += 1

            except Exception as e:
                item.error = str(e)
                item.status = Status.FAILED
                self.db.save(item)
                print(f"[FAILED] Scoring: {e}")

        if skipped_count > 0:
            print(f"[SKIPPED] {skipped_count} items below threshold ({self.settings.min_content_score})")

        return scored

    def generate_scripts(self, limit: int = 5) -> list[ContentItem]:
        # Use SCORED items if scoring enabled, otherwise INGESTED
        status = Status.SCORED if self.settings.enable_scoring else Status.INGESTED
        items = self.db.get_by_status(status, limit, order_by_score=self.settings.enable_scoring)
        processed = []

        for item in items:
            try:
                item.script = self.script_gen.generate(item)
                item.status = Status.SCRIPTED
                self.db.save(item)
                score_str = f" [Score: {item.content_score:.1f}]" if item.content_score else ""
                print(f"[SCRIPTED]{score_str} {item.title[:60]}...")
                processed.append(item)
            except Exception as e:
                item.error = str(e)
                item.status = Status.FAILED
                self.db.save(item)
                print(f"[FAILED] Script generation: {e}")

        return processed

    def render_videos(self, limit: int = 3) -> list[ContentItem]:
        items = self.db.get_by_status(Status.SCRIPTED, limit)
        processed = []

        for item in items:
            try:
                item.status = Status.RENDERING
                self.db.save(item)

                job_id = self.renderer.submit(item.script)
                print(f"[RENDERING] Job {job_id} for: {item.title[:40]}...")

                job = self.renderer.wait_for_completion(job_id)
                video_path = self.renderer.download(job.video_url, item.id)

                item.video_url = job.video_url
                item.video_path = str(video_path)
                item.status = Status.RENDERED
                self.db.save(item)
                print(f"[RENDERED] {item.title[:60]}...")
                processed.append(item)

            except Exception as e:
                item.error = str(e)
                item.status = Status.FAILED
                item.retry_count += 1
                self.db.save(item)
                print(f"[FAILED] Render: {e}")

        return processed

    def upload_videos(self, limit: int = 5) -> list[ContentItem]:
        items = self.db.get_by_status(Status.RENDERED, limit)
        processed = []

        for item in items:
            try:
                description = f"{item.title}\n\nSource: {item.source_name}\n{item.source_url}"
                tags = ["news", "breaking news", "world news", item.source_name.lower()]

                video_id = self.distributor.upload(
                    Path(item.video_path),
                    item.title,
                    description,
                    tags
                )

                item.youtube_id = video_id
                item.status = Status.UPLOADED
                self.db.save(item)
                print(f"[UPLOADED] https://youtube.com/watch?v={video_id} (private)")
                processed.append(item)

            except Exception as e:
                item.error = str(e)
                item.status = Status.FAILED
                self.db.save(item)
                print(f"[FAILED] Upload: {e}")

        return processed

    def run_full(self, ingest_limit: int = 10, process_limit: int = 3):
        print("\n=== INGESTING ===")
        self.ingest(ingest_limit)

        if self.settings.enable_scoring:
            print("\n=== SCORING CONTENT ===")
            self.score_content(ingest_limit)

        print("\n=== GENERATING SCRIPTS ===")
        self.generate_scripts(process_limit)

        print("\n=== RENDERING VIDEOS ===")
        self.render_videos(process_limit)

        print("\n=== UPLOADING TO YOUTUBE ===")
        self.upload_videos(process_limit)

        print("\n=== COMPLETE ===")
