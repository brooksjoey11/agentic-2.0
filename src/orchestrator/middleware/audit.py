"""
Audit Logging Middleware
Records all significant operations for security and compliance.
"""

import json
import logging
import time
import uuid
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..auth import verify_token

logger = logging.getLogger("audit")


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all requests and responses.
    
    Captures:
    - Who (user/session)
    - What (endpoint, method)
    - When (timestamp)
    - Result (status, duration)
    - Correlation ID
    """
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs"]
    
    async def dispatch(self, request: Request, call_next):
        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Extract identifiers
        user_id = None
        session_id = request.headers.get("X-Session-ID")
        
        # Try to get user from auth
        try:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]
                payload = verify_token(token)
                user_id = payload.get("sub")
        except Exception:
            pass
        
        # Get correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Add to request state
        request.state.correlation_id = correlation_id
        request.state.user_id = user_id
        request.state.session_id = session_id
        
        # Prepare audit log base
        audit_entry = {
            "timestamp": time.time(),
            "correlation_id": correlation_id,
            "user_id": user_id,
            "session_id": session_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("User-Agent")
        }
        
        # Process request and measure duration
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = (time.time() - start_time) * 1000
            
            # Complete audit entry
            audit_entry.update({
                "status_code": response.status_code,
                "duration_ms": round(duration, 2)
            })
            
            # Log at appropriate level
            if 200 <= response.status_code < 300:
                logger.info("Request completed", extra=audit_entry)
            elif 400 <= response.status_code < 500:
                logger.warning("Client error", extra=audit_entry)
            else:
                logger.error("Server error", extra=audit_entry)
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            audit_entry.update({
                "error": str(e),
                "duration_ms": round(duration, 2)
            })
            logger.exception("Request failed", extra=audit_entry)
            raise
