"""
Pydantic models for API request/response validation.
Defines the contract for all data structures used in the Eco-Forensics API.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


# ============== Error Models ==============

class SourceError(BaseModel):
    """
    Standardized error from a data source.
    Used across all endpoints for consistent error reporting.
    """
    source: str = Field(..., description="Service name that produced the error")
    error_type: str = Field(..., description="Exception class name")
    message: str = Field(..., description="Human-readable error message")
    retryable: bool = Field(..., description="Whether the request can be retried")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============== Satellite/Evidence Models ==============

class SentinelEvidence(BaseModel):
    """Evidence derived from Sentinel Hub imagery."""
    ndvi: Optional[float] = Field(None, description="Normalized Difference Vegetation Index (-1 to 1)")
    ndvi_change: Optional[float] = Field(None, description="NDVI change from baseline")
    nbr: Optional[float] = Field(None, description="Normalized Burn Ratio")
    nbr_change: Optional[float] = Field(None, description="NBR change (negative = burn damage)")
    burn_index: Optional[float] = Field(None, description="Burn severity index")
    truecolor_url: Optional[str] = Field(None, description="URL to true-color preview image")
    acquisition_date: Optional[datetime] = None
    cloud_coverage: Optional[float] = Field(None, ge=0, le=100)
    
    @validator('ndvi', 'nbr')
    def validate_index_range(cls, v):
        if v is not None and not -1 <= v <= 1:
            raise ValueError("Index must be between -1 and 1")
        return v


class FireEvent(BaseModel):
    """Active fire detection from FIRMS."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    brightness: Optional[float] = Field(None, description="Fire brightness temperature (Kelvin)")
    confidence: Optional[int] = Field(None, ge=0, le=100, description="Detection confidence %")
    frp: Optional[float] = Field(None, description="Fire Radiative Power (MW)")
    acquisition_time: datetime
    satellite: str = Field(..., description="MODIS, VIIRS, etc.")
    daynight: Optional[str] = Field(None, description="D=day, N=night")


class GLADAlert(BaseModel):
    """GLAD deforestation alert."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    date: datetime
    confidence: Optional[int] = Field(None, ge=0, le=100)
    area_ha: Optional[float] = Field(None, ge=0, description="Affected area in hectares")
    
    
class RADDAlert(BaseModel):
    """RADD radar-based deforestation alert."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    date: datetime
    confidence: Optional[str] = Field(None, description="high/nominal/low")
    area_ha: Optional[float] = Field(None, ge=0)


class HansenStats(BaseModel):
    """Hansen Global Forest Change statistics for a region."""
    total_loss_ha: float = Field(..., ge=0, description="Total forest loss in hectares")
    loss_by_year: Dict[int, float] = Field(default_factory=dict, description="Loss per year")
    tree_cover_2000_ha: Optional[float] = Field(None, ge=0)
    tree_cover_percent: Optional[float] = Field(None, ge=0, le=100)


# ============== Infrastructure/Company Models ==============

class InfrastructureNode(BaseModel):
    """Infrastructure element from OpenStreetMap."""
    osm_id: int
    node_type: str = Field(..., description="factory, industrial, mine, etc.")
    name: Optional[str] = None
    latitude: float
    longitude: float
    distance_m: Optional[float] = Field(None, description="Distance from AOI centroid")
    tags: Dict[str, str] = Field(default_factory=dict)


class Company(BaseModel):
    """Company/legal entity information."""
    name: str
    lei: Optional[str] = Field(None, description="Legal Entity Identifier")
    country: Optional[str] = None
    jurisdiction: Optional[str] = None
    parent_name: Optional[str] = None
    parent_lei: Optional[str] = None
    status: Optional[str] = Field(None, description="active/inactive")
    match_score: Optional[float] = Field(None, ge=0, le=100, description="Fuzzy match confidence")
    source: str = Field(default="gleif")


# ============== Sentiment Models ==============

class SentimentScore(BaseModel):
    """Sentiment analysis result from a single source."""
    count: int = Field(..., ge=0, description="Number of articles/posts analyzed")
    score: float = Field(..., ge=-1, le=1, description="Sentiment score (-1=negative, 1=positive)")
    keywords: List[str] = Field(default_factory=list)
    sample_titles: List[str] = Field(default_factory=list, max_items=5)


