"""
Social media and news sentiment analysis module.
(Continued from Part 2)
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus

import httpx

from .config import settings, GLOBAL_REGIONS
from .logger_config import get_logger
from .api_models import SentimentScore, CombinedSentiment, SourceError
from .utils import (
    retry_with_backoff, rate_limit, save_raw_response, bbox_to_hash,
    create_source_error
)

logger = get_logger("social_voice")


# ============== Simple Sentiment Analysis ==============

NEGATIVE_KEYWORDS = [
    'deforestation', 'destruction', 'illegal', 'logging', 'fire', 'burning',
    'pollution', 'damage', 'violation', 'fine', 'penalty', 'lawsuit',
    'scandal', 'corrupt', 'accused', 'investigation', 'harm', 'toxic',
    'spill', 'contamination', 'criminal', 'fraud', 'exploit', 'abuse',
    'clearcut', 'slash', 'burn', 'encroachment', 'poaching', 'smuggling'
]

POSITIVE_KEYWORDS = [
    'sustainable', 'conservation', 'protection', 'restoration', 'reforestation',
    'certified', 'green', 'eco-friendly', 'renewable', 'initiative', 
    'partnership', 'award', 'commitment', 'progress', 'improvement',
    'compliance', 'transparency', 'responsible'
]


def analyze_text_sentiment(text: str) -> float:
    """Simple keyword-based sentiment analysis. Returns -1 to 1."""
    if not text:
        return 0.0
    
    text_lower = text.lower()
    neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
    pos_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
    
    total = neg_count + pos_count
    if total == 0:
        return 0.0
    
    return round((pos_count - neg_count) / total, 3)


def extract_keywords(text: str, limit: int = 10) -> List[str]:
    """Extract relevant keywords from text."""
    if not text:
        return []
    
    text_lower = text.lower()
    found = []
    for kw in NEGATIVE_KEYWORDS + POSITIVE_KEYWORDS:
        if kw in text_lower and kw not in found:
            found.append(kw)
            if len(found) >= limit:
                break
    return found


# ============== Google Custom Search ==============

async def fetch_google_news_sentiment(
    query: str,
    region_or_bbox: Any,
    limit: int = 20
) -> Dict[str, Any]:
    """Fetch news via Google Custom Search and analyze sentiment."""
    logger.info(f"Initiating Google News search for query='{query}'")
    start_time = datetime.utcnow()
    
    if not settings.google_cse_api_key or not settings.google_cse_engine_id:
        logger.warning("Google CSE credentials not configured")
        return {"data": None, "error": "Google CSE not configured"}
    
    try:
        await rate_limit("google")
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": settings.google_cse_api_key,
            "cx": settings.google_cse_engine_id,
            "q": query,
            "num": min(limit, 10),
            "dateRestrict": "d30",
            "sort": "date"
        }
        
        async def make_request():
            async with httpx.AsyncClient(timeout=settings.default_timeout_seconds) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        
        data = await retry_with_backoff(make_request, max_retries=settings.max_retries, delays=settings.retry_delays)
        
        items = data.get("items", [])
        if not items:
            return {"data": SentimentScore(count=0, score=0.0, keywords=[], sample_titles=[]), "error": None}
        
        scores = []
        all_keywords = []
        sample_titles = []
        
        for item in items:
            combined_text = f"{item.get('title', '')} {item.get('snippet', '')}"
            scores.append(analyze_text_sentiment(combined_text))
            all_keywords.extend(extract_keywords(combined_text, limit=5))
            if len(sample_titles) < 5:
                sample_titles.append(item.get("title", "")[:100])
        
        avg_score = sum(scores) / len(scores) if scores else 0.0
        unique_keywords = list(dict.fromkeys(all_keywords))[:10]
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Google News returned {len(items)} results, avg_sentiment={avg_score:.3f} in {elapsed:.2f}s")
        
        query_hash = query.replace(" ", "_")[:20]
        await save_raw_response("news", query_hash, data, "google_news")
        
        return {
            "data": SentimentScore(count=len(items), score=round(avg_score, 3), keywords=unique_keywords, sample_titles=sample_titles),
            "error": None
        }
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            return {"data": None, "error": "Google CSE quota exceeded"}
        return {"data": None, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Google News fetch failed: {e}")
        return {"data": None, "error": str(e)}


async def check_google_health() -> Tuple[bool, Optional[str]]:
    """Check Google CSE health."""
    if not settings.google_cse_api_key:
        return False, "API key not configured"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": settings.google_cse_api_key, "cx": settings.google_cse_engine_id, "q": "test", "num": 1}
            )
            if response.status_code == 429:
                return False, "Quota exceeded"
            return response.status_code < 500, None if response.status_code < 500 else f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)


# ============== GDELT Global Knowledge Graph ==============

GDELT_GKG_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


async def fetch_gdelt_sentiment(query: str, region_or_bbox: Any) -> Dict[str, Any]:
    """Fetch sentiment from GDELT Global Knowledge Graph."""
    logger.info(f"Initiating GDELT GKG fetch for query='{query}'")
    start_time = datetime.utcnow()
    
    try:
        await rate_limit("gdelt")
        
        full_query = f"{query} {region_or_bbox}" if isinstance(region_or_bbox, str) else query
        params = {"query": full_query, "mode": "ArtList", "maxrecords": 50, "format": "json", "timespan": "30d"}
        
        async def make_request():
            async with httpx.AsyncClient(timeout=settings.default_timeout_seconds) as client:
                response = await client.get(GDELT_GKG_URL, params=params)
                response.raise_for_status()
                return response.json()
        
        data = await retry_with_backoff(make_request, max_retries=settings.max_retries, delays=settings.retry_delays)
        
        articles = data.get("articles", [])
        if not articles:
            return {"data": SentimentScore(count=0, score=0.0, keywords=[], sample_titles=[]), "error": None}
        
        tones = []
        sample_titles = []
        all_keywords = []
        
        for article in articles:
            tone = article.get("tone", 0)
            if isinstance(tone, (int, float)):
                tones.append(max(-1, min(1, tone / 10)))
            
            title = article.get("title", "")
            if title and len(sample_titles) < 5:
                sample_titles.append(title[:100])
            all_keywords.extend(extract_keywords(title, limit=3))
        
        avg_tone = sum(tones) / len(tones) if tones else 0.0
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"GDELT returned {len(articles)} articles, avg_tone={avg_tone:.3f} in {elapsed:.2f}s")
        
        await save_raw_response("gdelt", query.replace(" ", "_")[:20], data, "gdelt_gkg")
        
        return {
            "data": SentimentScore(count=len(articles), score=round(avg_tone, 3), keywords=list(dict.fromkeys(all_keywords))[:10], sample_titles=sample_titles),
            "error": None
        }
        
    except Exception as e:
        logger.error(f"GDELT fetch failed: {e}")
        return {"data": None, "error": str(e)}


async def check_gdelt_health() -> Tuple[bool, Optional[str]]:
    """Check GDELT API health."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(GDELT_GKG_URL, params={"query": "test", "mode": "ArtList", "maxrecords": 1, "format": "json"})
            return response.status_code < 500, None if response.status_code < 500 else f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)


