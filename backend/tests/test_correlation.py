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