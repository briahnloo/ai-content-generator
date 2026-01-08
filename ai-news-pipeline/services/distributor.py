from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dataclasses import dataclass

@dataclass
class YouTubeCredentials:
    client_id: str
    client_secret: str
    refresh_token: str

class YouTubeDistributor:
    def __init__(self, creds: YouTubeCredentials):
        credentials = Credentials(
            token=None,
            refresh_token=creds.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=creds.client_id,
            client_secret=creds.client_secret
        )
        credentials.refresh(Request())
        self.youtube = build("youtube", "v3", credentials=credentials)

    def upload(self, video_path: Path, title: str, description: str, tags: list[str]) -> str:
        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags,
                "categoryId": "25"  # News & Politics
            },
            "status": {
                "privacyStatus": "private",
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)
        request = self.youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()
        return response["id"]

    def set_public(self, video_id: str):
        self.youtube.videos().update(
            part="status",
            body={"id": video_id, "status": {"privacyStatus": "public"}}
        ).execute()