# ============== Reddit API ==============

REDDIT_OAUTH_URL = "https://oauth.reddit.com"
REDDIT_AUTH_URL = "https://www.reddit.com/api/v1/access_token"


class RedditClient:
    """Reddit API client with OAuth and graceful fallback."""
    
    def __init__(self):
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
    
    async def _get_token(self) -> str:
        """Get or refresh OAuth token."""
        if self._token and self._token_expires and datetime.utcnow() < self._token_expires:
            return self._token
        
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            raise ValueError("Reddit credentials not configured")
        
        auth = httpx.BasicAuth(settings.reddit_client_id, settings.reddit_client_secret)
        data = {"grant_type": "password", "username": settings.reddit_username, "password": settings.reddit_password}
        headers = {"User-Agent": settings.reddit_user_agent}
        
        async with httpx.AsyncClient(timeout=settings.default_timeout_seconds) as client:
            response = await client.post(REDDIT_AUTH_URL, auth=auth, data=data, headers=headers)
            response.raise_for_status()
            token_data = response.json()
        
        if "error" in token_data:
            raise ValueError(f"Reddit auth error: {token_data.get('error')}")
        
        self._token = token_data["access_token"]
        self._token_expires = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600) - 60)
        logger.info("Reddit OAuth token obtained")
        return self._token
    
    async def search(self, query: str, subreddit: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        """Search Reddit posts."""
        await rate_limit("reddit")
        token = await self._get_token()
        
        url = f"{REDDIT_OAUTH_URL}/r/{subreddit}/search" if subreddit else f"{REDDIT_OAUTH_URL}/search"
        params = {"q": query, "limit": limit, "sort": "relevance", "t": "month", "type": "link"}
        headers = {"Authorization": f"Bearer {token}", "User-Agent": settings.reddit_user_agent}
        
        async with httpx.AsyncClient(timeout=settings.default_timeout_seconds) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()


_reddit_client = RedditClient()

# Environment-related subreddits for searching
ENVIRONMENT_SUBREDDITS = [
    "environment", "climate", "sustainability", "conservation",
    "worldnews", "news", "science"
]


async def fetch_reddit_sentiment(
    query: str,
    region_or_bbox: Any,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Fetch Reddit posts and analyze sentiment.
    Includes graceful fallback if API is restricted.
    """
    logger.info(f"Initiating Reddit fetch for query='{query}'")
    start_time = datetime.utcnow()
    
    if not settings.reddit_client_id:
        logger.warning("Reddit credentials not configured - skipping")
        return {
            "data": None, 
            "error": "Reddit API not configured",
            "source_error": SourceError(
                source="reddit",
                error_type="ConfigurationError",
                message="Reddit credentials not configured",
                retryable=False,
                timestamp=datetime.utcnow()
            )
        }
    
    try:
        # Search across environment subreddits
        all_posts = []
        
        for subreddit in ENVIRONMENT_SUBREDDITS[:3]:  # Limit to avoid rate limits
            try:
                data = await _reddit_client.search(query, subreddit=subreddit, limit=limit // 3)
                posts = data.get("data", {}).get("children", [])
                all_posts.extend(posts)
            except Exception as e:
                logger.debug(f"Reddit search in r/{subreddit} failed: {e}")
                continue
        
        if not all_posts:
            # Try general search
            try:
                data = await _reddit_client.search(query, limit=limit)
                all_posts = data.get("data", {}).get("children", [])
            except Exception as e:
                logger.warning(f"Reddit general search failed: {e}")
        
        if not all_posts:
            return {"data": SentimentScore(count=0, score=0.0, keywords=[], sample_titles=[]), "error": None}
        
        # Analyze posts
        scores = []
        sample_titles = []
        all_keywords = []
        
        for post in all_posts:
            post_data = post.get("data", {})
            title = post_data.get("title", "")
            selftext = post_data.get("selftext", "")[:500]
            combined = f"{title} {selftext}"
            
            score = analyze_text_sentiment(combined)
            
            # Weight by upvotes (log scale to prevent domination)
            ups = post_data.get("ups", 1)
            weight = 1 + (0.1 * min(10, (ups / 100))) if ups > 0 else 1
            scores.append(score * weight)
            
            all_keywords.extend(extract_keywords(combined, limit=3))
            if len(sample_titles) < 5:
                sample_titles.append(title[:100])
        
        avg_score = sum(scores) / len(scores) if scores else 0.0
        # Normalize back to -1 to 1 range
        avg_score = max(-1, min(1, avg_score))
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Reddit returned {len(all_posts)} posts, avg_sentiment={avg_score:.3f} in {elapsed:.2f}s")
        
        await save_raw_response("reddit", query.replace(" ", "_")[:20], {"posts": [p.get("data", {}).get("title") for p in all_posts[:20]]}, "reddit_posts")
        
        return {
            "data": SentimentScore(
                count=len(all_posts),
                score=round(avg_score, 3),
                keywords=list(dict.fromkeys(all_keywords))[:10],
                sample_titles=sample_titles
            ),
            "error": None
        }
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            logger.error("Reddit API access denied (403) - API may require developer approval")
            return {
                "data": None,
                "error": "Reddit API access denied - may require developer approval",
                "source_error": SourceError(
                    source="reddit",
                    error_type="HTTPStatusError",
                    message="403 Forbidden - Reddit API access restricted",
                    retryable=False,
                    timestamp=datetime.utcnow()
                )
            }
        return {"data": None, "error": f"HTTP {e.response.status_code}"}
    except ValueError as e:
        # Auth errors
        logger.error(f"Reddit auth error: {e}")
        return {
            "data": None,
            "error": str(e),
            "source_error": SourceError(
                source="reddit",
                error_type="AuthenticationError",
                message=str(e),
                retryable=False,
                timestamp=datetime.utcnow()
            )
        }
    except Exception as e:
        logger.error(f"Reddit fetch failed: {e}")
        return {"data": None, "error": str(e)}


async def check_reddit_health() -> Tuple[bool, Optional[str]]:
    """Check Reddit API health."""
    if not settings.reddit_client_id:
        return False, "Not configured"
    try:
        await _reddit_client._get_token()
        return True, None
    except Exception as e:
        return False, str(e)


# ============== Combined Sentiment ==============

async def compute_combined_sentiment(
    google: Optional[SentimentScore],
    gdelt: Optional[SentimentScore],
    reddit: Optional[SentimentScore]
) -> CombinedSentiment:
    """
    Compute weighted combined sentiment from all sources.
    Weights: Google 0.5, GDELT 0.3, Reddit 0.2
    """
    weights = {"google": 0.5, "gdelt": 0.3, "reddit": 0.2}
    
    weighted_sum = 0.0
    total_weight = 0.0
    total_count = 0
    
    sources = {"google": google, "gdelt": gdelt, "reddit": reddit}
    
    for name, score in sources.items():
        if score and score.count > 0:
            weighted_sum += score.score * weights[name]
            total_weight += weights[name]
            total_count += score.count
    
    # Calculate final score
    if total_weight > 0:
        final_score = weighted_sum / total_weight
    else:
        final_score = 0.0
    
    # Confidence based on sample size and source diversity
    source_count = sum(1 for s in sources.values() if s and s.count > 0)
    sample_confidence = min(1.0, total_count / 50)  # Max confidence at 50+ samples
    source_confidence = source_count / 3
    confidence = (sample_confidence * 0.6) + (source_confidence * 0.4)
    
    # Determine dominant narrative
    all_keywords = []
    for score in sources.values():
        if score:
            all_keywords.extend(score.keywords)
    
    if all_keywords:
        # Most common keyword
        from collections import Counter
        keyword_counts = Counter(all_keywords)
        dominant = keyword_counts.most_common(1)[0][0] if keyword_counts else None
    else:
        dominant = None
    
    return CombinedSentiment(
        google=google,
        gdelt=gdelt,
        reddit=reddit,
        final_score=round(final_score, 3),
        confidence=round(confidence, 3),
        dominant_narrative=dominant
    )


async def fetch_all_sentiment(
    query: str,
    region_or_bbox: Any
) -> Tuple[CombinedSentiment, List[SourceError]]:
    """
    Fetch sentiment from all sources in parallel and combine.
    
    Returns:
        (CombinedSentiment, list of SourceErrors)
    """
    logger.info(f"Fetching all sentiment sources for query='{query}'")
    
    # Parallel fetch
    results = await asyncio.gather(
        fetch_google_news_sentiment(query, region_or_bbox),
        fetch_gdelt_sentiment(query, region_or_bbox),
        fetch_reddit_sentiment(query, region_or_bbox),
        return_exceptions=True
    )
    
    google_result, gdelt_result, reddit_result = results
    errors = []
    
    # Handle exceptions and extract data
    def extract_result(result, source_name):
        if isinstance(result, Exception):
            errors.append(SourceError(
                source=source_name,
                error_type=type(result).__name__,
                message=str(result),
                retryable=False,
                timestamp=datetime.utcnow()
            ))
            return None
        
        if result.get("source_error"):
            errors.append(result["source_error"])
        
        if result.get("error") and not result.get("data"):
            errors.append(SourceError(
                source=source_name,
                error_type="FetchError",
                message=result["error"],
                retryable=True,
                timestamp=datetime.utcnow()
            ))
        
        return result.get("data")
    
    google = extract_result(google_result, "google_news")
    gdelt = extract_result(gdelt_result, "gdelt")
    reddit = extract_result(reddit_result, "reddit")
    
    combined = await compute_combined_sentiment(google, gdelt, reddit)
    
    return combined, errors