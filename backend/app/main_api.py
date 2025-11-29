"""
FastAPI main application for Eco-Forensics backend.

Endpoints:
- GET /health - Service health check
- GET /dossier - Generate forensic dossier
- GET /fires - Fire data only
- GET /loss - Forest loss data only
- GET /sentiment - Sentiment analysis only
- GET /sentinel/preview - Sentinel imagery preview
- POST /internal/logs - Accept client logs
"""

import asyncio
import time
import traceback
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Query, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings, GLOBAL_REGIONS, is_region_covered, DATASET_COVERAGE
from .logger_config import get_logger, configure_root_logger
from .database import create_tables, get_session, DossierRecord, RequestLog
from .api_models import (
    Dossier, BBox, HealthResponse, ServiceStatus, SourceError,
    CoverageNote, HansenStats, FireEvent, GLADAlert, RADDAlert,
    SentinelEvidence, CombinedSentiment, Company, InfrastructureNode
)
from .utils import validate_bbox, parse_bbox_string, create_source_error
from .satellite_intel import (
    fetch_hansen_stats, fetch_firms, fetch_glad_alerts, fetch_radd_alerts,
    fetch_sentinel_evidence, check_gee_health, check_gfw_health, check_sentinelhub_health
)
from .suspect_profiler import (
    identify_nearby_infrastructure, enrich_infrastructure_companies,
    check_overpass_health, check_gleif_health
)
from .social_voice import (
    fetch_all_sentiment, check_google_health, check_gdelt_health, check_reddit_health
)
from .correlation_engine import correlate_events

# Configure logging
configure_root_logger()
logger = get_logger("main_api")

