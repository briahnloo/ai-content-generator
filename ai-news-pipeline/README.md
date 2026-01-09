# AI News Video Pipeline

Automated pipeline that transforms RSS news feeds into video content using GPT-4o for scriptwriting and HeyGen for video generation, then publishes to YouTube.

## Overview

**RSS → NLP Scoring → Script (GPT-4o) → Avatar Video (HeyGen) → YouTube (private, queued for review)**

This pipeline:
1. Ingests news articles from RSS feeds
2. **Scores content using NLP analysis to filter for engaging, sellable stories**
3. Generates 30-60 second video scripts using GPT-4o (only for high-scoring content)
4. Renders videos with AI avatars via HeyGen
5. Uploads videos to YouTube (private) for manual review before publishing

## Project Structure

```
ai-news-pipeline/
├── config/
│   ├── settings.py          # Configuration + env loading
│   ├── feeds.yaml           # RSS feed definitions
│   └── prompts/
│       └── news_script.txt  # LLM prompt template
├── core/
│   ├── models.py            # ContentItem, RenderJob dataclasses
│   └── database.py          # SQLite repository (CRUD + dedup)
├── services/
│   ├── ingestor.py          # RSS fetching + parsing
│   ├── content_scorer.py    # NLP-based content quality scoring
│   ├── script_generator.py  # OpenAI script generation
│   ├── renderer.py          # HeyGen API integration
│   └── distributor.py       # YouTube upload
├── pipeline.py              # Main orchestrator
├── cli.py                   # CLI entry point
└── requirements.txt
```

## Setup

### 1. Install Dependencies

```bash
cd ai-news-pipeline
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Download spaCy language model for NLP scoring
python -m spacy download en_core_web_sm
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your API credentials:

```env
OPENAI_API_KEY=sk-...
HEYGEN_API_KEY=...
HEYGEN_AVATAR_ID=
HEYGEN_VOICE_ID=

YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=

DATABASE_PATH=./data/pipeline.db
VIDEO_OUTPUT_DIR=./data/videos
MAX_RETRIES=3

# Content Scoring
ENABLE_SCORING=true
MIN_CONTENT_SCORE=50.0
```

### 3. Get API Keys

#### OpenAI
1. Go to [platform.openai.com](https://platform.openai.com)
2. Navigate to API Keys section
3. Create new API key

#### HeyGen
1. Sign up at [heygen.com](https://heygen.com)
2. Go to Dashboard → API
3. Get your API key
4. Select an avatar and voice to get `avatar_id` and `voice_id`

#### YouTube
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project
3. Enable YouTube Data API v3
4. Create OAuth 2.0 Client ID (Desktop app)
5. Add to `.env`: `YOUTUBE_CLIENT_ID` and `YOUTUBE_CLIENT_SECRET`
6. Run OAuth flow to get refresh token:

```bash
python cli.py auth
```

This will open a browser for OAuth consent. After authorization, copy the refresh token to your `.env` file.

## Usage

### Individual Commands

```bash
# Fetch news from RSS feeds
python cli.py ingest --limit 10

# Score content for production worthiness (NLP analysis)
python cli.py score --limit 20

# Generate scripts for high-scoring articles
python cli.py script --limit 5

# Render videos via HeyGen
python cli.py render --limit 3

# Upload to YouTube (private)
python cli.py upload --limit 5

# Check pipeline status
python cli.py status
```

### Run Full Pipeline

Process news end-to-end:

```bash
python cli.py run --ingest-limit 10 --process-limit 3
```

This will:
1. Ingest up to 10 new articles
2. Score all ingested articles (if ENABLE_SCORING=true)
3. Generate scripts for top 3 high-scoring articles
4. Render 3 videos
5. Upload 3 videos to YouTube (private)

### Publishing Videos

After reviewing videos on YouTube, make them public:

```bash
python cli.py publish VIDEO_ID
```

## Configuration

### RSS Feeds

Edit `config/feeds.yaml` to add/modify news sources:

```yaml
feeds:
  - name: "Associated Press"
    url: "https://feedx.net/rss/ap.xml"
    priority: 1

  - name: "BBC World"
    url: "https://feeds.bbci.co.uk/news/world/rss.xml"
    priority: 1

settings:
  min_content_length: 150
  max_age_hours: 24
  dedup_window_hours: 72
