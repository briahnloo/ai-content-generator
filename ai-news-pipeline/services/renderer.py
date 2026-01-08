import httpx
import asyncio
import time
from pathlib import Path
from dataclasses import dataclass
from core.models import RenderJob

@dataclass
class HeyGenConfig:
    api_key: str
    avatar_id: str
    voice_id: str

class HeyGenRenderer:
    BASE_URL = "https://api.heygen.com/v2"

    def __init__(self, config: HeyGenConfig, output_dir: Path):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {"X-Api-Key": config.api_key, "Content-Type": "application/json"}

    def submit(self, script: str) -> str:
        payload = {
            "video_inputs": [{
                "character": {
                    "type": "avatar",
                    "avatar_id": self.config.avatar_id,
                    "avatar_style": "normal"
                },
                "voice": {
                    "type": "text",
                    "input_text": script,
                    "voice_id": self.config.voice_id
                }
            }],
            "dimension": {"width": 1920, "height": 1080},
            "caption": True
        }

        with httpx.Client(timeout=30) as client:
            resp = client.post(f"{self.BASE_URL}/video/generate", json=payload, headers=self.headers)
            resp.raise_for_status()
            return resp.json()["data"]["video_id"]

    def poll(self, job_id: str) -> RenderJob:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{self.BASE_URL}/video_status.get", params={"video_id": job_id}, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()["data"]

            return RenderJob(
                id=job_id,
                content_id="",
                status=data["status"],
                video_url=data.get("video_url"),
                error=data.get("error")
            )

    def wait_for_completion(self, job_id: str, poll_interval: int = 30, timeout: int = 600) -> RenderJob:
        elapsed = 0
        while elapsed < timeout:
            job = self.poll(job_id)
            if job.status == "completed":
                return job
            elif job.status == "failed":
                raise Exception(f"Render failed: {job.error}")
            time.sleep(poll_interval)
            elapsed += poll_interval
        raise TimeoutError(f"Render timed out after {timeout}s")

    def download(self, video_url: str, content_id: str) -> Path:
        output_path = self.output_dir / f"{content_id}.mp4"
        with httpx.Client(timeout=120) as client:
            resp = client.get(video_url)
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
        return output_path
