"""
Database models and connection management.
Uses SQLAlchemy with async support for SQLite (development) or PostgreSQL (production).
"""

from datetime import datetime
from typing import Optional, AsyncGenerator
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import relationship

from .config import settings
from .logger_config import get_logger

logger = get_logger("database")

Base = declarative_base()


# ============== Database Models ==============

class DossierRecord(Base):
    """
    Stored dossier for audit/reproducibility.
    """
    __tablename__ = "dossiers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    region_name = Column(String(100), nullable=True, index=True)
    bbox_min_lon = Column(Float, nullable=False)
    bbox_min_lat = Column(Float, nullable=False)
    bbox_max_lon = Column(Float, nullable=False)
    bbox_max_lat = Column(Float, nullable=False)
    
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    analysis_start = Column(DateTime, nullable=False)
    analysis_end = Column(DateTime, nullable=False)
    
    confidence_score = Column(Float, nullable=True)
    
    # Store full dossier as JSON for simplicity
    dossier_json = Column(JSON, nullable=False)
    
    # Track errors
    had_errors = Column(Boolean, default=False)
    error_count = Column(Integer, default=0)


class AlertCache(Base):
    """
    Cache for satellite alerts (optional, for tracking historical queries).
    """
    __tablename__ = "alert_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False, index=True)  # firms, glad, radd
    bbox_hash = Column(String(64), nullable=False, index=True)  # Hash of bbox for lookup
    
    fetched_at = Column(DateTime, default=datetime.utcnow)
    alert_count = Column(Integer, default=0)
    data_json = Column(JSON, nullable=True)


class CompanyLookup(Base):
    """
    Cache of company/LEI lookups.
    """
    __tablename__ = "company_lookups"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_name = Column(String(255), nullable=False, index=True)
    
    lei = Column(String(20), nullable=True)
    legal_name = Column(String(500), nullable=True)
    country = Column(String(100), nullable=True)
    parent_lei = Column(String(20), nullable=True)
    parent_name = Column(String(500), nullable=True)
    
    match_score = Column(Float, nullable=True)
    looked_up_at = Column(DateTime, default=datetime.utcnow)
    
    raw_response = Column(JSON, nullable=True)


class RequestLog(Base):
    """
    Log of API requests for monitoring.
    """
    __tablename__ = "request_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    query_params = Column(Text, nullable=True)
    
    client_ip = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    status_code = Column(Integer, nullable=True)
    latency_ms = Column(Float, nullable=True)
    
    error_message = Column(Text, nullable=True)


# ============== Database Engine & Session ==============

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Set True for SQL debugging
    future=True
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def create_tables() -> None:
    """
    Create all database tables.
    Called on application startup.
    """
    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.
    Usage in FastAPI:
        async def endpoint(db: AsyncSession = Depends(get_session)):
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_database_health() -> tuple[bool, Optional[str]]:
    """
    Check if database is accessible.
    Returns (is_healthy, error_message).
    """
    try:
        async with async_session_maker() as session:
            # Simple query to verify connection
            await session.execute("SELECT 1")
        return True, None
    except Exception as e:
        return False, str(e)