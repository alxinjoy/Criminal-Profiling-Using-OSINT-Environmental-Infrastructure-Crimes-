Yes, there are a few files that need updates and some missing files. Let me identify them:

## Files Needing Updates/Completion

### 1. `backend/app/social_voice.py` - DUPLICATE ISSUE
Part 2 and Part 3 both contain this file. You should use **only the Part 3 version** as it's the complete one.

### 2. `backend/README.md` - INCOMPLETE
The file was cut off. Here's the completion:

```markdown
# Eco-Forensics Backend

A FastAPI backend for compiling cross-validated global "forensic dossiers" linking environmental damage to corporate entities.

## Features

- **Satellite Intelligence**: Hansen GFC, FIRMS fires, GLAD/RADD alerts, Sentinel Hub imagery
- **Infrastructure Mapping**: OpenStreetMap/Overpass API for nearby industrial facilities
- **Company Enrichment**: GLEIF API for Legal Entity Identifier lookups
- **Sentiment Analysis**: Google News, GDELT, Reddit (with graceful fallback)
- **Correlation Engine**: Links environmental damage to corporate suspects

## Quick Start

### 1. Clone and Setup

```bash
cd backend
cp .env.example .env
# Edit .env with your API credentials
```

### 2. Get API Credentials

#### Google Earth Engine
1. Create a Google Cloud project
2. Enable Earth Engine API
3. Create a service account with Earth Engine access
4. Download JSON key to `secrets/gee.json`

#### Global Forest Watch
1. Register at https://www.globalforestwatch.org/
2. Generate API key from your account settings

#### Sentinel Hub
1. Register at https://www.sentinel-hub.com/
2. Create an OAuth client in the dashboard
3. Note your Client ID, Client Secret, and Instance ID

#### Google Custom Search
1. Create a Programmable Search Engine at https://programmablesearchengine.google.com/
2. Get API key from Google Cloud Console
3. Note your Search Engine ID (cx)

#### Reddit (Optional)
1. Create an app at https://www.reddit.com/prefs/apps
2. Note Client ID and Secret
3. Note: Reddit API access may require approval

### 3. Run with Docker

```bash
docker-compose up --build
```

API will be available at http://localhost:8000

### 4. Run Locally (Development)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main_api:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health Check
```
GET /health
```
Returns status of all connected services.

### Generate Dossier
```
GET /dossier?region=Riau
GET /dossier?bbox=-73,-15,-45,5&start_date=2023-01-01&end_date=2023-12-31
```
Returns complete forensic dossier with satellite data, alerts, suspects, and evidence chain.

### Fire Data
```
GET /fires?region=Amazon&days=30
```

### Forest Loss
```
GET /loss?region=Borneo&years=2020,2021,2022
```

### Sentiment Analysis
```
GET /sentiment?region=Riau&query=palm%20oil%20deforestation
```

### Sentinel Preview
```
GET /sentinel/preview?bbox=100,-1,104,3&date=2023-06-15
```

## Available Regions

- `amazon` - Amazon Rainforest
- `congo` - Congo Basin
- `riau` - Riau Province, Indonesia
- `borneo` - Borneo Island
- `se_brazil` - Southeast Brazil
- `california` - California, USA
- `siberia` - Siberian forests
- `australia` - Australian bushfire regions

## Dataset Coverage Notes

| Dataset | Coverage | Notes |
|---------|----------|-------|
| Hansen GFC | Global | Annual forest loss data |
| FIRMS | Global | Active fire detections |
| GLAD Alerts | Tropical (30°N-30°S) | Best in humid tropical |
| RADD Alerts | Tropical humid only | Primary forests, expanding |
| Sentinel Hub | Global | 10m resolution imagery |

## Project Structure

```
backend/
├── app/
│   ├── logger_config.py    # Centralized logging
│   ├── config.py           # Configuration & regions
│   ├── api_models.py       # Pydantic schemas
│   ├── database.py         # SQLAlchemy models
│   ├── utils.py            # Rate limiting, retry, validation
│   ├── satellite_intel.py  # Satellite data fetchers
│   ├── suspect_profiler.py # Infrastructure & company enrichment
│   ├── social_voice.py     # Sentiment analysis
│   ├── correlation_engine.py # Evidence correlation
│   └── main_api.py         # FastAPI endpoints
├── data/                   # Raw API responses (auto-created)
├── secrets/                # API credentials (gitignored)
├── tests/
│   ├── fixtures/           # Test fixtures
│   ├── test_correlation.py
│   ├── test_fuzzy_match.py
│   └── test_integration.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_correlation.py -v
```

## License

MIT
```

