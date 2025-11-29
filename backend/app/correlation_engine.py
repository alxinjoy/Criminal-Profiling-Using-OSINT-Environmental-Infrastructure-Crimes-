"""
Correlation engine for linking environmental damage to corporate entities.

Creates evidence chains by analyzing:
- Spatial proximity (infrastructure within 5km of damage)
- Temporal correlation (fires within 14 days of detected loss)
- Sentinel signals (NDVI drop, NBR drop, burn index)
- Sentiment negativity (increases confidence)

Outputs human-readable evidence_chain and numeric confidence_score (0-100).
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from .config import settings, GLOBAL_REGIONS, is_region_covered
from .logger_config import get_logger
from .api_models import (
    Dossier, BBox, HansenStats, GLADAlert, RADDAlert, FireEvent,
    SentinelEvidence, InfrastructureNode, Company, CombinedSentiment,
    EvidenceLink, EvidenceChain, CoverageNote, SourceError
)
from .utils import haversine_distance, bbox_centroid

logger = get_logger("correlation_engine")


# ============== Correlation Parameters ==============

# Maximum distance (meters) to consider infrastructure "nearby"
MAX_PROXIMITY_DISTANCE_M = 5000

# Time window for temporal correlation (days)
TEMPORAL_WINDOW_DAYS = 14

# NDVI drop threshold to consider significant vegetation loss
NDVI_DROP_THRESHOLD = -0.15

# NBR drop threshold to consider significant burn damage
NBR_DROP_THRESHOLD = -0.2

# Burn index threshold for active burning
BURN_INDEX_THRESHOLD = 0.3

# Minimum alerts to establish pattern
MIN_ALERTS_FOR_PATTERN = 3

# Weights for confidence calculation
WEIGHTS = {
    "spatial_proximity": 0.25,
    "temporal_correlation": 0.20,
    "sentinel_ndvi": 0.15,
    "sentinel_nbr": 0.10,
    "sentinel_burn": 0.10,
    "alert_density": 0.10,
    "sentiment_negative": 0.10,
}


@dataclass
class CorrelationResult:
    """Result of correlation analysis for a single suspect."""
    suspect: Company
    evidence_links: List[EvidenceLink]
    total_weight: float
    confidence_score: float
    summary: str


def calculate_spatial_proximity_score(
    infrastructure: List[InfrastructureNode],
    alerts: List[Any],  # GLAD, RADD, or Fire alerts
    max_distance: float = MAX_PROXIMITY_DISTANCE_M
) -> Tuple[float, List[Dict]]:
    """
    Calculate spatial proximity between infrastructure and alerts.
    
    Returns:
        (score 0-1, list of proximity details)
    """
    if not infrastructure or not alerts:
        return 0.0, []
    
    proximity_details = []
    close_count = 0
    
    for node in infrastructure:
        for alert in alerts:
            # Get alert coordinates
            if hasattr(alert, 'latitude'):
                alert_lat = alert.latitude
                alert_lon = alert.longitude
            else:
                continue
            
            distance = haversine_distance(
                node.latitude, node.longitude,
                alert_lat, alert_lon
            )
            
            if distance <= max_distance:
                close_count += 1
                proximity_details.append({
                    "infrastructure": node.name or f"OSM:{node.osm_id}",
                    "infrastructure_type": node.node_type,
                    "distance_m": round(distance, 1),
                    "alert_type": type(alert).__name__
                })
    
    # Score based on number of close proximities (diminishing returns)
    if close_count == 0:
        score = 0.0
    elif close_count < 5:
        score = close_count * 0.15
    elif close_count < 10:
        score = 0.6 + (close_count - 5) * 0.05
    else:
        score = min(1.0, 0.85 + (close_count - 10) * 0.01)
    
    return score, proximity_details


def calculate_temporal_correlation_score(
    fires: List[FireEvent],
    deforestation_alerts: List[Any],  # GLAD or RADD
    window_days: int = TEMPORAL_WINDOW_DAYS
) -> Tuple[float, List[Dict]]:
    """
    Calculate temporal correlation between fires and deforestation.
    
    Fires occurring within window_days of deforestation alerts suggest
    slash-and-burn clearing patterns.
    """
    if not fires or not deforestation_alerts:
        return 0.0, []
    
    correlations = []
    
    for fire in fires:
        fire_time = fire.acquisition_time
        
        for alert in deforestation_alerts:
            alert_time = alert.date if hasattr(alert, 'date') else None
            if not alert_time:
                continue
            
            # Check if fire is within window of alert
            time_diff = abs((fire_time - alert_time).days)
            
            if time_diff <= window_days:
                # Closer in time = stronger correlation
                strength = 1.0 - (time_diff / window_days)
                correlations.append({
                    "fire_date": fire_time.isoformat(),
                    "alert_date": alert_time.isoformat(),
                    "days_apart": time_diff,
                    "correlation_strength": round(strength, 2)
                })
    
    if not correlations:
        return 0.0, []
    
    # Average correlation strength
    avg_strength = sum(c["correlation_strength"] for c in correlations) / len(correlations)
    
    # Bonus for multiple correlations
    count_bonus = min(0.3, len(correlations) * 0.05)
    
    score = min(1.0, avg_strength + count_bonus)
    
    return score, correlations


def calculate_sentinel_scores(
    sentinel: Optional[SentinelEvidence]
) -> Dict[str, Tuple[float, str]]:
    """
    Calculate scores from Sentinel imagery analysis.
    
    Returns dict of {metric: (score, explanation)}
    """
    scores = {}
    
    if not sentinel:
        return {
            "ndvi": (0.0, "No Sentinel data available"),
            "nbr": (0.0, "No Sentinel data available"),
            "burn": (0.0, "No Sentinel data available")
        }
    
    # NDVI analysis
    if sentinel.ndvi is not None:
        if sentinel.ndvi < 0.2:
            # Very low NDVI indicates severe vegetation loss
            ndvi_score = 0.8 + (0.2 - sentinel.ndvi) * 0.5
            explanation = f"Very low NDVI ({sentinel.ndvi:.2f}) indicates severe vegetation loss"
        elif sentinel.ndvi < 0.4:
            ndvi_score = 0.4 + (0.4 - sentinel.ndvi) * 1.0
            explanation = f"Low NDVI ({sentinel.ndvi:.2f}) indicates vegetation stress/loss"
        else:
            ndvi_score = max(0, 0.4 - (sentinel.ndvi - 0.4) * 0.5)
            explanation = f"NDVI ({sentinel.ndvi:.2f}) indicates vegetation present"
        
        scores["ndvi"] = (min(1.0, ndvi_score), explanation)
    else:
        scores["ndvi"] = (0.0, "NDVI data not available")
    
    # NBR analysis (Normalized Burn Ratio)
    if sentinel.nbr is not None:
        if sentinel.nbr < -0.1:
            # Negative NBR indicates burn damage
            nbr_score = 0.6 + abs(sentinel.nbr) * 0.8
            explanation = f"Negative NBR ({sentinel.nbr:.2f}) indicates burn damage"
        elif sentinel.nbr < 0.1:
            nbr_score = 0.3
            explanation = f"Low NBR ({sentinel.nbr:.2f}) suggests possible damage"
        else:
            nbr_score = 0.0
            explanation = f"NBR ({sentinel.nbr:.2f}) indicates healthy vegetation"
        
        scores["nbr"] = (min(1.0, nbr_score), explanation)
    else:
        scores["nbr"] = (0.0, "NBR data not available")
    
    # Burn index analysis
    if sentinel.burn_index is not None:
        if sentinel.burn_index > BURN_INDEX_THRESHOLD:
            burn_score = min(1.0, sentinel.burn_index * 1.5)
            explanation = f"High burn index ({sentinel.burn_index:.2f}) indicates active/recent burning"
        elif sentinel.burn_index > 0.15:
            burn_score = sentinel.burn_index * 2
            explanation = f"Elevated burn index ({sentinel.burn_index:.2f})"
        else:
            burn_score = 0.0
            explanation = f"Low burn index ({sentinel.burn_index:.2f})"
        
        scores["burn"] = (burn_score, explanation)
    else:
        scores["burn"] = (0.0, "Burn index not available")
    
    return scores


def calculate_alert_density_score(
    glad_alerts: List[GLADAlert],
    radd_alerts: List[RADDAlert],
    fires: List[FireEvent],
    bbox: tuple
) -> Tuple[float, str]:
    """
    Calculate alert density score based on concentration of alerts.
    """
    total_alerts = len(glad_alerts) + len(radd_alerts) + len(fires)
    
    if total_alerts == 0:
        return 0.0, "No alerts detected in region"
    
    # Calculate area in sq km (approximate)
    min_lon, min_lat, max_lon, max_lat = bbox
    # 1 degree ≈ 111 km at equator
    width_km = (max_lon - min_lon) * 111 * abs(cos_deg((min_lat + max_lat) / 2))
    height_km = (max_lat - min_lat) * 111
    area_sq_km = width_km * height_km
    
    if area_sq_km <= 0:
        return 0.0, "Invalid area"
    
    # Alerts per 100 sq km
    density = (total_alerts / area_sq_km) * 100
    
    if density > 50:
        score = 1.0
        explanation = f"Very high alert density: {density:.1f} per 100 sq km"
    elif density > 20:
        score = 0.7 + (density - 20) * 0.01
        explanation = f"High alert density: {density:.1f} per 100 sq km"
    elif density > 5:
        score = 0.3 + (density - 5) * 0.027
        explanation = f"Moderate alert density: {density:.1f} per 100 sq km"
    else:
        score = density * 0.06
        explanation = f"Low alert density: {density:.1f} per 100 sq km"
    
    return min(1.0, score), explanation


def cos_deg(degrees: float) -> float:
    """Cosine of angle in degrees."""
    import math
    return math.cos(math.radians(degrees))


def calculate_sentiment_score(sentiment: Optional[CombinedSentiment]) -> Tuple[float, str]:
    """
    Calculate score based on negative sentiment.
    More negative sentiment = higher concern = higher score.
    """
    if not sentiment:
        return 0.0, "No sentiment data available"
    
    # Convert sentiment (-1 to 1) to score (0 to 1)
    # Negative sentiment contributes to evidence
    if sentiment.final_score < -0.3:
        score = 0.8 + abs(sentiment.final_score + 0.3) * 0.3
        explanation = f"Strongly negative media sentiment ({sentiment.final_score:.2f})"
    elif sentiment.final_score < 0:
        score = 0.4 + abs(sentiment.final_score) * 1.3
        explanation = f"Negative media sentiment ({sentiment.final_score:.2f})"
    elif sentiment.final_score < 0.2:
        score = 0.2
        explanation = f"Neutral media sentiment ({sentiment.final_score:.2f})"
    else:
        score = 0.0
        explanation = f"Positive media sentiment ({sentiment.final_score:.2f})"
    
    # Adjust by confidence
    score *= sentiment.confidence
    
    if sentiment.dominant_narrative:
        explanation += f"; dominant theme: {sentiment.dominant_narrative}"
    
    return min(1.0, score), explanation


def build_evidence_chain(
    suspect: Company,
    spatial_score: float,
    spatial_details: List[Dict],
    temporal_score: float,
    temporal_details: List[Dict],
    sentinel_scores: Dict[str, Tuple[float, str]],
    density_score: float,
    density_explanation: str,
    sentiment_score: float,
    sentiment_explanation: str
) -> EvidenceChain:
    """
    Build a complete evidence chain for a suspect.
    """
    links = []
    
    # Spatial proximity evidence
    if spatial_score > 0:
        closest = min(spatial_details, key=lambda x: x["distance_m"]) if spatial_details else {}
        links.append(EvidenceLink(
            evidence_type="spatial_proximity",
            description=f"Infrastructure within {MAX_PROXIMITY_DISTANCE_M}m of {len(spatial_details)} damage points",
            weight=spatial_score * WEIGHTS["spatial_proximity"],
            supporting_data={
                "proximity_count": len(spatial_details),
                "closest_distance_m": closest.get("distance_m"),
                "closest_type": closest.get("infrastructure_type")
            }
        ))
    
    # Temporal correlation evidence
    if temporal_score > 0:
        links.append(EvidenceLink(
            evidence_type="temporal_correlation",
            description=f"Fire events correlated with deforestation alerts ({len(temporal_details)} matches within {TEMPORAL_WINDOW_DAYS} days)",
            weight=temporal_score * WEIGHTS["temporal_correlation"],
            supporting_data={
                "correlation_count": len(temporal_details),
                "avg_days_apart": sum(t["days_apart"] for t in temporal_details) / len(temporal_details) if temporal_details else 0
            }
        ))
    
    # Sentinel evidence
    ndvi_score, ndvi_exp = sentinel_scores.get("ndvi", (0, ""))
    if ndvi_score > 0:
        links.append(EvidenceLink(
            evidence_type="sentinel_ndvi",
            description=ndvi_exp,
            weight=ndvi_score * WEIGHTS["sentinel_ndvi"],
            supporting_data={"score": ndvi_score}
        ))
    
    nbr_score, nbr_exp = sentinel_scores.get("nbr", (0, ""))
    if nbr_score > 0:
        links.append(EvidenceLink(
            evidence_type="sentinel_nbr",
            description=nbr_exp,
            weight=nbr_score * WEIGHTS["sentinel_nbr"],
            supporting_data={"score": nbr_score}
        ))
    
    burn_score, burn_exp = sentinel_scores.get("burn", (0, ""))
    if burn_score > 0:
        links.append(EvidenceLink(
            evidence_type="sentinel_burn",
            description=burn_exp,
            weight=burn_score * WEIGHTS["sentinel_burn"],
            supporting_data={"score": burn_score}
        ))
    
    # Alert density
    if density_score > 0:
        links.append(EvidenceLink(
            evidence_type="alert_density",
            description=density_explanation,
            weight=density_score * WEIGHTS["alert_density"],
            supporting_data={"score": density_score}
        ))
    
    # Sentiment
    if sentiment_score > 0:
        links.append(EvidenceLink(
            evidence_type="sentiment_negative",
            description=sentiment_explanation,
            weight=sentiment_score * WEIGHTS["sentiment_negative"],
            supporting_data={"score": sentiment_score}
        ))
    
    # Calculate total weight
    total_weight = sum(link.weight for link in links)
    
    # Build summary
    summary_parts = []
    if spatial_score > 0.5:
        summary_parts.append("strong spatial correlation with damage sites")
    if temporal_score > 0.5:
        summary_parts.append("temporal pattern of fires preceding deforestation")
    if ndvi_score > 0.5:
        summary_parts.append("satellite imagery confirms vegetation loss")
    if sentiment_score > 0.5:
        summary_parts.append("negative media coverage")
    
    if summary_parts:
        summary = f"{suspect.name}: Evidence shows {', '.join(summary_parts)}."
    else:
        summary = f"{suspect.name}: Limited evidence found for direct involvement."
    
    return EvidenceChain(
        suspect=suspect,
        links=links,
        total_weight=round(total_weight, 3),
        summary=summary
    )


async def correlate_events(
    aoi: tuple,
    timeframe: Tuple[datetime, datetime],
    hansen: Optional[HansenStats],
    glad_alerts: List[GLADAlert],
    radd_alerts: List[RADDAlert],
    fires: List[FireEvent],
    sentinel: Optional[SentinelEvidence],
    infrastructure: List[InfrastructureNode],
    suspects: List[Company],
    sentiment: Optional[CombinedSentiment]
) -> Tuple[List[EvidenceChain], float]:
    """
    Main correlation function that creates evidence links.
    
    Args:
        aoi: Bounding box
        timeframe: Analysis period
        hansen: Hansen forest loss statistics
        glad_alerts: GLAD deforestation alerts
        radd_alerts: RADD alerts
        fires: Fire events
        sentinel: Sentinel imagery evidence
        infrastructure: Nearby infrastructure
        suspects: Enriched company data
        sentiment: Combined sentiment analysis
    
    Returns:
        (list of EvidenceChain, overall confidence score 0-100)
    """
    logger.info(f"Starting correlation analysis for bbox={aoi}")
    
    # Combine all deforestation alerts
    all_deforestation = glad_alerts + radd_alerts
    
    # Calculate base scores (not suspect-specific)
    spatial_score, spatial_details = calculate_spatial_proximity_score(
        infrastructure, all_deforestation + fires
    )
    
    temporal_score, temporal_details = calculate_temporal_correlation_score(
        fires, all_deforestation
    )
    
    sentinel_scores = calculate_sentinel_scores(sentinel)
    
    density_score, density_explanation = calculate_alert_density_score(
        glad_alerts, radd_alerts, fires, aoi
    )
    
    sentiment_score, sentiment_explanation = calculate_sentiment_score(sentiment)
    
    # Build evidence chains for each suspect
    evidence_chains = []
    
    for suspect in suspects:
        # Filter spatial details for this suspect's infrastructure
        suspect_infra = [n for n in infrastructure if 
                        n.name == suspect.name or 
                        n.tags.get("operator") == suspect.name or
                        n.tags.get("company") == suspect.name]
        
        if suspect_infra:
            suspect_spatial, suspect_spatial_details = calculate_spatial_proximity_score(
                suspect_infra, all_deforestation + fires
            )
        else:
            # Use general spatial score if no specific infrastructure
            suspect_spatial = spatial_score * 0.5  # Reduced weight
            suspect_spatial_details = spatial_details
        
        chain = build_evidence_chain(
            suspect=suspect,
            spatial_score=suspect_spatial,
            spatial_details=suspect_spatial_details,
            temporal_score=temporal_score,
            temporal_details=temporal_details,
            sentinel_scores=sentinel_scores,
            density_score=density_score,
            density_explanation=density_explanation,
            sentiment_score=sentiment_score,
            sentiment_explanation=sentiment_explanation
        )
        
        evidence_chains.append(chain)
    
    # Sort by total weight
    evidence_chains.sort(key=lambda x: x.total_weight, reverse=True)
    
    # Calculate overall confidence score (0-100)
    # Based on amount and quality of evidence
    base_confidence = 0.0
    
    # Evidence from multiple sources increases confidence
    evidence_sources = 0
    if glad_alerts or radd_alerts:
        evidence_sources += 1
        base_confidence += 15
    if fires:
        evidence_sources += 1
        base_confidence += 10
    if sentinel and (sentinel.ndvi or sentinel.nbr):
        evidence_sources += 1
        base_confidence += 15
    if hansen and hansen.total_loss_ha > 0:
        evidence_sources += 1
        base_confidence += 10
    if infrastructure:
        evidence_sources += 1
        base_confidence += 10
    if sentiment:
        evidence_sources += 1
        base_confidence += 5
    
    # Add weighted scores
    base_confidence += spatial_score * 15
    base_confidence += temporal_score * 10
    base_confidence += density_score * 10
    
    # Sentinel indicators
    for metric, (score, _) in sentinel_scores.items():
        base_confidence += score * 5
    
    # Cap at 100
    confidence_score = min(100, base_confidence)
    
    logger.info(f"Correlation complete: {len(evidence_chains)} suspects analyzed, confidence={confidence_score:.1f}")
    
    return evidence_chains, round(confidence_score, 1)