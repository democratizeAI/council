#!/usr/bin/env python3
"""
Correlation ID Middleware
========================
FastAPI middleware for tracking requests across Trinity microservices.
"""

import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add/extract correlation IDs for request tracing.
    
    Features:
    - Generates correlation ID if not present
    - Extracts existing correlation ID from headers
    - Adds correlation ID to response headers
    - Logs correlation ID for tracking
    """
    
    def __init__(self, app, header_name: str = "X-Corr-ID"):
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation ID tracking"""
        
        # Extract or generate correlation ID
        correlation_id = self._get_or_create_correlation_id(request)
        
        # Add to request state for downstream access
        request.state.correlation_id = correlation_id
        
        # Log request start
        logger.info(
            f"Request started | {request.method} {request.url.path} | "
            f"corr: {correlation_id}"
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers[self.header_name] = correlation_id
            
            # Log successful response
            logger.info(
                f"Request completed | {response.status_code} | "
                f"corr: {correlation_id}"
            )
            
            return response
            
        except Exception as e:
            # Log error with correlation ID
            logger.error(
                f"Request failed | {str(e)} | "
                f"corr: {correlation_id}"
            )
            raise
    
    def _get_or_create_correlation_id(self, request: Request) -> str:
        """Extract correlation ID from headers or generate new one"""
        
        # Check various header formats
        correlation_id = (
            request.headers.get(self.header_name) or
            request.headers.get("x-correlation-id") or
            request.headers.get("x-request-id") or
            request.headers.get("correlation-id")
        )
        
        if correlation_id:
            logger.debug(f"Using existing correlation ID: {correlation_id}")
            return correlation_id
        
        # Generate new correlation ID
        new_id = str(uuid.uuid4())[:8]  # Short format for logs
        logger.debug(f"Generated new correlation ID: {new_id}")
        return new_id

def get_correlation_id(request: Request) -> str:
    """Helper function to get correlation ID from request state"""
    return getattr(request.state, 'correlation_id', 'unknown')

class CorrelationIdLogger:
    """Logger wrapper that automatically includes correlation ID"""
    
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
    
    def _format_message(self, message: str, correlation_id: str = None) -> str:
        """Format message with correlation ID"""
        if correlation_id:
            return f"{message} | corr: {correlation_id}"
        return message
    
    def info(self, message: str, correlation_id: str = None):
        """Log info with correlation ID"""
        self.logger.info(self._format_message(message, correlation_id))
    
    def error(self, message: str, correlation_id: str = None):
        """Log error with correlation ID"""
        self.logger.error(self._format_message(message, correlation_id))
    
    def warning(self, message: str, correlation_id: str = None):
        """Log warning with correlation ID"""
        self.logger.warning(self._format_message(message, correlation_id))
    
    def debug(self, message: str, correlation_id: str = None):
        """Log debug with correlation ID"""
        self.logger.debug(self._format_message(message, correlation_id))

# Helper for creating correlation-aware loggers
def get_corr_logger(name: str) -> CorrelationIdLogger:
    """Create a correlation-aware logger"""
    return CorrelationIdLogger(name)

# Context manager for adding correlation ID to outbound requests
class CorrelationIdContext:
    """Context manager for propagating correlation ID to external services"""
    
    def __init__(self, correlation_id: str):
        self.correlation_id = correlation_id
        self.headers = {"X-Corr-ID": correlation_id}
    
    def get_headers(self) -> dict:
        """Get headers dict with correlation ID"""
        return self.headers.copy()
    
    def add_to_request(self, request_kwargs: dict) -> dict:
        """Add correlation ID headers to requests.post/get kwargs"""
        if 'headers' not in request_kwargs:
            request_kwargs['headers'] = {}
        
        request_kwargs['headers'].update(self.headers)
        return request_kwargs

# Example usage patterns:
"""
# In FastAPI app setup:
app.add_middleware(CorrelationIdMiddleware)

# In route handlers:
@router.post("/some-endpoint")
async def handler(request: Request):
    corr_id = get_correlation_id(request)
    logger = get_corr_logger(__name__)
    logger.info("Processing request", corr_id)
    
    # For outbound requests:
    context = CorrelationIdContext(corr_id)
    response = requests.post(
        "http://service/api",
        **context.add_to_request({"json": {"data": "value"}})
    )

# In background tasks:
async def background_task(correlation_id: str):
    logger = get_corr_logger(__name__)
    logger.info("Background task started", correlation_id)
""" 