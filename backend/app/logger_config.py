"""
Centralized logging configuration for Eco-Forensics backend.
Provides consistent log format across all modules.
"""

import logging
import sys
from typing import Optional


# Global log format as specified
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Track configured loggers to avoid duplicate handlers
_configured_loggers: set = set()


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get or create a logger with the standardized format.
    
    Args:
        name: Logger name (typically module name like 'satellite_intel')
        level: Optional logging level override (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already done
    if name not in _configured_loggers:
        # Set level
        logger.setLevel(level or logging.INFO)
        
        # Create console handler with formatting
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level or logging.INFO)
        
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        
        # Avoid duplicate handlers
        if not logger.handlers:
            logger.addHandler(handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        _configured_loggers.add(name)
    
    return logger


def configure_root_logger(level: int = logging.INFO) -> None:
    """
    Configure the root logger for any uncaught log messages.
    Called once at application startup.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root_logger.addHandler(handler)