# Create FastAPI app
app = FastAPI(
    title="Eco-Forensics API",
    description="Forensic analysis linking environmental damage to corporate entities",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Middleware ==============

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with method, path, latency, and status."""
    start_time = time.time()
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Process request
    try:
        response = await call_next(request)
        status_code = response.status_code
        error_msg = None
    except Exception as e:
        status_code = 500
        error_msg = str(e)
        raise
    finally:
        latency_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"{request.method} {request.url.path} - "
            f"client={client_ip} status={status_code} latency={latency_ms:.2f}ms"
        )
    
    return response


# ============== Startup/Shutdown ==============

@app.on_event("startup")
async def startup_event():
    """Initialize database and log startup."""
    logger.info("Starting Eco-Forensics API...")
    await create_tables()
    
    # Log configuration warnings
    warnings = settings.validate()
    for w in warnings:
        logger.warning(f"Config warning: {w}")
    
    logger.info("Eco-Forensics API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown."""
    logger.info("Shutting down Eco-Forensics API...")


# ============== Health Check ==============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Comprehensive health check for all services.
    
    Tests: GEE auth, GFW reachability, Sentinel Hub auth, 
    Google Search quota, GDELT access, Overpass latency, 
    GLEIF access, Reddit API status.
    """
    logger.info("Performing health check...")
    services = []
    
    # GEE
    start = time.time()
    gee_ok, gee_err = await check_gee_health()
    services.append(ServiceStatus(
        name="google_earth_engine",
        status="healthy" if gee_ok else "unhealthy",
        latency_ms=(time.time() - start) * 1000,
        message=gee_err
    ))
    
    # GFW
    start = time.time()
    gfw_ok, gfw_err = await check_gfw_health()
    services.append(ServiceStatus(
        name="global_forest_watch",
        status="healthy" if gfw_ok else "unhealthy",
        latency_ms=(time.time() - start) * 1000,
        message=gfw_err
    ))
    
    # Sentinel Hub
    start = time.time()
    sentinel_ok, sentinel_err = await check_sentinelhub_health()
    services.append(ServiceStatus(
        name="sentinel_hub",
        status="healthy" if sentinel_ok else "unhealthy",
        latency_ms=(time.time() - start) * 1000,
        message=sentinel_err
    ))
    
    # Google CSE
    start = time.time()
    google_ok, google_err = await check_google_health()
    services.append(ServiceStatus(
        name="google_custom_search",
        status="healthy" if google_ok else ("degraded" if google_err == "Quota exceeded" else "unhealthy"),
        latency_ms=(time.time() - start) * 1000,
        message=google_err
    ))
    
    # GDELT
    start = time.time()
    gdelt_ok, gdelt_err = await check_gdelt_health()
    services.append(ServiceStatus(
        name="gdelt",
        status="healthy" if gdelt_ok else "unhealthy",
        latency_ms=(time.time() - start) * 1000,
        message=gdelt_err
    ))
    
    # Overpass
    start = time.time()
    overpass_ok, overpass_err, overpass_latency = await check_overpass_health()
    services.append(ServiceStatus(
        name="overpass_osm",
        status="healthy" if overpass_ok else "unhealthy",
        latency_ms=overpass_latency or (time.time() - start) * 1000,
        message=overpass_err
    ))
    
    # GLEIF
    start = time.time()
    gleif_ok, gleif_err = await check_gleif_health()
    services.append(ServiceStatus(
        name="gleif",
        status="healthy" if gleif_ok else "unhealthy",
        latency_ms=(time.time() - start) * 1000,
        message=gleif_err
    ))
    
    # Reddit
    start = time.time()
    reddit_ok, reddit_err = await check_reddit_health()
    services.append(ServiceStatus(
        name="reddit",
        status="healthy" if reddit_ok else ("degraded" if "Not configured" in str(reddit_err) else "unhealthy"),
        latency_ms=(time.time() - start) * 1000,
        message=reddit_err if not reddit_ok else "API access may require developer approval"
    ))
    
    # Overall status
    unhealthy_count = sum(1 for s in services if s.status == "unhealthy")
    degraded_count = sum(1 for s in services if s.status == "degraded")
    
    if unhealthy_count > 2:
        overall_status = "unhealthy"
    elif unhealthy_count > 0 or degraded_count > 0:
        overall_status = "degraded"
    else:
        overall_status = "healthy"
    
    return HealthResponse(
        status=overall_status,
        services=services,
        timestamp=datetime.utcnow()
    )


# ============== Helper Functions ==============

def resolve_bbox(region: Optional[str], bbox_str: Optional[str]) -> tuple:
    """Resolve bbox from region name or bbox string."""
    if region:
        region_lower = region.lower().replace(" ", "_")
        if region_lower not in GLOBAL_REGIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown region: {region}. Available: {list(GLOBAL_REGIONS.keys())}"
            )
        return GLOBAL_REGIONS[region_lower].bbox
    
    if bbox_str:
        try:
            bbox = parse_bbox_string(bbox_str)
            valid, error = validate_bbox(bbox)
            if not valid:
                raise HTTPException(status_code=400, detail=error)
            return bbox
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    raise HTTPException(status_code=400, detail="Either 'region' or 'bbox' parameter required")


def build_search_query(region: Optional[str], bbox: tuple) -> str:
    """Build a search query for sentiment analysis."""
    if region:
        region_config = GLOBAL_REGIONS.get(region.lower().replace(" ", "_"))
        if region_config:
            return f"deforestation {region_config.name} forest fire"
    
    # Generic query based on coordinates
    center_lon = (bbox[0] + bbox[2]) / 2
    center_lat = (bbox[1] + bbox[3]) / 2
    return f"deforestation forest fire {center_lat:.1f} {center_lon:.1f}"


# ============== Main Dossier Endpoint ==============

@app.get("/dossier", response_model=Dossier)
async def get_dossier(
    region: Optional[str] = Query(None, description="Named region (e.g., 'Riau', 'Amazon')"),
    bbox: Optional[str] = Query(None, description="Custom bbox: minLon,minLat,maxLon,maxLat"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Generate a complete forensic dossier for a region.
    
    Compiles cross-validated data from satellite imagery, deforestation alerts,
    fire detections, infrastructure mapping, company enrichment, and sentiment analysis.
    """
    logger.info(f"Dossier request: region={region}, bbox={bbox}")
    start_time = datetime.utcnow()
    
    try:
        # Resolve bounding box
        aoi = resolve_bbox(region, bbox)
        bbox_model = BBox.from_tuple(aoi)
        
        # Parse dates
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
        else:
            end_dt = datetime.utcnow()
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
        else:
            start_dt = end_dt - timedelta(days=90)
        
        timeframe = (start_dt, end_dt)
        
        source_errors: List[SourceError] = []
        coverage_notes: List[CoverageNote] = []
        
        # ===== Parallel Data Fetching =====
        logger.info("Starting parallel data fetch...")
        
        # Phase 1: Satellite and alert data (parallel)
        hansen_task = fetch_hansen_stats(aoi, years=list(range(start_dt.year, end_dt.year + 1)))
        firms_task = fetch_firms(aoi, timeframe)
        glad_task = fetch_glad_alerts(aoi, timeframe)
        radd_task = fetch_radd_alerts(aoi, timeframe)
        sentinel_task = fetch_sentinel_evidence(aoi, end_dt)
        infra_task = identify_nearby_infrastructure(aoi, radius_m=5000)
        
        results = await asyncio.gather(
            hansen_task, firms_task, glad_task, radd_task, sentinel_task, infra_task,
            return_exceptions=True
        )
        
        hansen_result, firms_result, glad_result, radd_result, sentinel_result, infra_result = results
        
        # Process Hansen result
        hansen: Optional[HansenStats] = None
        if isinstance(hansen_result, Exception):
            source_errors.append(create_source_error("hansen_gfc", hansen_result, retryable=True))
        elif hansen_result.get("error"):
            source_errors.append(SourceError(
                source="hansen_gfc", error_type="FetchError",
                message=hansen_result["error"], retryable=True, timestamp=datetime.utcnow()
            ))
        else:
            hansen = hansen_result.get("data")
        
        # Process FIRMS result
        fires: List[FireEvent] = []
        if isinstance(firms_result, Exception):
            source_errors.append(create_source_error("firms", firms_result, retryable=True))
        elif firms_result.get("error"):
            source_errors.append(SourceError(
                source="firms", error_type="FetchError",
                message=firms_result["error"], retryable=True, timestamp=datetime.utcnow()
            ))
        else:
            fires = firms_result.get("data") or []
        
        # Process GLAD result
        glad_alerts: List[GLADAlert] = []
        if isinstance(glad_result, Exception):
            source_errors.append(create_source_error("gfw_glad", glad_result, retryable=True))
        elif glad_result.get("skipped"):
            coverage_notes.append(CoverageNote(
                dataset="gfw_glad", status="skipped", reason=glad_result.get("skip_reason")
            ))
        elif glad_result.get("error"):
            source_errors.append(SourceError(
                source="gfw_glad", error_type="FetchError",
                message=glad_result["error"], retryable=True, timestamp=datetime.utcnow()
            ))
        else:
            glad_alerts = glad_result.get("data") or []
        
        # Process RADD result
        radd_alerts: List[RADDAlert] = []
        if isinstance(radd_result, Exception):
            source_errors.append(create_source_error("gfw_radd", radd_result, retryable=True))
        elif radd_result.get("skipped"):
            coverage_notes.append(CoverageNote(
                dataset="gfw_radd", status="skipped", reason=radd_result.get("skip_reason")
            ))
        elif radd_result.get("error"):
            source_errors.append(SourceError(
                source="gfw_radd", error_type="FetchError",
                message=radd_result["error"], retryable=True, timestamp=datetime.utcnow()
            ))
        else:
            radd_alerts = radd_result.get("data") or []
        
        # Process Sentinel result
        sentinel: Optional[SentinelEvidence] = None
        if isinstance(sentinel_result, Exception):
            source_errors.append(create_source_error("sentinel_hub", sentinel_result, retryable=True))
        elif sentinel_result.get("error"):
            source_errors.append(SourceError(
                source="sentinel_hub", error_type="FetchError",
                message=sentinel_result["error"], retryable=True, timestamp=datetime.utcnow()
            ))
        else:
            sentinel = sentinel_result.get("data")
        
        # Process infrastructure result
        infrastructure: List[InfrastructureNode] = []
        if isinstance(infra_result, Exception):
            source_errors.append(create_source_error("overpass", infra_result, retryable=True))
        elif infra_result.get("error"):
            source_errors.append(SourceError(
                source="overpass", error_type="FetchError",
                message=infra_result["error"], retryable=True, timestamp=datetime.utcnow()
            ))
        else:
            infrastructure = infra_result.get("data") or []
        
        # ===== Phase 2: Company enrichment and sentiment =====
        logger.info("Starting company enrichment and sentiment analysis...")
        
        # Enrich companies from infrastructure
        suspects: List[Company] = []
        if infrastructure:
            try:
                suspects = await enrich_infrastructure_companies(infrastructure)
            except Exception as e:
                source_errors.append(create_source_error("gleif", e, retryable=True))
        
        # Fetch sentiment
        search_query = build_search_query(region, aoi)
        sentiment: Optional[CombinedSentiment] = None
        try:
            sentiment, sentiment_errors = await fetch_all_sentiment(search_query, region or aoi)
            source_errors.extend(sentiment_errors)
        except Exception as e:
            source_errors.append(create_source_error("sentiment", e, retryable=True))
        
        # ===== Phase 3: Correlation analysis =====
        logger.info("Running correlation analysis...")
        
        evidence_chains, confidence_score = await correlate_events(
            aoi=aoi,
            timeframe=timeframe,
            hansen=hansen,
            glad_alerts=glad_alerts,
            radd_alerts=radd_alerts,
            fires=fires,
            sentinel=sentinel,
            infrastructure=infrastructure,
            suspects=suspects,
            sentiment=sentiment
        )
        
        # Build final dossier
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Dossier generation complete in {elapsed:.2f}s")
        
        dossier = Dossier(
            region=region,
            bbox=bbox_model,
            generated_at=datetime.utcnow(),
            analysis_period_start=start_dt,
            analysis_period_end=end_dt,
            hansen=hansen,
            gfw_glad=glad_alerts,
            gfw_radd=radd_alerts,
            firms=fires,
            sentinel=sentinel,
            nearby_infra=infrastructure,
            suspects=suspects,
            sentiment=sentiment,
            evidence_chain=evidence_chains,
            confidence_score=confidence_score,
            source_errors=source_errors,
            coverage_notes=coverage_notes
        )
        
        return dossier
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unhandled exception in /dossier: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Individual Data Endpoints ==============

@app.get("/fires")
async def get_fires(
    region: Optional[str] = Query(None),
    bbox: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365)
):
    """Get fire detections for a region."""
    aoi = resolve_bbox(region, bbox)
    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=days)
    
    result = await fetch_firms(aoi, (start_dt, end_dt))
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    return {
        "fires": result.get("data") or [],
        "count": len(result.get("data") or []),
        "bbox": aoi,
        "period": {"start": start_dt.isoformat(), "end": end_dt.isoformat()}
    }


