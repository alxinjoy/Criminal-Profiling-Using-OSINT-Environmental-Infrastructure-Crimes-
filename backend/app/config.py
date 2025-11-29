# config.py
"""
Configuration management for Eco-Forensics backend.
Loads environment variables and defines global constants including region definitions
and dataset coverage mappings.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

from .logger_config import get_logger

logger = get_logger("config")

# Load .env file if present
load_dotenv()


@dataclass
class RegionConfig:
    """Configuration for a predefined region."""
    name: str
    bbox: tuple  # (min_lon, min_lat, max_lon, max_lat) - EPSG:4326
    description: str
    climate_zone: str  # "tropical", "temperate", "boreal", etc.


# Global regions with their bounding boxes (EPSG:4326)
GLOBAL_REGIONS: Dict[str, RegionConfig] = {
    "amazon": RegionConfig(
        name="Amazon",
        bbox=(-73.0, -15.0, -45.0, 5.0),
        description="Amazon Rainforest - Brazil, Peru, Colombia",
        climate_zone="tropical"
    ),
    "congo": RegionConfig(
        name="Congo Basin",
        bbox=(9.0, -13.0, 31.0, 10.0),
        description="Congo Rainforest - DRC, Republic of Congo, Cameroon",
        climate_zone="tropical"
    ),
    "riau": RegionConfig(
        name="Riau",
        bbox=(100.0, -1.0, 104.0, 3.0),
        description="Riau Province, Sumatra, Indonesia",
        climate_zone="tropical"
    ),
    "borneo": RegionConfig(
        name="Borneo",
        bbox=(108.0, -4.5, 119.5, 7.5),
        description="Borneo Island - Indonesia, Malaysia, Brunei",
        climate_zone="tropical"
    ),
    "se_brazil": RegionConfig(
        name="SE Brazil",
        bbox=(-53.0, -28.0, -40.0, -18.0),
        description="Southeast Brazil - Atlantic Forest and Cerrado",
        climate_zone="tropical"
    ),
    "california": RegionConfig(
        name="California",
        bbox=(-124.5, 32.5, -114.0, 42.0),
        description="California, USA - Fire-prone regions",
        climate_zone="temperate"
    ),
    "siberia": RegionConfig(
        name="Siberia",
        bbox=(60.0, 50.0, 140.0, 75.0),
        description="Siberian forests - Russia",
        climate_zone="boreal"
    ),
    "australia": RegionConfig(
        name="Australia",
        bbox=(113.0, -44.0, 154.0, -10.0),
        description="Australia - bushfire regions",
        climate_zone="temperate"
    ),
}


# Dataset coverage definitions
# "global" = worldwide coverage
# "tropical" = roughly 30°N to 30°S, best in humid tropical forests
# "tropical_humid" = primary humid tropical forests only
DATASET_COVERAGE: Dict[str, Dict[str, Any]] = {
    "hansen_gfc": {
        "coverage": "global",
        "lat_range": (-90, 90),
        "description": "Hansen Global Forest Change - annual forest loss"
    },
    "firms": {
        "coverage": "global",
        "lat_range": (-90, 90),
        "description": "MODIS/VIIRS active fire detections"
    },
    "gfw_glad": {
        "coverage": "tropical",
        "lat_range": (-30, 30),
        "description": "GLAD deforestation alerts - optical, tropical belt",
        "notes": "Best performance in humid tropical forests"
    },
    "gfw_radd": {
        "coverage": "tropical_humid",
        "lat_range": (-30, 30),
        "description": "RADD alerts - radar-based, primary humid tropical forests",
        "notes": "Coverage expanding; currently limited to primary humid tropical"
    },
    "sentinel_hub": {
        "coverage": "global",
        "lat_range": (-90, 90),
        "description": "Sentinel-2 imagery - NDVI, NBR, true color"
    },
    "overpass": {
        "coverage": "global",
        "lat_range": (-90, 90),
        "description": "OpenStreetMap infrastructure data"
    },
    "gleif": {
        "coverage": "global",
        "lat_range": None,
        "description": "Legal Entity Identifier data"
    },
    "google_news": {
        "coverage": "global",
        "lat_range": None,
        "description": "Google Custom Search for news"
    },
    "gdelt": {
        "coverage": "global",
        "lat_range": None,
        "description": "GDELT Global Knowledge Graph"
    },
    "reddit": {
        "coverage": "global",
        "lat_range": None,
        "description": "Reddit community posts",
        "notes": "API access may require developer approval"
    },
}


def is_region_covered(dataset: str, bbox: tuple) -> tuple[bool, Optional[str]]:
    """
    Check if a bounding box falls within dataset coverage.
    
    Args:
        dataset: Dataset name from DATASET_COVERAGE
        bbox: (min_lon, min_lat, max_lon, max_lat)
    
    Returns:
        Tuple of (is_covered: bool, skip_reason: Optional[str])
    """
    if dataset not in DATASET_COVERAGE:
        return False, f"Unknown dataset: {dataset}"
    
    config = DATASET_COVERAGE[dataset]
    
    # Datasets without geographic restrictions
    if config["lat_range"] is None:
        return True, None
    
    min_lon, min_lat, max_lon, max_lat = bbox
    lat_min_allowed, lat_max_allowed = config["lat_range"]
    
    coverage_type = config["coverage"]
    
    if coverage_type == "global":
        return True, None
    
    elif coverage_type == "tropical":
        # Check if bbox is within tropical belt
        if max_lat < lat_min_allowed or min_lat > lat_max_allowed:
            return False, f"Region outside tropical coverage ({lat_min_allowed}° to {lat_max_allowed}°)"
        return True, None
    
    elif coverage_type == "tropical_humid":
        # Stricter - must be mostly within tropical belt
        # and we add a note about limited coverage
        if max_lat < lat_min_allowed or min_lat > lat_max_allowed:
            return False, "Region outside tropical humid forest coverage"
        # Even within range, RADD has limited coverage
        return True, config.get("notes")
    
    return True, None


@dataclass
class Settings:
    """Application settings loaded from environment variables."""
    
    # Google Earth Engine
    gee_credentials_json: str = field(default_factory=lambda: os.getenv("GEE_CREDENTIALS_JSON", "/secrets/gee.json"))
    
    # Global Forest Watch
    gfw_api_key: str = field(default_factory=lambda: os.getenv("GFW_API_KEY", ""))
    gfw_api_base: str = field(default_factory=lambda: os.getenv("GFW_API_BASE", "https://data-api.globalforestwatch.org"))
    
    # Sentinel Hub
    sentinelhub_client_id: str = field(default_factory=lambda: os.getenv("SENTINELHUB_CLIENT_ID", ""))
    sentinelhub_client_secret: str = field(default_factory=lambda: os.getenv("SENTINELHUB_CLIENT_SECRET", ""))
    sentinelhub_instance_id: str = field(default_factory=lambda: os.getenv("SENTINELHUB_INSTANCE_ID", ""))
    # Base host; endpoints are constructed in the SentinelHubClient
    sentinelhub_base_url: str = field(default_factory=lambda: os.getenv(
        "SENTINELHUB_BASE_URL",
        "https://services.sentinel-hub.com"
    ))
    
    # Google Custom Search
    google_cse_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_CSE_API_KEY", ""))
    google_cse_engine_id: str = field(default_factory=lambda: os.getenv("GOOGLE_CSE_ENGINE_ID", ""))
    
    # Reddit
    reddit_client_id: str = field(default_factory=lambda: os.getenv("REDDIT_CLIENT_ID", ""))
    reddit_client_secret: str = field(default_factory=lambda: os.getenv("REDDIT_CLIENT_SECRET", ""))
    reddit_username: str = field(default_factory=lambda: os.getenv("REDDIT_USERNAME", ""))
    reddit_password: str = field(default_factory=lambda: os.getenv("REDDIT_PASSWORD", ""))
    reddit_user_agent: str = field(default_factory=lambda: os.getenv("REDDIT_USER_AGENT", "eco-forensics/1.0"))
    
    # GLEIF
    gleif_api_base: str = field(default_factory=lambda: os.getenv("GLEIF_API_BASE", "https://api.gleif.org/api/v1"))
    
    # Database
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dev.db"))
    
    # Rate limiting
    api_rate_limit_per_min: int = field(default_factory=lambda: int(os.getenv("API_RATE_LIMIT_PER_MIN", "60")))
    
    # Timeouts
    default_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("DEFAULT_TIMEOUT_SECONDS", "12")))
    sentinelhub_timeout_seconds: int = 15  # Override for Sentinel Hub
    
    # Retry settings
    max_retries: int = 3
    retry_delays: tuple = (1, 2, 4)  # seconds between retries
    
    # Data storage path
    data_path: Path = field(default_factory=lambda: Path(os.getenv("DATA_PATH", "./data")))
    
    def __post_init__(self):
        """Ensure data directories exist."""
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for each service
        for service in ["hansen", "firms", "glad", "radd", "sentinel", "overpass", "gleif", "news", "gdelt", "reddit"]:
            (self.data_path / service).mkdir(exist_ok=True)
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of warnings/errors.
        """
        warnings: List[str] = []
        
        if not self.gfw_api_key:
            warnings.append("GFW_API_KEY not set - GFW endpoints will fail")
        
        if not self.sentinelhub_client_id or not self.sentinelhub_client_secret:
            warnings.append("Sentinel Hub credentials incomplete")
        
        if not self.google_cse_api_key:
            warnings.append("Google CSE API key not set - news search will fail")
        
        if not self.reddit_client_id:
            warnings.append("Reddit credentials not set - Reddit sentiment will be skipped")
        
        return warnings


# Global settings instance
settings = Settings()

# Log configuration warnings on import
_warnings = settings.validate()
for w in _warnings:
    logger.warning(w)
