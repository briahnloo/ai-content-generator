import click
from config.settings import Settings
from pipeline import Pipeline

@click.group()
def cli():
    """AI News Video Pipeline"""
    pass

@cli.command()
@click.option("--limit", default=10, help="Max items to ingest")
def ingest(limit):
    """Fetch new content from RSS feeds"""
    pipeline = Pipeline(Settings.from_env())
    items = pipeline.ingest(limit)
    click.echo(f"Ingested {len(items)} items")

@cli.command()
@click.option("--limit", default=20, help="Max items to score")
def score(limit):
    """Score ingested content for production worthiness"""
    pipeline = Pipeline(Settings.from_env())
    items = pipeline.score_content(limit)
    click.echo(f"Scored {len(items)} items (passed threshold)")

@cli.command()
@click.option("--limit", default=5, help="Max scripts to generate")
def script(limit):
    """Generate scripts for scored/ingested content"""
    pipeline = Pipeline(Settings.from_env())
    items = pipeline.generate_scripts(limit)
    click.echo(f"Generated {len(items)} scripts")

@cli.command()
@click.option("--limit", default=3, help="Max videos to render")
def render(limit):
    """Render videos via HeyGen"""
    pipeline = Pipeline(Settings.from_env())
    items = pipeline.render_videos(limit)
    click.echo(f"Rendered {len(items)} videos")

@cli.command()
@click.option("--limit", default=5, help="Max videos to upload")
def upload(limit):
    """Upload rendered videos to YouTube (private)"""
    pipeline = Pipeline(Settings.from_env())
    items = pipeline.upload_videos(limit)
    click.echo(f"Uploaded {len(items)} videos")

@cli.command()
@click.option("--ingest-limit", default=10)
@click.option("--process-limit", default=3)
def run(ingest_limit, process_limit):
    """Run full pipeline: ingest → score → script → render → upload"""
    pipeline = Pipeline(Settings.from_env())
    pipeline.run_full(ingest_limit, process_limit)

@cli.command()
@click.argument("video_id")
def publish(video_id):
    """Set a YouTube video to public"""
    pipeline = Pipeline(Settings.from_env())
    pipeline.distributor.set_public(video_id)
    click.echo(f"Published: https://youtube.com/watch?v={video_id}")

@cli.command()
def auth():
    """Run YouTube OAuth flow to get refresh token"""
    from google_auth_oauthlib.flow import InstalledAppFlow
    import json

    settings = Settings.from_env()

    client_config = {
        "installed": {
            "client_id": settings.youtube_client_id,
            "client_secret": settings.youtube_client_secret,
            "redirect_uris": ["http://localhost:8080"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }

    flow = InstalledAppFlow.from_client_config(
        client_config,
        scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )
    credentials = flow.run_local_server(port=8080)

    click.echo(f"\nYOUTUBE_REFRESH_TOKEN={credentials.refresh_token}")
    click.echo("\nAdd this to your .env file")

@cli.command()
def status():
    """Show pipeline status"""
    from core.database import Database
    from core.models import Status

    settings = Settings.from_env()
    db = Database(settings.database_path)

    for s in Status:
        count = len(db.get_by_status(s, limit=1000))
        if count > 0:
            click.echo(f"{s.value}: {count}")

if __name__ == "__main__":
    cli()
