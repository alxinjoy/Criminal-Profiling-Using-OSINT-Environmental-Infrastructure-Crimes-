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