---

### 3. **NEW FILE: `backend/runbook.md`**

```markdown
# Eco-Forensics Runbook

## Deployment

### Prerequisites
- Docker and Docker Compose installed
- API credentials configured in `.env`
- GEE service account JSON in `secrets/gee.json`

### Production Deployment

```bash
# Build and start
docker-compose up -d --build

# Check logs
docker-compose logs -f api

# Check health
curl http://localhost:8000/health
```

### Scaling Considerations
- For high traffic, add PostgreSQL (uncomment in docker-compose.yml)
- Consider Redis for rate limiting in distributed setup
- Add nginx reverse proxy for SSL termination

## Monitoring

### Health Check
```bash
curl http://localhost:8000/health | jq
```

Expected healthy response:
```json
{
  "status": "healthy",
  "services": [
    {"name": "google_earth_engine", "status": "healthy"},
    {"name": "global_forest_watch", "status": "healthy"},
    ...
  ]
}
```

### Log Analysis
Logs follow format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

```bash
# View errors only
docker-compose logs api | grep ERROR

# View specific module
docker-compose logs api | grep satellite_intel
```

## Troubleshooting

### Common Issues

#### 1. GEE Authentication Failed
```
ERROR - Failed to initialize Google Earth Engine
```
**Solution**: Verify `secrets/gee.json` exists and contains valid service account credentials.

#### 2. GFW API 401/403
```
ERROR - GLAD API HTTP error: 401
```
**Solution**: Check `GFW_API_KEY` in `.env` is valid and not expired.

#### 3. Sentinel Hub Timeout
```
WARNING - Attempt 1/3 failed for fetch_sentinelhub_ndvi: TimeoutException
```
**Solution**: Sentinel Hub has 15s timeout. For large areas, reduce bbox size.

#### 4. Reddit API 403
```
ERROR - Reddit API access denied (403)
```
**Solution**: Reddit API now requires developer approval. The system will skip Reddit and continue with other sources.

#### 5. GLAD/RADD Skipped for Region
```
WARNING - Dataset gfw_radd not available for region Siberia — skipping
```
**Expected behavior**: GLAD/RADD only cover tropical regions. Check `coverage_notes` in response.

### Data Issues

#### Missing Alerts
- Check date range (default: 90 days)
- Verify region has GLAD/RADD coverage
- Check `source_errors` in response

#### Low Confidence Score
- Fewer data sources = lower confidence
- Non-tropical regions lack GLAD/RADD
- Sentiment analysis may have few results

## Maintenance

### Database
```bash
# SQLite is file-based, backup:
cp data/dev.db data/dev.db.backup

