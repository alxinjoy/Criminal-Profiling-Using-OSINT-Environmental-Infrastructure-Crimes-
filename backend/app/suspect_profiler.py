"""
Suspect profiling module with better Overpass queries.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from rapidfuzz import fuzz, process

from .config import settings
from .logger_config import get_logger
from .api_models import InfrastructureNode, Company, SourceError
from .utils import (
    retry_with_backoff, rate_limit, save_raw_response, bbox_to_hash,
    create_source_error, haversine_distance, bbox_centroid
)

logger = get_logger("suspect_profiler")


OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def build_overpass_query(bbox: tuple, radius_m: int = 5000) -> str:
    """Build Overpass QL query for industrial infrastructure."""
    min_lon, min_lat, max_lon, max_lat = bbox
    
    # Limit bbox size
    max_size = 2.0
    if (max_lon - min_lon) > max_size or (max_lat - min_lat) > max_size:
        center_lon = (min_lon + max_lon) / 2
        center_lat = (min_lat + max_lat) / 2
        half_size = max_size / 2
        min_lon = center_lon - half_size
        max_lon = center_lon + half_size
        min_lat = center_lat - half_size
        max_lat = center_lat + half_size
    
    bbox_str = f"{min_lat},{min_lon},{max_lat},{max_lon}"
    
    # Broader query for various industrial facilities
    query = f"""
