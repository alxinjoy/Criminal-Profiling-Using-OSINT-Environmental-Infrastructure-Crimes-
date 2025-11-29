"""
Shared utilities for Eco-Forensics backend.
Includes rate limiting, retry logic, file storage, and validation helpers.
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from functools import wraps

import httpx

from .config import settings
from .logger_config import get_logger
from .api_models import SourceError, BBox

logger = get_logger("utils")

T = TypeVar('T')


# ============== Rate Limiter ==============

class TokenBucketRateLimiter:
    """
    Simple token bucket rate limiter for API calls.
    Thread-safe using asyncio locks.
    """
    
    def __init__(self, tokens_per_minute: int, bucket_size: Optional[int] = None):
        self.tokens_per_minute = tokens_per_minute
        self.bucket_size = bucket_size or tokens_per_minute
        self.tokens = float(self.bucket_size)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> None:
        """
        Wait until tokens are available, then consume them.
        """
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_update
                
                # Refill tokens based on elapsed time
                self.tokens = min(
                    self.bucket_size,
                    self.tokens + elapsed * (self.tokens_per_minute / 60.0)
                )
                self.last_update = now
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                
                # Wait for tokens to refill
                wait_time = (tokens - self.tokens) / (self.tokens_per_minute / 60.0)
                await asyncio.sleep(min(wait_time, 1.0))


# Global rate limiters for different services
rate_limiters: Dict[str, TokenBucketRateLimiter] = {
    "google": TokenBucketRateLimiter(tokens_per_minute=60),
    "sentinel": TokenBucketRateLimiter(tokens_per_minute=30),
    "gfw": TokenBucketRateLimiter(tokens_per_minute=60),
    "overpass": TokenBucketRateLimiter(tokens_per_minute=30),
    "gleif": TokenBucketRateLimiter(tokens_per_minute=60),
    "reddit": TokenBucketRateLimiter(tokens_per_minute=30),
    "gdelt": TokenBucketRateLimiter(tokens_per_minute=60),
}


async def rate_limit(service: str) -> None:
    """
    Apply rate limiting for a service.
    """
    if service in rate_limiters:
        await rate_limiters[service].acquire()


# ============== Retry Logic ==============

async def retry_with_backoff(
    func: Callable,
    *args,
    max_retries: int = 3,
    delays: tuple = (1, 2, 4),
    retryable_exceptions: tuple = (httpx.TimeoutException, httpx.NetworkError),
    **kwargs
) -> Any:
    """
    Execute an async function with retry and exponential backoff.
    
    Args:
        func: Async function to execute
        max_retries: Maximum number of attempts
        delays: Tuple of delay times in seconds for each retry
        retryable_exceptions: Exception types that trigger retry
    
    Returns:
        Result from successful function call
    
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = delays[min(attempt, len(delays) - 1)]
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"All {max_retries} attempts failed for {func.__name__}: {e}")
    
    raise last_exception


# ============== File Storage ==============

def get_storage_path(service: str, identifier: str) -> Path:
    """
    Get the storage path for raw API responses.
    
    Args:
        service: Service name (firms, glad, sentinel, etc.)
        identifier: Unique identifier (bbox hash, region name, etc.)
    
    Returns:
        Path to storage directory
    """
    path = settings.data_path / service / identifier
    path.mkdir(parents=True, exist_ok=True)
    return path


def bbox_to_hash(bbox: tuple) -> str:
    """
    Create a short hash of a bounding box for file naming.
    """
    bbox_str = f"{bbox[0]:.4f},{bbox[1]:.4f},{bbox[2]:.4f},{bbox[3]:.4f}"
    return hashlib.md5(bbox_str.encode()).hexdigest()[:12]


async def save_raw_response(
    service: str,
    identifier: str,
    data: Any,
    filename_prefix: str = "response"
) -> Path:
    """
    Save raw API response to disk for reproducibility.
    
    Args:
        service: Service name
        identifier: Unique identifier for this request
        data: Data to save (will be JSON serialized)
        filename_prefix: Prefix for the filename
    
    Returns:
        Path to saved file
    """
    storage_path = get_storage_path(service, identifier)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.json"
    filepath = storage_path / filename
    
    # Convert data to JSON-serializable format
    if hasattr(data, 'dict'):
        data = data.dict()
    elif hasattr(data, 'model_dump'):
        data = data.model_dump()
    
    # Handle datetime objects
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=json_serializer)
    
    logger.debug(f"Saved raw response to {filepath}")
    return filepath


# ============== Validation Helpers ==============

def validate_bbox(bbox: tuple) -> tuple[bool, Optional[str]]:
    """
    Validate a bounding box.
    
    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
    
    Returns:
        (is_valid, error_message)
    """
    if len(bbox) != 4:
        return False, "BBox must have exactly 4 values"
    
    min_lon, min_lat, max_lon, max_lat = bbox
    
    # Check lat/lon ranges
    if not (-180 <= min_lon <= 180) or not (-180 <= max_lon <= 180):
        return False, "Longitude must be between -180 and 180"
    
    if not (-90 <= min_lat <= 90) or not (-90 <= max_lat <= 90):
        return False, "Latitude must be between -90 and 90"
    
    # Check ordering
    if min_lon > max_lon:
        return False, "min_lon must be <= max_lon"
    
    if min_lat > max_lat:
        return False, "min_lat must be <= max_lat"
    
    # Check reasonable area (max ~10 million sq km ≈ 100 sq degrees)
    area = (max_lon - min_lon) * (max_lat - min_lat)
    if area > 1000:
        return False, f"BBox area too large ({area:.1f} sq degrees). Max is 1000."
    
    if area < 0.0001:
        return False, "BBox area too small. Minimum is 0.0001 sq degrees."
    
    return True, None


def parse_bbox_string(bbox_str: str) -> tuple:
    """
    Parse a bbox string like "minLon,minLat,maxLon,maxLat" into a tuple.
    """
    parts = [float(x.strip()) for x in bbox_str.split(',')]
    if len(parts) != 4:
        raise ValueError("BBox must have exactly 4 comma-separated values")
    return tuple(parts)


# ============== Error Helpers ==============

def create_source_error(
    source: str,
    exception: Exception,
    retryable: bool = False
) -> SourceError:
    """
    Create a standardized SourceError from an exception.
    """
    return SourceError(
        source=source,
        error_type=type(exception).__name__,
        message=str(exception)[:500],  # Truncate long messages
        retryable=retryable,
        timestamp=datetime.utcnow()
    )


def is_retryable_error(exception: Exception) -> bool:
    """
    Determine if an exception represents a retryable error.
    """
    retryable_types = (
        httpx.TimeoutException,
        httpx.NetworkError,
        ConnectionError,
        TimeoutError,
    )
    
    # Check exception type
    if isinstance(exception, retryable_types):
        return True
    
    # Check for specific HTTP status codes in response errors
    if isinstance(exception, httpx.HTTPStatusError):
        status = exception.response.status_code
        # 429 (rate limit), 5xx (server errors) are retryable
        return status == 429 or status >= 500
    
    return False


# ============== Geo Helpers ==============

def bbox_centroid(bbox: tuple) -> tuple:
    """
    Calculate the centroid of a bounding box.
    
    Returns:
        (center_lon, center_lat)
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    return (
        (min_lon + max_lon) / 2,
        (min_lat + max_lat) / 2
    )


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.
    
    Returns:
        Distance in meters
    """
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371000  # Earth's radius in meters
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c