# For PostgreSQL, use pg_dump
```

### Clear Raw Response Cache
```bash
# Raw responses stored in data/
rm -rf data/*/  # Clears all cached responses
```

### Update Dependencies
```bash
pip install -r requirements.txt --upgrade
docker-compose build --no-cache
```

## API Rate Limits

| Service | Limit | Notes |
|---------|-------|-------|
| Google CSE | 100/day free | Paid plans available |
| Sentinel Hub | 30/min | Configurable |
| GFW | 60/min | |
| Overpass | 30/min | Public server limits |
| GLEIF | 60/min | No auth required |
| Reddit | 30/min | May be restricted |

## Emergency Procedures

### Service Degradation
1. Check `/health` endpoint
2. Identify failing service
3. API continues with available sources
4. Check `source_errors` in dossier response

### Complete Outage
```bash
# Restart container
docker-compose restart api

# Full rebuild
docker-compose down
docker-compose up -d --build
```

### Data Recovery
Raw API responses are saved to `data/{service}/` for reproducibility.
```bash
# Find recent responses
find data/ -name "*.json" -mtime -1
```
```

---

### 4. **NEW FILE: `backend/tests/__init__.py`**

```python
"""Test package for Eco-Forensics backend."""
```

---

### 5. **NEW FILE: `backend/tests/test_fuzzy_match.py`**

```python
"""
Unit tests for fuzzy matching utilities.
"""

import pytest
from app.suspect_profiler import (
    fuzzy_match_company,
    normalize_company_name,
    calculate_match_confidence
)


class TestNormalizeCompanyName:
    """Tests for company name normalization."""
    
    def test_removes_common_suffixes(self):
        assert normalize_company_name("Acme Corp") == "ACME"
        assert normalize_company_name("Acme Corporation") == "ACME"
        assert normalize_company_name("Acme Inc.") == "ACME"
        assert normalize_company_name("Acme LLC") == "ACME"
        assert normalize_company_name("Acme Ltd.") == "ACME"
        assert normalize_company_name("Acme PLC") == "ACME"
    
    def test_handles_whitespace(self):
        assert normalize_company_name("  Acme  Corp  ") == "ACME"
        assert normalize_company_name("Acme\t\nCorp") == "ACME"
    
    def test_uppercase_conversion(self):
        assert normalize_company_name("acme corp") == "ACME"
        assert normalize_company_name("ACME CORP") == "ACME"
    
    def test_empty_string(self):
        assert normalize_company_name("") == ""
        assert normalize_company_name(None) == ""


class TestFuzzyMatchCompany:
    """Tests for fuzzy company matching."""
    
    def test_exact_match(self):
        candidates = ["Acme Corporation", "Beta Inc", "Gamma LLC"]
        results = fuzzy_match_company("Acme Corporation", candidates)
        assert len(results) > 0
        assert results[0][0] == "Acme Corporation"
        assert results[0][1] == 100
    
    def test_partial_match(self):
        candidates = ["Acme Corporation", "Acme Industries", "Beta Corp"]
        results = fuzzy_match_company("Acme Corp", candidates, threshold=60)
        assert len(results) >= 1
        # Should match Acme entries
        assert any("Acme" in r[0] for r in results)
    
    def test_threshold_filtering(self):
        candidates = ["Acme Corporation", "Completely Different"]
        results = fuzzy_match_company("Acme", candidates, threshold=80)
        # Should not include "Completely Different"
        assert not any("Different" in r[0] for r in results)
    
    def test_empty_candidates(self):
        results = fuzzy_match_company("Acme", [])
        assert results == []
    
    def test_no_matches_above_threshold(self):
        candidates = ["XYZ Corp", "ABC Inc"]
        results = fuzzy_match_company("Completely Unrelated Name", candidates, threshold=90)
        assert results == []


class TestCalculateMatchConfidence:
    """Tests for match confidence calculation."""
    
    def test_exact_match_with_lei(self):
        confidence = calculate_match_confidence(
            query="Acme Corporation",
            matched="Acme Corporation",
            lei_found=True
        )
        assert confidence >= 95
    
    def test_exact_match_without_lei(self):
        confidence = calculate_match_confidence(
            query="Acme Corporation",
            matched="Acme Corporation",
            lei_found=False
        )
        assert 80 <= confidence <= 100
    
    def test_partial_match(self):
        confidence = calculate_match_confidence(
            query="Acme",
            matched="Acme Corporation International",
            lei_found=False
        )
        assert confidence < 90
    
    def test_lei_bonus(self):
        without_lei = calculate_match_confidence("Acme", "Acme Corp", False)
        with_lei = calculate_match_confidence("Acme", "Acme Corp", True)
        assert with_lei > without_lei
```

---

### 6. **NEW FILE: `backend/tests/test_sentiment.py`**

```python
"""
Unit tests for sentiment analysis.
"""

import pytest
from app.social_voice import (
    analyze_text_sentiment,
    extract_keywords,
    compute_combined_sentiment
)
from app.api_models import SentimentScore


class TestAnalyzeTextSentiment:
    """Tests for text sentiment analysis."""
    
    def test_negative_sentiment(self):
        text = "Illegal deforestation and destruction of forest"
        score = analyze_text_sentiment(text)
        assert score < 0
    
    def test_positive_sentiment(self):
        text = "Sustainable conservation and reforestation initiative"
        score = analyze_text_sentiment(text)
        assert score > 0
    
    def test_neutral_sentiment(self):
        text = "The company released a statement today"
        score = analyze_text_sentiment(text)
        assert score == 0.0
    
    def test_mixed_sentiment(self):
        text = "Despite deforestation concerns, the company launched a sustainable initiative"
        score = analyze_text_sentiment(text)
        # Should be close to neutral with mixed keywords
        assert -0.5 <= score <= 0.5
    
    def test_empty_text(self):
        assert analyze_text_sentiment("") == 0.0
        assert analyze_text_sentiment(None) == 0.0
    
    def test_score_range(self):
        # Heavily negative
        text = "illegal deforestation destruction fire burning pollution damage"
        score = analyze_text_sentiment(text)
        assert -1 <= score <= 1


class TestExtractKeywords:
    """Tests for keyword extraction."""
    
    def test_extracts_negative_keywords(self):
        text = "Reports of illegal deforestation and burning"
        keywords = extract_keywords(text)
        assert "illegal" in keywords
        assert "deforestation" in keywords
        assert "burning" in keywords
    
    def test_extracts_positive_keywords(self):
        text = "New sustainable conservation program launched"
        keywords = extract_keywords(text)
        assert "sustainable" in keywords
        assert "conservation" in keywords
    
    def test_limit_parameter(self):
        text = "deforestation destruction illegal fire burning pollution"
        keywords = extract_keywords(text, limit=3)
        assert len(keywords) <= 3
    
    def test_empty_text(self):
        assert extract_keywords("") == []
        assert extract_keywords(None) == []


class TestComputeCombinedSentiment:
    """Tests for combined sentiment calculation."""
    
    @pytest.mark.asyncio
    async def test_all_sources_available(self):
        google = SentimentScore(count=10, score=-0.5, keywords=["deforestation"], sample_titles=[])
        gdelt = SentimentScore(count=20, score=-0.3, keywords=["fire"], sample_titles=[])
        reddit = SentimentScore(count=5, score=-0.7, keywords=["illegal"], sample_titles=[])
        
        combined = await compute_combined_sentiment(google, gdelt, reddit)
        
        # Weighted: 0.5*(-0.5) + 0.3*(-0.3) + 0.2*(-0.7) = -0.25 - 0.09 - 0.14 = -0.48
        assert combined.final_score < 0
        assert combined.confidence > 0.5  # Multiple sources
        assert combined.google == google
        assert combined.gdelt == gdelt
        assert combined.reddit == reddit
    
    @pytest.mark.asyncio
    async def test_missing_sources(self):
        google = SentimentScore(count=10, score=-0.5, keywords=[], sample_titles=[])
        
        combined = await compute_combined_sentiment(google, None, None)
        
        assert combined.final_score == -0.5  # Only Google available
        assert combined.confidence < 0.5  # Low confidence with one source
    
    @pytest.mark.asyncio
    async def test_all_sources_missing(self):
        combined = await compute_combined_sentiment(None, None, None)
        
        assert combined.final_score == 0.0
        assert combined.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_dominant_narrative(self):
        google = SentimentScore(count=10, score=-0.5, keywords=["deforestation", "fire"], sample_titles=[])
        gdelt = SentimentScore(count=20, score=-0.3, keywords=["deforestation", "illegal"], sample_titles=[])
        reddit = SentimentScore(count=5, score=-0.7, keywords=["deforestation"], sample_titles=[])
        
        combined = await compute_combined_sentiment(google, gdelt, reddit)
        
        # "deforestation" appears most frequently
        assert combined.dominant_narrative == "deforestation"
```

---

### 7. **NEW FILE: `backend/tests/test_correlation.py`**

```python
"""
Unit tests for correlation engine.
"""

import pytest
from datetime import datetime, timedelta
from app.correlation_engine import (
    calculate_spatial_proximity_score,
    calculate_temporal_correlation_score,
    calculate_sentinel_scores,
    calculate_alert_density_score,
    calculate_sentiment_score
)
from app.api_models import (
    InfrastructureNode, FireEvent, GLADAlert, SentinelEvidence, CombinedSentiment
)


class TestSpatialProximityScore:
    """Tests for spatial proximity calculation."""
    
    def test_close_proximity(self):
        infra = [
            InfrastructureNode(
                osm_id=1, node_type="factory", name="Test Factory",
                latitude=0.0, longitude=0.0, distance_m=100, tags={}
            )
        ]
        alerts = [
            GLADAlert(latitude=0.001, longitude=0.001, date=datetime.now(), confidence=80)
        ]
        
        score, details = calculate_spatial_proximity_score(infra, alerts, max_distance=5000)
        
        assert score > 0
        assert len(details) > 0
    
    def test_no_proximity(self):
        infra = [
            InfrastructureNode(
                osm_id=1, node_type="factory", name="Test Factory",
                latitude=0.0, longitude=0.0, distance_m=100, tags={}
            )
        ]
        alerts = [
            GLADAlert(latitude=10.0, longitude=10.0, date=datetime.now(), confidence=80)
        ]
        
        score, details = calculate_spatial_proximity_score(infra, alerts, max_distance=5000)
        
        assert score == 0
        assert len(details) == 0
    
    def test_empty_inputs(self):
        score, details = calculate_spatial_proximity_score([], [], 5000)
        assert score == 0.0
        assert details == []


class TestTemporalCorrelationScore:
    """Tests for temporal correlation calculation."""
    
    def test_correlated_events(self):
        base_time = datetime.now()
        
        fires = [
            FireEvent(
                latitude=0.0, longitude=0.0, brightness=350,
                confidence=80, frp=10.0, acquisition_time=base_time,
                satellite="MODIS", daynight="D"
            )
        ]
        alerts = [
            GLADAlert(
                latitude=0.0, longitude=0.0,
                date=base_time - timedelta(days=5),
                confidence=80
            )
        ]
        
        score, details = calculate_temporal_correlation_score(fires, alerts, window_days=14)
        
        assert score > 0
        assert len(details) > 0
        assert details[0]["days_apart"] == 5
    
    def test_uncorrelated_events(self):
        base_time = datetime.now()
        
        fires = [
            FireEvent(
                latitude=0.0, longitude=0.0, brightness=350,
                confidence=80, frp=10.0, acquisition_time=base_time,
                satellite="MODIS", daynight="D"
            )
        ]
        alerts = [
            GLADAlert(
                latitude=0.0, longitude=0.0,
                date=base_time - timedelta(days=30),  # Outside window
                confidence=80
            )
        ]
        
        score, details = calculate_temporal_correlation_score(fires, alerts, window_days=14)
        
        assert score == 0
        assert len(details) == 0


class TestSentinelScores:
    """Tests for Sentinel imagery score calculation."""
    
    def test_low_ndvi_high_score(self):
        sentinel = SentinelEvidence(ndvi=0.1, nbr=0.5, burn_index=0.1)
        scores = calculate_sentinel_scores(sentinel)
        
        assert scores["ndvi"][0] > 0.5  # Low NDVI = high concern
    
    def test_high_ndvi_low_score(self):
        sentinel = SentinelEvidence(ndvi=0.8, nbr=0.7, burn_index=0.05)
        scores = calculate_sentinel_scores(sentinel)
        
        assert scores["ndvi"][0] < 0.3  # Healthy vegetation
    
    def test_negative_nbr_indicates_burn(self):
        sentinel = SentinelEvidence(ndvi=0.3, nbr=-0.3, burn_index=0.4)
        scores = calculate_sentinel_scores(sentinel)
        
        assert scores["nbr"][0] > 0.5  # Burn damage
        assert scores["burn"][0] > 0.3  # Active burning
    
    def test_no_sentinel_data(self):
        scores = calculate_sentinel_scores(None)
        
        assert scores["ndvi"][0] == 0.0
        assert scores["nbr"][0] == 0.0
        assert scores["burn"][0] == 0.0


class TestAlertDensityScore:
    """Tests for alert density calculation."""
    
    def test_high_density(self):
        # Many alerts in small area
        bbox = (0.0, 0.0, 0.1, 0.1)  # ~100 sq km at equator
        glad = [GLADAlert(latitude=0.05, longitude=0.05, date=datetime.now()) for _ in range(100)]
        
        score, explanation = calculate_alert_density_score(glad, [], [], bbox)
        
        assert score > 0.5
        assert "high" in explanation.lower() or "density" in explanation.lower()
    
    def test_low_density(self):
        bbox = (0.0, 0.0, 1.0, 1.0)  # ~12,000 sq km at equator
        glad = [GLADAlert(latitude=0.5, longitude=0.5, date=datetime.now())]
        
        score, explanation = calculate_alert_density_score(glad, [], [], bbox)
        
        assert score < 0.3


class TestSentimentScore:
    """Tests for sentiment-based scoring."""
    
    def test_negative_sentiment_high_score(self):
        sentiment = CombinedSentiment(
            google=None, gdelt=None, reddit=None,
            final_score=-0.6, confidence=0.8, dominant_narrative="deforestation"
        )
        
        score, explanation = calculate_sentiment_score(sentiment)
        
        assert score > 0.5  # Negative sentiment = concern
    
    def test_positive_sentiment_low_score(self):
        sentiment = CombinedSentiment(
            google=None, gdelt=None, reddit=None,
            final_score=0.5, confidence=0.8, dominant_narrative="conservation"
        )
        
        score, explanation = calculate_sentiment_score(sentiment)
        
        assert score == 0.0  # Positive sentiment = no concern
    
    def test_no_sentiment(self):
        score, explanation = calculate_sentiment_score(None)
        
        assert score == 0.0
```

---

### 8. **NEW FILE: `backend/tests/test_integration.py`**

```python
"""
Integration tests for Eco-Forensics API.
Uses fixtures from tests/fixtures/ directory.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main_api import app
from app.api_models import Dossier, HealthResponse


# Test client
client = TestClient(app)

# Fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    """Load a JSON fixture file."""
    fixture_path = FIXTURES_DIR / f"{name}.json"
    if fixture_path.exists():
        with open(fixture_path) as f:
            return json.load(f)
    return {}


class TestHealthEndpoint:
    """Tests for /health endpoint."""
    
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_response_structure(self):
        response = client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert "services" in data
        assert "timestamp" in data
        assert isinstance(data["services"], list)
    
    def test_health_service_statuses(self):
        response = client.get("/health")
        data = response.json()
        
        service_names = [s["name"] for s in data["services"]]
        
        # Check all expected services are present
        expected_services = [
            "google_earth_engine",
            "global_forest_watch", 
            "sentinel_hub",
            "google_custom_search",
            "gdelt",
            "overpass_osm",
            "gleif",
            "reddit"
        ]
        
        for service in expected_services:
            assert service in service_names


class TestDossierEndpoint:
    """Tests for /dossier endpoint."""
    
    def test_dossier_requires_region_or_bbox(self):
        response = client.get("/dossier")
        assert response.status_code == 400
        assert "region" in response.json()["detail"].lower() or "bbox" in response.json()["detail"].lower()
    
    def test_dossier_invalid_region(self):
        response = client.get("/dossier?region=InvalidRegion")
        assert response.status_code == 400
        assert "unknown region" in response.json()["detail"].lower()
    
    def test_dossier_invalid_bbox_format(self):
        response = client.get("/dossier?bbox=invalid")
        assert response.status_code == 400
    
    def test_dossier_bbox_validation(self):
        # Latitude out of range
        response = client.get("/dossier?bbox=0,-100,10,10")
        assert response.status_code == 400
        
        # Longitude out of range  
        response = client.get("/dossier?bbox=-200,0,10,10")
        assert response.status_code == 400
    
    def test_dossier_valid_region(self):
        """Test with a valid region - may fail if APIs are not configured."""
        response = client.get("/dossier?region=Riau")
        
        # Should return 200 or 500 (if APIs not configured)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify response structure matches Dossier model
            assert "region" in data
            assert "bbox" in data
            assert "generated_at" in data
            assert "confidence_score" in data
            assert "source_errors" in data
            assert "coverage_notes" in data
    
    def test_dossier_response_has_required_fields(self):
        """Test dossier response contains all required fields."""
        response = client.get("/dossier?region=Riau")
        
        if response.status_code == 200:
            data = response.json()
            
            required_fields = [
                "region", "bbox", "generated_at",
                "analysis_period_start", "analysis_period_end",
                "hansen", "gfw_glad", "gfw_radd", "firms",
                "sentinel", "nearby_infra", "suspects",
                "sentiment", "evidence_chain", "confidence_score",
                "source_errors", "coverage_notes"
            ]
            
            for field in required_fields:
                assert field in data, f"Missing field: {field}"


class TestFiresEndpoint:
    """Tests for /fires endpoint."""
    
    def test_fires_requires_location(self):
        response = client.get("/fires")
        assert response.status_code == 400
    
    def test_fires_valid_region(self):
        response = client.get("/fires?region=Amazon&days=7")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "fires" in data
            assert "count" in data
            assert "bbox" in data


class TestLossEndpoint:
    """Tests for /loss endpoint."""
    
    def test_loss_requires_location(self):
        response = client.get("/loss")
        assert response.status_code == 400
    
    def test_loss_valid_region(self):
        response = client.get("/loss?region=Borneo")
        assert response.status_code in [200, 500]


class TestSentimentEndpoint:
    """Tests for /sentiment endpoint."""
    
    def test_sentiment_requires_location(self):
        response = client.get("/sentiment")
        assert response.status_code == 400
    
    def test_sentiment_valid_region(self):
        response = client.get("/sentiment?region=Riau")
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "sentiment" in data
            assert "query" in data


class TestSentinelPreviewEndpoint:
    """Tests for /sentinel/preview endpoint."""
    
    def test_preview_requires_bbox(self):
        response = client.get("/sentinel/preview")
        assert response.status_code == 422  # Missing required parameter
    
    def test_preview_valid_bbox(self):
        response = client.get("/sentinel/preview?bbox=100,-1,104,3")
        assert response.status_code in [200, 500]


class TestInternalLogsEndpoint:
    """Tests for /internal/logs endpoint."""
    
    def test_logs_accepts_valid_payload(self):
        logs = [
            {"level": "INFO", "message": "Test log message"},
            {"level": "ERROR", "message": "Test error", "context": {"page": "/home"}}
        ]
        
        response = client.post("/internal/logs", json=logs)
        
        assert response.status_code == 200
        assert response.json()["received"] == 2
    
    def test_logs_empty_array(self):
        response = client.post("/internal/logs", json=[])
        
        assert response.status_code == 200
        assert response.json()["received"] == 0
```

---

### 9. **NEW FILE: `backend/tests/fixtures/.gitkeep`**

```
# Placeholder for test fixtures
# Add real API response fixtures here for integration testing
```

---

### 10. **NEW FILE: `backend/tests/fixtures/riau_dossier.json`** (Sample fixture)

```json
{
  "region": "Riau",
  "bbox": {
    "min_lon": 100.0,
    "min_lat": -1.0,
    "max_lon": 104.0,
    "max_lat": 3.0
  },
  "generated_at": "2024-01-15T10:30:00Z",
  "analysis_period_start": "2023-10-15T00:00:00Z",
  "analysis_period_end": "2024-01-15T00:00:00Z",
  "hansen": {
    "total_loss_ha": 15420.5,
    "loss_by_year": {
      "2021": 4500.2,
      "2022": 5120.8,
      "2023": 5799.5
    },
    "tree_cover_percent": 45.2
  },
  "gfw_glad": [
    {
      "latitude": 1.234,
      "longitude": 102.456,
      "date": "2023-12-01T00:00:00Z",
      "confidence": 85
    }
  ],
  "gfw_radd": [],
  "firms": [
    {
      "latitude": 1.235,
      "longitude": 102.457,
      "brightness": 345.5,
      "confidence": 90,
      "frp": 25.3,
      "acquisition_time": "2023-12-02T14:30:00Z",
      "satellite": "VIIRS",
      "daynight": "D"
    }
  ],
  "sentinel": {
    "ndvi": 0.32,
    "nbr": 0.15,
    "burn_index": 0.28,
    "truecolor_url": null
  },
  "nearby_infra": [
    {
      "osm_id": 12345678,
      "node_type": "industrial",
      "name": "Palm Oil Mill",
      "latitude": 1.230,
      "longitude": 102.450,
      "distance_m": 1200,
      "tags": {"industrial": "palm_oil_mill"}
    }
  ],
  "suspects": [
    {
      "name": "Example Palm Oil Corp",
      "lei": "529900ABC123DEF456GH",
      "country": "ID",
      "parent_name": "Example Holdings Ltd",
      "match_score": 85.5,
      "source": "gleif"
    }
  ],
  "sentiment": {
    "google": {"count": 15, "score": -0.45, "keywords": ["deforestation", "fire"], "sample_titles": []},
    "gdelt": {"count": 32, "score": -0.38, "keywords": ["palm oil", "forest"], "sample_titles": []},
    "reddit": null,
    "final_score": -0.42,
    "confidence": 0.65,
    "dominant_narrative": "deforestation"
  },
  "evidence_chain": [
    {
      "suspect": {
        "name": "Example Palm Oil Corp",
        "lei": "529900ABC123DEF456GH",
        "country": "ID",
        "match_score": 85.5,
        "source": "gleif"
      },
      "links": [
        {
          "evidence_type": "spatial_proximity",
          "description": "Infrastructure within 5000m of 1 damage points",
          "weight": 0.15,
          "supporting_data": {"proximity_count": 1, "closest_distance_m": 1200}
        }
      ],
      "total_weight": 0.45,
      "summary": "Example Palm Oil Corp: Evidence shows spatial correlation with damage sites."
    }
  ],
  "confidence_score": 62.5,
  "source_errors": [],
  "coverage_notes": []
}
```

---

## Summary of Files

Here's the complete file structure with status:

```
backend/
├── app/
│   ├── __init__.py          # NEW (empty, needed for package)
│   ├── logger_config.py     # ✅ Part 1
│   ├── config.py            # ✅ Part 1
│   ├── api_models.py        # ✅ Part 1
│   ├── database.py          # ✅ Part 1
│   ├── utils.py             # ✅ Part 1
│   ├── satellite_intel.py   # ✅ Part 2
│   ├── suspect_profiler.py  # ✅ Part 2
│   ├── social_voice.py      # ✅ Part 3 (USE THIS VERSION)
│   ├── correlation_engine.py # ✅ Part 3
│   └── main_api.py          # ✅ Part 3
├── tests/
│   ├── __init__.py          # ✅ NEW
│   ├── test_fuzzy_match.py  # ✅ NEW
│   ├── test_sentiment.py    # ✅ NEW
│   ├── test_correlation.py  # ✅ NEW
│   ├── test_integration.py  # ✅ NEW
│   └── fixtures/
│       ├── .gitkeep         # ✅ NEW
│       └── riau_dossier.json # ✅ NEW
├── data/                    # Auto-created at runtime
├── secrets/                 # For GEE credentials
│   └── .gitkeep            # NEW (keep dir in git)
├── Dockerfile              # ✅ Part 3
├── docker-compose.yml      # ✅ Part 3
├── requirements.txt        # ✅ Part 3
├── .env.example           # ✅ Part 3
├── README.md              # ✅ COMPLETED above
└── runbook.md             # ✅ NEW
```

### Final file to add: `backend/app/__init__.py`

```python
"""Eco-Forensics Backend Application."""
```

### And: `backend/secrets/.gitkeep`

```
# Place gee.json service account credentials here
```