[out:json][timeout:20];
(
  node["landuse"="industrial"]({bbox_str});
  way["landuse"="industrial"]({bbox_str});
  node["industrial"]({bbox_str});
  way["industrial"]({bbox_str});
  node["man_made"="works"]({bbox_str});
  way["man_made"="works"]({bbox_str});
  node["building"="industrial"]({bbox_str});
  way["building"="industrial"]({bbox_str});
  node["craft"~"sawmill|oil"]({bbox_str});
  way["craft"~"sawmill|oil"]({bbox_str});
  node["power"="plant"]({bbox_str});
  way["power"="plant"]({bbox_str});
);
out center body 200;
"""
    return query


async def identify_nearby_infrastructure(
    aoi: tuple,
    radius_m: int = 5000
) -> Dict[str, Any]:
    """Identify industrial infrastructure near an area of interest."""
    logger.info(f"Initiating Overpass infrastructure search for bbox={aoi}, radius={radius_m}m")
    start_time = datetime.utcnow()
    
    query = build_overpass_query(aoi, radius_m)
    last_error = None
    
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            await rate_limit("overpass")
            
            async with httpx.AsyncClient(timeout=25) as client:
                response = await client.post(
                    endpoint,
                    data={"data": query},
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 429:
                    logger.warning(f"Overpass rate limit at {endpoint}, trying next...")
                    await asyncio.sleep(2)
                    continue
                
                if response.status_code == 504:
                    logger.warning(f"Overpass timeout at {endpoint}, trying next...")
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                center_lon, center_lat = bbox_centroid(aoi)
                nodes = []
                elements = data.get("elements", [])
                
                for elem in elements:
                    if elem.get("type") == "node":
                        lat = elem.get("lat")
                        lon = elem.get("lon")
                    else:
                        center = elem.get("center", {})
                        lat = center.get("lat")
                        lon = center.get("lon")
                    
                    if lat is None or lon is None:
                        continue
                    
                    distance = haversine_distance(center_lat, center_lon, lat, lon)
                    
                    tags = elem.get("tags", {})
                    node_type = (
                        tags.get("industrial") or 
                        tags.get("landuse") or 
                        tags.get("man_made") or 
                        tags.get("craft") or
                        tags.get("power") or
                        "industrial"
                    )
                    
                    nodes.append(InfrastructureNode(
                        osm_id=elem.get("id"),
                        node_type=node_type,
                        name=tags.get("name") or tags.get("operator") or tags.get("company"),
                        latitude=lat,
                        longitude=lon,
                        distance_m=round(distance, 1),
                        tags=tags
                    ))
                
                nodes.sort(key=lambda x: x.distance_m or float('inf'))
                
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                logger.info(f"Overpass returned {len(nodes)} infrastructure nodes in {elapsed:.2f}s via {endpoint}")
                
                bbox_hash = bbox_to_hash(aoi)
                await save_raw_response("overpass", bbox_hash, data, "overpass_raw")
                
                return {"data": nodes, "error": None}
                
        except httpx.HTTPStatusError as e:
            logger.warning(f"Overpass HTTP error via {endpoint}: {e.response.status_code}")
            last_error = e
        except httpx.TimeoutException:
            logger.warning(f"Overpass timeout via {endpoint}")
            last_error = "Timeout"
        except Exception as e:
            logger.warning(f"Overpass error via {endpoint}: {e}")
            last_error = e
    
    logger.error(f"Overpass API failed on all endpoints: {last_error}")
    return {"data": [], "error": f"All Overpass endpoints failed: {last_error}"}


async def check_overpass_health() -> Tuple[bool, Optional[str], Optional[float]]:
    """Check Overpass API health."""
    test_query = "[out:json][timeout:5];node(1);out;"
    
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            start = datetime.utcnow()
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    endpoint,
                    data={"data": test_query}
                )
                
                if response.status_code == 200:
                    latency = (datetime.utcnow() - start).total_seconds() * 1000
                    return True, None, latency
                    
        except Exception as e:
            logger.debug(f"Overpass health check failed at {endpoint}: {e}")
            continue
    
    return False, "All endpoints unavailable", None


# ============== GLEIF API ==============

async def search_gleif(query: str, limit: int = 5) -> Dict[str, Any]:
    """Search GLEIF API for legal entities."""
    await rate_limit("gleif")
    
    url = f"{settings.gleif_api_base}/lei-records"
    params = {
        "filter[entity.legalName]": query,
        "page[size]": limit
    }
    
    async with httpx.AsyncClient(timeout=settings.default_timeout_seconds) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def enrich_company(name: str) -> Dict[str, Any]:
    """Enrich company information using GLEIF API."""
    logger.info(f"Enriching company: {name}")
    
    if not name or len(name.strip()) < 2:
        return {"data": None, "error": "Invalid company name"}
    
    try:
        search_result = await search_gleif(name, limit=5)
        records = search_result.get("data", [])
        
        if not records:
            return {
                "data": Company(name=name, source="gleif", match_score=0),
                "error": None
            }
        
        best_match = None
        best_score = 0
        
        for record in records:
            attrs = record.get("attributes", {})
            entity = attrs.get("entity", {})
            legal_name = entity.get("legalName", {}).get("name", "")
            
            score = fuzz.ratio(name.lower(), legal_name.lower())
            
            if score > best_score:
                best_score = score
                best_match = record
        
        if best_match and best_score >= 60:
            attrs = best_match.get("attributes", {})
            entity = attrs.get("entity", {})
            lei = best_match.get("id")
            legal_address = entity.get("legalAddress", {})
            
            company = Company(
                name=entity.get("legalName", {}).get("name", name),
                lei=lei,
                country=legal_address.get("country"),
                jurisdiction=legal_address.get("region"),
                status=entity.get("status"),
                match_score=best_score,
                source="gleif"
            )
            
            logger.info(f"GLEIF enrichment complete for '{name}': LEI={lei}, score={best_score}")
            return {"data": company, "error": None}
        
        return {
            "data": Company(name=name, source="gleif", match_score=best_score),
            "error": None
        }
        
    except Exception as e:
        logger.error(f"GLEIF enrichment failed for '{name}': {e}")
        return {"data": None, "error": str(e)}


async def enrich_infrastructure_companies(infrastructure: List[InfrastructureNode]) -> List[Company]:
    """Enrich all companies found in infrastructure data."""
    company_names = set()
    
    for node in infrastructure:
        if node.name:
            company_names.add(node.name)
        
        operator = node.tags.get("operator")
        company = node.tags.get("company")
        
        if operator:
            company_names.add(operator)
        if company:
            company_names.add(company)
    
    if not company_names:
        logger.info("No company names found in infrastructure to enrich")
        return []
    
    logger.info(f"Enriching {len(company_names)} unique company names")
    
    semaphore = asyncio.Semaphore(3)
    
    async def limited_enrich(name: str) -> Optional[Company]:
        async with semaphore:
            result = await enrich_company(name)
            return result.get("data")
    
    results = await asyncio.gather(
        *[limited_enrich(name) for name in list(company_names)[:10]],  # Limit to 10
        return_exceptions=True
    )
    
    companies = []
    for result in results:
        if isinstance(result, Company):
            companies.append(result)
    
    return companies


async def check_gleif_health() -> Tuple[bool, Optional[str]]:
    """Check GLEIF API health."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{settings.gleif_api_base}/lei-records?page[size]=1")
            if response.status_code < 500:
                return True, None
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)


# ============== Fuzzy Matching ==============

def fuzzy_match_company(query: str, candidates: List[str], threshold: int = 70) -> List[Tuple[str, int]]:
    """Fuzzy match a company name against candidates."""
    if not candidates:
        return []
    
    results = process.extract(query, candidates, scorer=fuzz.token_sort_ratio, limit=10)
    return [(match, score) for match, score, _ in results if score >= threshold]


def normalize_company_name(name: str) -> str:
    """Normalize a company name for matching."""
    if not name:
        return ""
    
    name = name.strip().upper()
    
    suffixes = [" INC", " INC.", " LLC", " LTD", " LTD.", " CORP", " CORP.", " CORPORATION", " CO", " CO.", " PLC"]
    
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    
    return " ".join(name.split())


def calculate_match_confidence(query: str, matched: str, lei_found: bool) -> float:
    """Calculate confidence score for a company match."""
    base_score = fuzz.ratio(normalize_company_name(query), normalize_company_name(matched))
    
    if lei_found:
        base_score = min(100, base_score + 15)
    
    return round(base_score, 1)