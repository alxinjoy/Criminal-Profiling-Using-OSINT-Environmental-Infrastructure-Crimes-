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