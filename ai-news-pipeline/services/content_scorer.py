"""
Content scoring system to evaluate article quality and viewer engagement potential.
Uses free NLP tools and heuristics to determine if content is worth producing.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Optional
from textblob import TextBlob
import spacy
from collections import Counter

# Load spaCy model (download with: python -m spacy download en_core_web_sm)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    # Fallback if model not installed
    nlp = None

class ContentScorer:
    """
    Scores content based on multiple factors to determine video production worthiness.

    Scoring dimensions:
    1. Headline Quality (0-20): Click-worthiness, clarity, emotional appeal
    2. Entity Prominence (0-20): Notable people, places, organizations
    3. Sentiment Intensity (0-15): Emotional engagement potential
    4. Topic Relevance (0-20): Newsworthy keywords and trending topics
    5. Recency Bonus (0-10): Time-sensitive content boost
    6. Content Richness (0-15): Sufficient detail for video production

    Total: 0-100 scale
    """

    # High-value entities that boost scores
    NOTABLE_PERSONS = {
        'trump', 'biden', 'harris', 'putin', 'xi', 'modi', 'macron', 'scholz',
        'netanyahu', 'zelenskyy', 'erdogan', 'lula', 'sunak', 'trudeau'
    }

    NOTABLE_ORGS = {
        'un', 'nato', 'eu', 'who', 'fda', 'fed', 'white house', 'pentagon',
        'congress', 'senate', 'supreme court', 'parliament', 'world bank', 'imf'
    }

    NOTABLE_PLACES = {
        'us', 'usa', 'china', 'russia', 'ukraine', 'israel', 'gaza', 'iran',
        'north korea', 'taiwan', 'syria', 'afghanistan', 'iraq'
    }

    # High-impact keywords for news
    TRENDING_KEYWORDS = {
        'breaking', 'exclusive', 'crisis', 'emergency', 'war', 'conflict',
        'scandal', 'investigation', 'breakthrough', 'historic', 'unprecedented',
        'disaster', 'attack', 'protest', 'revolution', 'election', 'vote',
        'economy', 'inflation', 'recession', 'market crash', 'pandemic',
        'climate', 'ai', 'technology', 'crypto', 'bitcoin'
    }

    # Click-worthy headline patterns
    ENGAGING_PATTERNS = [
        r'\b(shocking|stunning|incredible|unbelievable|devastating)\b',
        r'\b(revealed|exposed|discovered|uncovered)\b',
        r'\bwhy\s+\w+',  # "Why X happened"
        r'\bhow\s+\w+',  # "How X works"
        r'\d+\s+(reasons|ways|things|facts)',  # Listicles
        r'(?:you|your)\b',  # Direct address
    ]

    def __init__(self,
                 headline_weight: float = 0.20,
                 entity_weight: float = 0.20,
                 sentiment_weight: float = 0.15,
                 topic_weight: float = 0.20,
                 recency_weight: float = 0.10,
                 richness_weight: float = 0.15):
        """
        Initialize scorer with configurable weights.

        Args:
            headline_weight: Weight for headline quality (default 0.20)
            entity_weight: Weight for entity prominence (default 0.20)
            sentiment_weight: Weight for sentiment intensity (default 0.15)
            topic_weight: Weight for topic relevance (default 0.20)
            recency_weight: Weight for recency bonus (default 0.10)
            richness_weight: Weight for content richness (default 0.15)
        """
        self.weights = {
            'headline': headline_weight,
            'entities': entity_weight,
            'sentiment': sentiment_weight,
            'topic': topic_weight,
            'recency': recency_weight,
            'richness': richness_weight
        }

    def score(self, title: str, content: str, published_at: Optional[datetime] = None) -> tuple[float, Dict[str, float]]:
        """
        Score content and return overall score plus breakdown.

        Args:
            title: Article headline
            content: Article body text
            published_at: Publication timestamp (optional)

        Returns:
            Tuple of (overall_score, score_breakdown_dict)
        """
        breakdown = {
            'headline': self._score_headline(title),
            'entities': self._score_entities(title, content),
            'sentiment': self._score_sentiment(title, content),
            'topic': self._score_topic_relevance(title, content),
            'recency': self._score_recency(published_at),
            'richness': self._score_content_richness(content)
        }

        # Calculate weighted overall score
        overall = sum(breakdown[key] * self.weights[key] for key in breakdown.keys())

        # Normalize to 0-100 scale
        max_possible = sum(self.weights.values()) * 100
        overall = (overall / max_possible) * 100

        return round(overall, 2), breakdown

    def _score_headline(self, title: str) -> float:
        """
        Score headline quality (0-20 points).

        Factors:
        - Length (optimal 40-100 chars)
        - Emotional words
        - Click-worthy patterns
        - Specificity (numbers, proper nouns)
        """
        score = 0.0
        title_lower = title.lower()

        # Length optimization (5 points)
        length = len(title)
        if 40 <= length <= 100:
            score += 5
        elif 30 <= length < 40 or 100 < length <= 120:
            score += 3
        else:
            score += 1

        # Engaging patterns (8 points)
        pattern_matches = sum(1 for pattern in self.ENGAGING_PATTERNS if re.search(pattern, title_lower, re.IGNORECASE))
        score += min(pattern_matches * 2, 8)

        # Numbers present (specificity) (3 points)
        if re.search(r'\d+', title):
            score += 3

        # Proper nouns/capitalization (suggests specificity) (4 points)
        capital_words = sum(1 for word in title.split() if word and word[0].isupper())
        if capital_words >= 2:
            score += 4
        elif capital_words == 1:
            score += 2

        return min(score, 20)

    def _score_entities(self, title: str, content: str) -> float:
        """
        Score based on prominent entities (0-20 points).

        Uses spaCy for entity extraction and checks against notable entity lists.
        """
        score = 0.0
        text = f"{title} {content[:1000]}".lower()

        # Extract entities with spaCy if available
        entities = {'persons': set(), 'orgs': set(), 'places': set()}
        if nlp:
            doc = nlp(text[:2000])  # Limit for performance
            for ent in doc.ents:
                if ent.label_ == 'PERSON':
                    entities['persons'].add(ent.text.lower())
                elif ent.label_ in ('ORG', 'NORP'):
                    entities['orgs'].add(ent.text.lower())
                elif ent.label_ in ('GPE', 'LOC'):
                    entities['places'].add(ent.text.lower())

        # Score notable persons (8 points max)
        notable_persons_found = sum(1 for person in entities['persons']
                                     if any(notable in person for notable in self.NOTABLE_PERSONS))
        score += min(notable_persons_found * 4, 8)

        # Score notable organizations (6 points max)
        notable_orgs_found = sum(1 for org in entities['orgs']
                                  if any(notable in org for notable in self.NOTABLE_ORGS))
        score += min(notable_orgs_found * 3, 6)

        # Score notable places (6 points max)
        notable_places_found = sum(1 for place in entities['places']
                                    if any(notable in place for notable in self.NOTABLE_PLACES))
        score += min(notable_places_found * 3, 6)

        return min(score, 20)

    def _score_sentiment(self, title: str, content: str) -> float:
        """
        Score sentiment intensity (0-15 points).

        Higher absolute sentiment = more emotional = more engaging.
        Uses TextBlob for sentiment analysis.
        """
        try:
            title_blob = TextBlob(title)
            content_blob = TextBlob(content[:500])

            # Get polarity (-1 to 1)
            title_polarity = abs(title_blob.sentiment.polarity)
            content_polarity = abs(content_blob.sentiment.polarity)

            # Get subjectivity (0 to 1) - more subjective = more opinionated
            title_subjectivity = title_blob.sentiment.subjectivity
            content_subjectivity = content_blob.sentiment.subjectivity

            # Combine scores (title weighted more)
            polarity_score = (title_polarity * 0.6 + content_polarity * 0.4) * 10
            subjectivity_score = (title_subjectivity * 0.4 + content_subjectivity * 0.6) * 5

            return min(polarity_score + subjectivity_score, 15)
        except:
            return 5.0  # Default moderate score if analysis fails

    def _score_topic_relevance(self, title: str, content: str) -> float:
        """
        Score topic relevance and newsworthiness (0-20 points).

        Checks for trending keywords and high-impact topics.
        """
        score = 0.0
        text = f"{title} {content}".lower()

        # Count trending keyword matches (15 points max)
        keyword_matches = sum(1 for keyword in self.TRENDING_KEYWORDS if keyword in text)
        score += min(keyword_matches * 3, 15)

        # Bonus for appearing in title (5 points max)
        title_keywords = sum(1 for keyword in self.TRENDING_KEYWORDS if keyword in title.lower())
        score += min(title_keywords * 2.5, 5)

        return min(score, 20)

    def _score_recency(self, published_at: Optional[datetime]) -> float:
        """
        Score based on recency (0-10 points).

        Newer content gets higher scores. Decays over 24 hours.
        """
        if not published_at:
            return 5.0  # Default moderate score

        now = datetime.utcnow()
        if published_at.tzinfo:
            published_at = published_at.replace(tzinfo=None)

        age_hours = (now - published_at).total_seconds() / 3600

        # Full points for < 2 hours
        if age_hours < 2:
            return 10.0
        # Linear decay over 24 hours
        elif age_hours < 24:
            return 10.0 - (age_hours / 24) * 5
        # Half points for 24-48 hours
        elif age_hours < 48:
            return 5.0 - ((age_hours - 24) / 24) * 3
        # Minimum for older content
        else:
            return 2.0

    def _score_content_richness(self, content: str) -> float:
        """
        Score content richness and substance (0-15 points).

        Evaluates if there's enough material for a good video script.
        """
        score = 0.0

        # Length check (6 points)
        length = len(content)
        if length >= 1000:
            score += 6
        elif length >= 500:
            score += 4
        elif length >= 200:
            score += 2

        # Sentence variety (5 points)
        sentences = content.count('.') + content.count('!') + content.count('?')
        if sentences >= 5:
            score += 5
        elif sentences >= 3:
            score += 3
        elif sentences >= 1:
            score += 1

        # Quote presence (suggests depth) (4 points)
        quotes = content.count('"') + content.count("'")
        if quotes >= 4:  # At least 2 quoted statements
            score += 4
        elif quotes >= 2:
            score += 2

        return min(score, 15)

    def is_worthy(self, score: float, threshold: float = 50.0) -> bool:
        """
        Determine if content is worthy of video production.

        Args:
            score: Overall content score (0-100)
            threshold: Minimum score for worthiness (default 50.0)

        Returns:
            True if score meets threshold
        """
        return score >= threshold
