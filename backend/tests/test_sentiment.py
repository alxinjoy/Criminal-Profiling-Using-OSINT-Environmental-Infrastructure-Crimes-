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