@app.get("/loss")
async def get_loss(
    region: Optional[str] = Query(None),
    bbox: Optional[str] = Query(None),
    years: Optional[str] = Query(None, description="Comma-separated years, e.g., '2020,2021,2022'")
):
    """Get forest loss statistics for a region."""
    aoi = resolve_bbox(region, bbox)
    
    year_list = None
    if years:
        year_list = [int(y.strip()) for y in years.split(",")]
    
    result = await fetch_hansen_stats(aoi, years=year_list)
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    return {
        "hansen_stats": result.get("data"),
        "bbox": aoi
    }


@app.get("/sentiment")
async def get_sentiment(
    region: Optional[str] = Query(None),
    bbox: Optional[str] = Query(None),
    query: Optional[str] = Query(None, description="Custom search query")
):
    """Get sentiment analysis for a region."""
    aoi = resolve_bbox(region, bbox)
    
    search_query = query or build_search_query(region, aoi)
    
    sentiment, errors = await fetch_all_sentiment(search_query, region or aoi)
    
    return {
        "sentiment": sentiment,
        "query": search_query,
        "source_errors": [e.dict() for e in errors]
    }


@app.get("/sentinel/preview")
async def get_sentinel_preview(
    bbox: str = Query(..., description="Bbox: minLon,minLat,maxLon,maxLat"),
    date: Optional[str] = Query(None, description="Date (YYYY-MM-DD)")
):
    """Get Sentinel imagery preview for a bbox."""
    try:
        aoi = parse_bbox_string(bbox)
        valid, error = validate_bbox(aoi)
        if not valid:
            raise HTTPException(status_code=400, detail=error)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    target_date = datetime.fromisoformat(date) if date else datetime.utcnow()
    
    result = await fetch_sentinel_evidence(aoi, target_date)
    
    if result.get("error") and not result.get("data"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    return {
        "sentinel": result.get("data"),
        "bbox": aoi,
        "date": target_date.isoformat()
    }


# ============== Internal Endpoints ==============

class ClientLog(BaseModel):
    level: str
    message: str
    timestamp: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@app.post("/internal/logs")
async def receive_client_logs(logs: List[ClientLog]):
    """Receive logs from frontend clients."""
    for log in logs:
        log_msg = f"[CLIENT] {log.message}"
        if log.context:
            log_msg += f" | context={log.context}"
        
        if log.level.upper() == "ERROR":
            logger.error(log_msg)
        elif log.level.upper() == "WARNING":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
    
    return {"received": len(logs)}


# ============== Error Handlers ==============

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to ensure consistent error responses."""
    logger.error(f"Unhandled exception in {request.url.path}: {exc}\n{traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "source_errors": [{
                "source": "api",
                "error_type": type(exc).__name__,
                "message": str(exc),
                "retryable": False,
                "timestamp": datetime.utcnow().isoformat()
            }]
        }
    )