```

### Script Prompt

Customize the scriptwriting instructions in `config/prompts/news_script.txt`.

## Enhanced Content Scoring System

The pipeline includes a sophisticated multi-tier NLP scoring system that filters for genuinely **newsworthy, hard-hitting content** suitable for video production. This aggressive filtering ensures only sellable stories make it through.

### News Category Classification

Articles are automatically classified into 3 tiers:

**Tier 1 - Hard News (+20 bonus):**
- Politics & Government (elections, legislation, scandals, arrests)
- Conflicts & Security (war, terrorism, shootings, attacks)
- Major Disasters (natural disasters, mass casualties, evacuations)
- Economics & Markets (recession, inflation, market crashes, layoffs)
- Legal/Judicial (trials, verdicts, Supreme Court, indictments)
- International Relations (sanctions, treaties, diplomatic crises)

**Tier 2 - Soft News (+10 bonus):**
- Major Sports (championships, records, major scandals)
- Science Breakthroughs (cures, major discoveries - not curiosities)
- Technology (major launches, regulations - not reviews)
- Health (epidemics, drug approvals - not tips)

**Tier 3 - Fluff (-30 penalty):**
- Celebrity gossip & entertainment
- Animal stories (cute dogs, rescue pets)
- Lifestyle tips & how-to content
- Human interest curiosities
- Minor sports injuries
- Soft science ("study finds...")

### Scoring Algorithm

**Base Components (50% weight):**
1. Headline Quality (15%)
2. Entity Prominence (15%) - World leaders, major institutions
3. Sentiment Intensity (10%) - Emotional engagement
4. Recency (10%)
5. Content Richness (10%)

**Enhanced Components (50% weight):**
6. **News Category Bonus/Penalty** - Based on tier classification
7. **Impact & Scale (0-20)** - Global/national reach, mass casualties, economic scope
8. **Consequence (0-15)** - Policy implications, urgency, irreversibility
9. **Authority (0-10)** - Government sources, official statements
10. **Fluff Penalty (0-40)** - Aggressively penalizes non-news content

### Fluff Detection

The system actively penalizes:
- **Animal fluff** (dogs, cats) - unless attack/death context
- **Lifestyle content** (tips, recipes, fashion) - heavy penalty
- **Entertainment** (celebrities, movies) - unless crime/scandal
- **Soft science** (curiosities, minor studies) - unless breakthrough
- **Sports injuries** (ankle sprains, rehab) - moderate penalty

**Examples:**
- ❌ "Chloe Kim injures shoulder" → **Score: ~25** (sports injury + fluff)
- ❌ "Dogs learn toy names" → **Score: ~20** (animal fluff + soft science)
- ✅ "Minnesota shooting videos challenge narrative" → **Score: ~75** (conflict + authority)
- ✅ "Fatal ICE shooting sparks jurisdiction clash" → **Score: ~80** (conflict + policy)

### Configuration

```env
ENABLE_SCORING=true                    # Enable/disable scoring filter
MIN_CONTENT_SCORE=60.0                 # Threshold (0-100), default 60
REQUIRE_HARD_NEWS=false                # If true, reject all non-Tier 1
FLUFF_PENALTY_MULTIPLIER=1.5          # Harshness (1.0-2.0), 1.5 = reasonably aggressive
```

### How It Works

- Articles scoring **≥ 60** → Status: `SCORED` (proceed to script generation)
- Articles scoring **< 60** → Status: `SKIPPED` (filtered out)
- Hard news prioritized over soft news over fluff
- When scoring disabled, all ingested articles proceed

### Expected Filtering Rate

With default settings (60.0 threshold, 1.5 penalty):
- **~70-80% rejection rate** for general news feeds
- Majority of rejected: lifestyle, entertainment, minor sports, animal stories
- Majority accepted: conflicts, policy changes, major disasters, elections

### Free NLP Tools Used

- **spaCy** (`en_core_web_sm`): Named entity recognition (persons, orgs, places)
- **TextBlob**: Sentiment analysis (polarity and subjectivity)
- **Advanced keyword taxonomy**: 200+ categorized keywords for news classification
- **Pattern matching**: Regex for mass casualties, urgency, official sources

## Pipeline Flow

```
┌──────────────┐
│  RSS Feeds   │
└──────┬───────┘
       │
       ▼
┌──────────────┐      ┌──────────────┐
│   Ingestor   │─────▶│   Database   │
└──────┬───────┘      └──────────────┘
       │                      │
       ▼                      │
┌──────────────┐             │
│ Enhanced NLP │◀────────────┘
│Content Scorer│
│ • Category   │
│ • Impact     │
│ • Fluff Det. │
└──────┬───────┘
       │
       ├─ Score ≥ 60 ─▶ SCORED (Hard News Priority)
       │
       └─ Score < 60 ─▶ SKIPPED (Fluff Rejected)
       │
       ▼
┌──────────────┐
│  GPT-4o      │
│  Scripting   │
│ (Top Scored) │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   HeyGen     │
│  Rendering   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   YouTube    │
│  (Private)   │
└──────────────┘
```

## Database

SQLite database stores content through all stages:
- **ingested**: Fetched from RSS
- **scored**: Passed content quality threshold (score ≥ MIN_CONTENT_SCORE)
- **skipped**: Failed quality threshold (score < MIN_CONTENT_SCORE)
- **scripted**: Script generated
- **rendering**: Video in progress
- **rendered**: Video ready
- **uploaded**: On YouTube (private)
- **published**: Live on YouTube

Additional fields stored:
- `content_score`: Overall quality score (0-100)
- `score_breakdown`: JSON with individual dimension scores

## Error Handling

- Failed items are marked with status `failed` and error messages
- Retry counts tracked per item
- Use `python cli.py status` to view pipeline state

## Development

Run tests (if applicable):
```bash
pytest tests/
```

## License

MIT
