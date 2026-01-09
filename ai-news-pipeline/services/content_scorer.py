"""
Enhanced content scoring system with news category classification and fluff detection.
Filters for genuinely newsworthy content suitable for video production.
Uses free NLP tools and sophisticated heuristics.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from textblob import TextBlob
import spacy
from enum import Enum

# Load spaCy model (download with: python -m spacy download en_core_web_sm)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = None

class NewsTier(Enum):
    """News category tiers for content classification"""
    HARD_NEWS = 1      # Politics, conflict, economics, disasters
    SOFT_NEWS = 2      # Major sports, tech, science breakthroughs
    FLUFF = 3          # Entertainment, lifestyle, curiosities

class ContentScorer:
    """
    Advanced content scorer with category classification and impact assessment.

    Scoring system:
    1. Base scoring (headline, entities, sentiment, recency, richness)
    2. News category bonus/penalty (Tier 1: +20, Tier 2: +10, Tier 3: -30)
    3. Impact & scale scoring (0-20)
    4. Consequence scoring (0-15)
    5. Authority scoring (0-10)
    6. Fluff penalty (-5 to -40)

    Final: 0-100 scale (higher threshold recommended: 60+)
    """

    # === TIER 1: HARD NEWS KEYWORDS ===

    CONFLICT_KEYWORDS = {
        'war', 'invasion', 'bombing', 'attack', 'attacked', 'attacks', 'shooting',
        'shot', 'terrorism', 'terrorist', 'missile', 'strike', 'airstrike',
        'combat', 'battle', 'assault', 'raid', 'hostage', 'kidnapped'
    }

    CRISIS_KEYWORDS = {
        'emergency', 'disaster', 'collapse', 'crashed', 'crash', 'crisis',
        'catastrophe', 'evacuation', 'evacuated', 'outbreak', 'epidemic',
        'pandemic', 'hurricane', 'earthquake', 'flood', 'wildfire', 'tornado'
    }

    DEATH_KEYWORDS = {
        'killed', 'dead', 'death', 'deaths', 'died', 'fatal', 'fatalities',
        'casualties', 'victims', 'massacre', 'murder', 'murdered', 'assassination'
    }

    GOVERNMENT_ACTION_KEYWORDS = {
        'sanctions', 'sanctioned', 'impeachment', 'impeached', 'resignation',
        'resigned', 'coup', 'arrested', 'charges', 'indicted', 'indictment',
        'trial', 'verdict', 'conviction', 'sentenced', 'plea', 'guilty',
        'jury', 'court', 'judge', 'prosecutor', 'lawsuit', 'sued', 'acquitted'
    }

    # === TIER 1/2: IMPORTANT KEYWORDS ===

    ECONOMICS_KEYWORDS = {
        'inflation', 'recession', 'unemployment', 'gdp', 'interest rates',
        'federal reserve', 'stock market', 'dow', 'nasdaq', 'bankruptcy',
        'layoffs', 'jobs report', 'trade war', 'tariff', 'tariffs'
    }

    POLICY_KEYWORDS = {
        'legislation', 'bill', 'regulation', 'executive order', 'ruling',
        'supreme court', 'law', 'policy', 'reform', 'ban', 'banned'
    }

    ELECTION_KEYWORDS = {
        'election', 'vote', 'voting', 'primary', 'campaign', 'poll',
        'debate', 'candidate', 'president', 'senator', 'governor'
    }

    INTERNATIONAL_KEYWORDS = {
        'treaty', 'summit', 'alliance', 'nato', 'un', 'trade deal',
        'diplomatic', 'ambassador', 'foreign minister', 'g7', 'g20',
        'coalition', 'smuggle', 'separatist', 'rebels', 'militants'
    }

    # === TIER 3: FLUFF INDICATORS ===

    ANIMAL_FLUFF = {
        'dog', 'dogs', 'cat', 'cats', 'puppy', 'puppies', 'kitten', 'kittens',
        'pet', 'pets', 'cute', 'adorable', 'rescue dog', 'service dog'
    }

    LIFESTYLE_FLUFF = {
        'tips', 'how to', 'recipe', 'recipes', 'fashion', 'beauty', 'style',
        'workout', 'exercise', 'diet', 'lose weight', 'best', 'top 10'
    }

    ENTERTAINMENT_FLUFF = {
        'celebrity', 'celebrities', 'actor', 'actress', 'singer', 'musician',
        'movie', 'film', 'show', 'series', 'album', 'concert', 'performance'
    }

    SOFT_SCIENCE_FLUFF = {
        'study finds', 'research shows', 'scientists say', 'study says',
        'according to a study', 'new study', 'researchers found'
    }

    SPORTS_MINOR = {
        'injured', 'injury', 'injuries', 'sprained', 'ankle', 'shoulder',
        'rehab', 'practices', 'training', 'workout', 'signs contract'
    }

    # === IMPACT & AUTHORITY INDICATORS ===

    GLOBAL_IMPACT = {
        'world', 'global', 'international', 'countries', 'nations',
        'worldwide', 'planet', 'earth', 'humanity'
    }

    NATIONAL_IMPACT = {
        'national', 'nationwide', 'federal', 'congress', 'senate',
        'house', 'president', 'states', 'america', 'american'
    }

    MASS_SCALE_PATTERNS = [
        r'\d+\s*(?:million|billion|thousand)\s+(?:people|affected|dead|evacuated|cases)',
        r'death toll',
        r'\d+\s+(?:killed|dead|injured|affected)',
        r'mass\s+(?:shooting|casualty|evacuation)'
    ]

    CONSEQUENCE_KEYWORDS = {
        'law', 'regulation', 'ban', 'sanctions', 'legislation', 'policy',
        'rule', 'order', 'mandate', 'requirement', 'deadline', 'final',
        'historic', 'unprecedented', 'first time', 'landmark'
    }

    AUTHORITY_SOURCES = {
        'government', 'official', 'officials', 'white house', 'pentagon',
        'state department', 'department of', 'agency', 'fda', 'cdc',
        'federal reserve', 'fed', 'central bank', 'minister', 'secretary',
        'police', 'sheriff', 'attorney', 'prosecutor', 'investigators',
        'authorities', 'spokesman', 'spokesperson', 'statement', 'announced'
    }

    # === NOTABLE ENTITIES ===

    NOTABLE_PERSONS = {
        'trump', 'biden', 'harris', 'putin', 'xi jinping', 'modi', 'macron',
        'scholz', 'netanyahu', 'zelenskyy', 'erdogan', 'lula', 'sunak',
        'trudeau', 'obama', 'pence', 'pelosi', 'mcconnell', 'pope'
    }

    NOTABLE_ORGS = {
        'un', 'nato', 'eu', 'who', 'fda', 'fed', 'federal reserve',
        'white house', 'pentagon', 'congress', 'senate', 'supreme court',
        'parliament', 'world bank', 'imf', 'world health organization'
    }

    NOTABLE_PLACES = {
        'us', 'usa', 'united states', 'china', 'russia', 'ukraine', 'israel',
        'gaza', 'iran', 'north korea', 'taiwan', 'syria', 'afghanistan',
        'iraq', 'yemen', 'pakistan', 'india'
    }

    def __init__(self,
                 require_hard_news: bool = False,
                 fluff_penalty_multiplier: float = 1.5):
        """
        Initialize enhanced content scorer.

        Args:
            require_hard_news: If True, reject all non-Tier 1 news
            fluff_penalty_multiplier: How harsh to penalize fluff (1.0-2.0)
        """
        self.require_hard_news = require_hard_news
        self.fluff_penalty_multiplier = fluff_penalty_multiplier

    def score(self, title: str, content: str, published_at: Optional[datetime] = None) -> Tuple[float, Dict[str, float]]:
        """
        Score content with enhanced news classification and impact assessment.

        Args:
            title: Article headline
            content: Article body text
            published_at: Publication timestamp (optional)

        Returns:
            Tuple of (overall_score, detailed_breakdown_dict)
        """
        text_combined = f"{title} {content}".lower()

        # Base scoring components
        base_breakdown = {
            'headline_quality': self._score_headline(title),
            'entity_prominence': self._score_entities(title, content),
            'sentiment_intensity': self._score_sentiment(title, content),
            'recency': self._score_recency(published_at),
            'content_richness': self._score_content_richness(content)
        }

        # Enhanced scoring components
        news_tier = self._classify_news_category(text_combined)
        category_bonus = self._get_category_bonus(news_tier)
        impact_score = self._score_impact_scale(text_combined)
        consequence_score = self._score_consequence(text_combined)
        authority_score = self._score_authority(text_combined)

        # Only apply fluff penalty to FLUFF tier content, not hard news
        if news_tier == NewsTier.FLUFF:
            fluff_penalty = self._detect_fluff_penalty(text_combined, title.lower())
        else:
            fluff_penalty = 0.0

        # Combine base score (normalize to ~40 point contribution)
        # Max possible: 20+20+15+10+15 = 80, scale to ~40
        base_score = (
            base_breakdown['headline_quality'] * 0.5 +      # 0-20 → 0-10
            base_breakdown['entity_prominence'] * 0.5 +     # 0-20 → 0-10
            base_breakdown['sentiment_intensity'] * 0.67 +  # 0-15 → 0-10
            base_breakdown['recency'] * 0.5 +               # 0-10 → 0-5
            base_breakdown['content_richness'] * 0.33       # 0-15 → 0-5
        )  # Total: 0-40

        # Add enhanced components (~60 point contribution)
        enhanced_score = (
            category_bonus +           # -30 to +20
            impact_score +             # 0-20
            consequence_score +        # 0-15
            authority_score -          # 0-10
            (fluff_penalty * self.fluff_penalty_multiplier)  # 0 to -60
        )

        # Calculate final score
        final_score = base_score + enhanced_score
        final_score = max(0, min(100, final_score))  # Clamp to 0-100

        # Build detailed breakdown
        breakdown = {
            **base_breakdown,
            'news_category': news_tier.name,
            'category_bonus': category_bonus,
            'impact_scale': impact_score,
            'consequence': consequence_score,
            'authority': authority_score,
            'fluff_penalty': -fluff_penalty * self.fluff_penalty_multiplier,
            'base_score': round(base_score, 2),
            'enhanced_score': round(enhanced_score, 2)
        }

        return round(final_score, 2), breakdown

    def _classify_news_category(self, text: str) -> NewsTier:
        """
        Classify content into news tiers: Hard News, Soft News, or Fluff.

        Args:
            text: Combined title + content (lowercase)

        Returns:
            NewsTier enum value
        """
        # Check for hard news indicators (Tier 1)
        hard_news_score = 0

        # Conflict/violence
        hard_news_score += sum(3 for kw in self.CONFLICT_KEYWORDS if kw in text)

        # Crisis/disaster
        hard_news_score += sum(3 for kw in self.CRISIS_KEYWORDS if kw in text)

        # Death/casualties
        hard_news_score += sum(4 for kw in self.DEATH_KEYWORDS if kw in text)

        # Government action
        hard_news_score += sum(3 for kw in self.GOVERNMENT_ACTION_KEYWORDS if kw in text)

        # Economics (major)
        hard_news_score += sum(2 for kw in self.ECONOMICS_KEYWORDS if kw in text)

        # Policy/legal
        hard_news_score += sum(2 for kw in self.POLICY_KEYWORDS if kw in text)

        # Elections
        hard_news_score += sum(2 for kw in self.ELECTION_KEYWORDS if kw in text)

        # International relations
        hard_news_score += sum(2 for kw in self.INTERNATIONAL_KEYWORDS if kw in text)

        # Check for fluff indicators (Tier 3)
        fluff_score = 0

        fluff_score += sum(2 for kw in self.ANIMAL_FLUFF if kw in text)
        fluff_score += sum(2 for kw in self.LIFESTYLE_FLUFF if kw in text)
        fluff_score += sum(2 for kw in self.ENTERTAINMENT_FLUFF if kw in text)
        fluff_score += sum(3 for kw in self.SOFT_SCIENCE_FLUFF if kw in text)
        fluff_score += sum(2 for kw in self.SPORTS_MINOR if kw in text)

        # Decision logic (more permissive thresholds)
        if hard_news_score >= 4:  # Lowered from 6
            return NewsTier.HARD_NEWS
        elif fluff_score >= 6:  # Raised from 4 to be less aggressive
            return NewsTier.FLUFF
        elif hard_news_score >= 2:  # Lowered from 3
            return NewsTier.SOFT_NEWS
        elif fluff_score >= 3:  # Raised from 2
            return NewsTier.FLUFF
        else:
            # Default to soft news for ambiguous cases
            return NewsTier.SOFT_NEWS

    def _get_category_bonus(self, tier: NewsTier) -> float:
        """Get bonus/penalty based on news tier."""
        if tier == NewsTier.HARD_NEWS:
            return 30.0  # Increased from 20 to ensure hard news passes
        elif tier == NewsTier.SOFT_NEWS:
            return 15.0  # Increased from 10
        else:  # FLUFF
            return -30.0

    def _score_impact_scale(self, text: str) -> float:
        """
        Score based on scope and scale of impact (0-20 points).

        Evaluates: global/national reach, mass casualties, economic scale
        """
        score = 0.0

        # Global impact indicators (8 points max)
        global_count = sum(1 for kw in self.GLOBAL_IMPACT if kw in text)
        score += min(global_count * 4, 8)

        # National impact indicators (6 points max)
        national_count = sum(1 for kw in self.NATIONAL_IMPACT if kw in text)
        score += min(national_count * 3, 6)

        # Mass scale patterns (6 points max)
        mass_scale_matches = sum(1 for pattern in self.MASS_SCALE_PATTERNS
                                 if re.search(pattern, text, re.IGNORECASE))
        score += min(mass_scale_matches * 3, 6)

        return min(score, 20.0)

    def _score_consequence(self, text: str) -> float:
        """
        Score based on policy/economic/legal consequences (0-15 points).

        Evaluates: irreversibility, policy implications, urgency
        """
        score = 0.0

        # Consequence keywords (10 points max)
        consequence_count = sum(1 for kw in self.CONSEQUENCE_KEYWORDS if kw in text)
        score += min(consequence_count * 2, 10)

        # Urgency indicators (5 points max)
        urgency_patterns = [
            r'\bbreaking\b', r'\bdeveloping\b', r'\bongoing\b',
            r'\bemergency\b', r'\bimmediate\b', r'\burgent\b'
        ]
        urgency_matches = sum(1 for pattern in urgency_patterns
                              if re.search(pattern, text, re.IGNORECASE))
        score += min(urgency_matches * 2.5, 5)

        return min(score, 15.0)

    def _score_authority(self, text: str) -> float:
        """
        Score based on official sources and authority (0-10 points).

        Evaluates: government sources, official statements, expert attribution
        """
        score = 0.0

        # Authority source mentions (10 points max)
        authority_count = sum(1 for kw in self.AUTHORITY_SOURCES if kw in text)
        score += min(authority_count * 2.5, 10)

        return min(score, 10.0)

    def _detect_fluff_penalty(self, text: str, title: str) -> float:
        """
        Detect fluff indicators and return penalty amount (0-40 points).

        Higher penalty for lifestyle/entertainment content.
        """
        penalty = 0.0

        # Animal fluff (unless serious context)
        animal_matches = sum(1 for kw in self.ANIMAL_FLUFF if kw in text)
        if animal_matches > 0:
            # Check for serious context (attack, death, disaster)
            serious_context = any(kw in text for kw in ['attack', 'killed', 'dead', 'mauled', 'disaster'])
            if not serious_context:
                penalty += min(animal_matches * 8, 20)

        # Lifestyle content (heavy penalty)
        lifestyle_matches = sum(1 for kw in self.LIFESTYLE_FLUFF if kw in text)
        penalty += min(lifestyle_matches * 10, 25)

        # Entertainment content
        entertainment_matches = sum(1 for kw in self.ENTERTAINMENT_FLUFF if kw in text)
        if entertainment_matches > 0:
            # Check for serious context (arrested, died, scandal)
            serious_context = any(kw in text for kw in ['arrested', 'died', 'dead', 'scandal', 'charged', 'trial'])
            if not serious_context:
                penalty += min(entertainment_matches * 7, 20)

        # Soft science/curiosity (moderate penalty)
        soft_science_matches = sum(1 for kw in self.SOFT_SCIENCE_FLUFF if kw in text)
        if soft_science_matches > 0:
            # Check for major breakthrough context
            major_context = any(kw in text for kw in ['breakthrough', 'cure', 'cancer', 'treatment', 'vaccine'])
            if not major_context:
                penalty += min(soft_science_matches * 6, 15)

        # Minor sports (moderate penalty)
        sports_minor_matches = sum(1 for kw in self.SPORTS_MINOR if kw in text)
        if sports_minor_matches > 0:
            # Sports injuries are almost always low-value
            penalty += min(sports_minor_matches * 8, 20)

        return min(penalty, 40.0)

    def _score_headline(self, title: str) -> float:
        """Score headline quality (0-20 points)."""
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
        patterns = [
            r'\b(shocking|stunning|incredible|unbelievable|devastating)\b',
            r'\b(revealed|exposed|discovered|uncovered)\b',
            r'\bwhy\s+\w+', r'\bhow\s+\w+',
            r'\d+\s+(reasons|ways|things|facts)',
        ]
        pattern_matches = sum(1 for p in patterns if re.search(p, title_lower, re.IGNORECASE))
        score += min(pattern_matches * 2, 8)

        # Numbers (specificity) (3 points)
        if re.search(r'\d+', title):
            score += 3

        # Proper nouns (4 points)
        capital_words = sum(1 for word in title.split() if word and word[0].isupper())
        if capital_words >= 2:
            score += 4
        elif capital_words == 1:
            score += 2

        return min(score, 20.0)

    def _score_entities(self, title: str, content: str) -> float:
        """Score prominent entities (0-20 points)."""
        score = 0.0
        text = f"{title} {content[:1000]}".lower()

        # Extract entities with spaCy if available
        entities = {'persons': set(), 'orgs': set(), 'places': set()}
        if nlp:
            doc = nlp(text[:2000])
            for ent in doc.ents:
                if ent.label_ == 'PERSON':
                    entities['persons'].add(ent.text.lower())
                elif ent.label_ in ('ORG', 'NORP'):
                    entities['orgs'].add(ent.text.lower())
                elif ent.label_ in ('GPE', 'LOC'):
                    entities['places'].add(ent.text.lower())

        # Notable persons (8 points max)
        notable_persons = sum(1 for p in entities['persons']
                              if any(notable in p for notable in self.NOTABLE_PERSONS))
        score += min(notable_persons * 4, 8)

        # Notable orgs (6 points max)
        notable_orgs = sum(1 for o in entities['orgs']
                           if any(notable in o for notable in self.NOTABLE_ORGS))
        score += min(notable_orgs * 3, 6)

        # Notable places (6 points max)
        notable_places = sum(1 for p in entities['places']
                             if any(notable in p for notable in self.NOTABLE_PLACES))
        score += min(notable_places * 3, 6)

        return min(score, 20.0)

    def _score_sentiment(self, title: str, content: str) -> float:
        """Score sentiment intensity (0-15 points)."""
        try:
            title_blob = TextBlob(title)
            content_blob = TextBlob(content[:500])

            title_polarity = abs(title_blob.sentiment.polarity)
            content_polarity = abs(content_blob.sentiment.polarity)

            title_subjectivity = title_blob.sentiment.subjectivity
            content_subjectivity = content_blob.sentiment.subjectivity

            polarity_score = (title_polarity * 0.6 + content_polarity * 0.4) * 10
            subjectivity_score = (title_subjectivity * 0.4 + content_subjectivity * 0.6) * 5

            return min(polarity_score + subjectivity_score, 15.0)
        except:
            return 5.0

    def _score_recency(self, published_at: Optional[datetime]) -> float:
        """Score recency (0-10 points)."""
        if not published_at:
            return 5.0

        now = datetime.utcnow()
        if published_at.tzinfo:
            published_at = published_at.replace(tzinfo=None)

        age_hours = (now - published_at).total_seconds() / 3600

        if age_hours < 2:
            return 10.0
        elif age_hours < 24:
            return 10.0 - (age_hours / 24) * 5
        elif age_hours < 48:
            return 5.0 - ((age_hours - 24) / 24) * 3
        else:
            return 2.0

    def _score_content_richness(self, content: str) -> float:
        """Score content depth and richness (0-15 points)."""
        score = 0.0

        # Length (6 points)
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

        # Quotes (4 points)
        quotes = content.count('"') + content.count("'")
        if quotes >= 4:
            score += 4
        elif quotes >= 2:
            score += 2

        return min(score, 15.0)

    def is_worthy(self, score: float, threshold: float = 60.0) -> bool:
        """
        Determine if content is worthy of video production.

        Args:
            score: Overall content score (0-100)
            threshold: Minimum score for worthiness (default 60.0)

        Returns:
            True if score meets threshold
        """
        return score >= threshold