class CombinedSentiment(BaseModel):
    """Combined sentiment from all sources."""
    google: Optional[SentimentScore] = None
    gdelt: Optional[SentimentScore] = None
    reddit: Optional[SentimentScore] = None
    final_score: float = Field(..., ge=-1, le=1, description="Weighted combined score")
    confidence: float = Field(..., ge=0, le=1, description="Confidence based on sample size")
    dominant_narrative: Optional[str] = Field(None, description="Key theme detected")


# ============== Evidence Chain Models ==============

class EvidenceLink(BaseModel):
    """A single piece of evidence linking damage to an entity."""
    evidence_type: str = Field(..., description="spatial_proximity, temporal_correlation, sentinel_signal, etc.")
    description: str
    weight: float = Field(..., ge=0, le=1, description="How much this contributes to confidence")
    supporting_data: Dict[str, Any] = Field(default_factory=dict)


class EvidenceChain(BaseModel):
    """Complete chain of evidence for a suspect."""
    suspect: Company
    links: List[EvidenceLink] = Field(default_factory=list)
    total_weight: float = Field(..., ge=0)
    summary: str = Field(..., description="Human-readable evidence summary")


# ============== Main Dossier Model ==============

class BBox(BaseModel):
    """Bounding box in EPSG:4326."""
    min_lon: float = Field(..., ge=-180, le=180)
    min_lat: float = Field(..., ge=-90, le=90)
    max_lon: float = Field(..., ge=-180, le=180)
    max_lat: float = Field(..., ge=-90, le=90)
    
    @validator('max_lon')
    def validate_lon_order(cls, v, values):
        if 'min_lon' in values and v < values['min_lon']:
            raise ValueError("max_lon must be >= min_lon")
        return v
    
    @validator('max_lat')
    def validate_lat_order(cls, v, values):
        if 'min_lat' in values and v < values['min_lat']:
            raise ValueError("max_lat must be >= min_lat")
        return v
    
    def to_tuple(self) -> tuple:
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)
    
    @classmethod
    def from_tuple(cls, t: tuple) -> 'BBox':
        return cls(min_lon=t[0], min_lat=t[1], max_lon=t[2], max_lat=t[3])
    
    def area_sq_degrees(self) -> float:
        return (self.max_lon - self.min_lon) * (self.max_lat - self.min_lat)


class CoverageNote(BaseModel):
    """Note about dataset coverage limitations."""
    dataset: str
    status: str = Field(..., description="available, skipped, partial")
    reason: Optional[str] = None


class Dossier(BaseModel):
    """
    Complete forensic dossier for a region.
    This is the main response model for the /dossier endpoint.
    """
    # Metadata
    region: Optional[str] = Field(None, description="Named region if applicable")
    bbox: BBox
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    analysis_period_start: datetime
    analysis_period_end: datetime
    
    # Satellite data
    hansen: Optional[HansenStats] = None
    gfw_glad: List[GLADAlert] = Field(default_factory=list)
    gfw_radd: List[RADDAlert] = Field(default_factory=list)
    firms: List[FireEvent] = Field(default_factory=list)
    sentinel: Optional[SentinelEvidence] = None
    
    # Infrastructure and suspects
    nearby_infra: List[InfrastructureNode] = Field(default_factory=list)
    suspects: List[Company] = Field(default_factory=list)
    
    # Sentiment analysis
    sentiment: Optional[CombinedSentiment] = None
    
    # Correlation results
    evidence_chain: List[EvidenceChain] = Field(default_factory=list)
    confidence_score: float = Field(..., ge=0, le=100, description="Overall confidence 0-100")
    
    # Error and coverage tracking
    source_errors: List[SourceError] = Field(default_factory=list)
    coverage_notes: List[CoverageNote] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============== Request Models ==============

class DossierRequest(BaseModel):
    """Request parameters for dossier generation."""
    region: Optional[str] = Field(None, description="Named region from GLOBAL_REGIONS")
    bbox: Optional[str] = Field(None, description="Custom bbox as 'minLon,minLat,maxLon,maxLat'")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    @validator('bbox')
    def parse_bbox(cls, v):
        if v is None:
            return None
        try:
            parts = [float(x.strip()) for x in v.split(',')]
            if len(parts) != 4:
                raise ValueError("bbox must have 4 components")
            return v
        except Exception as e:
            raise ValueError(f"Invalid bbox format: {e}")


# ============== Health Check Models ==============

class ServiceStatus(BaseModel):
    """Health status for a single service."""
    name: str
    status: str = Field(..., description="healthy, degraded, unhealthy, unknown")
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    last_checked: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Response for /health endpoint."""
    status: str = Field(..., description="healthy, degraded, unhealthy")
    services: List[ServiceStatus] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)