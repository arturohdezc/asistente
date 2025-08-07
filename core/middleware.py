"""
Security and error handling middleware for FastAPI

This module provides middleware for request ID tracking, security headers,
input sanitization, and global error handling.
"""

import uuid
import time
from typing import Callable, Dict, Any
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
import structlog

from .exceptions import (
    PersonalAssistantError, 
    ValidationError, 
    AuthenticationError,
    AuthorizationError,
    RateLimitError
)

logger = structlog.get_logger()


async def request_id_middleware(request: Request, call_next: Callable) -> Response:
    """
    Add request ID to all requests for tracking and logging
    """
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Add to structured logging context
    with structlog.contextvars.bound_contextvars(request_id=request_id):
        # Log request start
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            user_agent=request.headers.get("user-agent"),
            client_ip=request.client.host if request.client else None
        )
        
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            process_time = time.time() - start_time
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(round(process_time, 4))
            
            # Log successful response
            logger.info(
                "Request completed",
                status_code=response.status_code,
                process_time=process_time
            )
            
            return response
            
        except Exception as e:
            # Calculate response time for errors too
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                "Request failed",
                error=str(e),
                exception_type=type(e).__name__,
                process_time=process_time,
                exc_info=True
            )
            
            # Re-raise to be handled by global exception handler
            raise


async def security_headers_middleware(request: Request, call_next: Callable) -> Response:
    """
    Add security headers to all responses
    """
    response = await call_next(request)
    
    # Security headers
    security_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
    }
    
    for header, value in security_headers.items():
        response.headers[header] = value
    
    return response


async def input_sanitization_middleware(request: Request, call_next: Callable) -> Response:
    """
    Basic input sanitization and validation
    """
    # Check for suspicious patterns in URL path
    suspicious_patterns = [
        "../", "..\\", "<script", "javascript:", "data:text/html",
        "eval(", "expression(", "vbscript:", "onload=", "onerror="
    ]
    
    path = request.url.path.lower()
    for pattern in suspicious_patterns:
        if pattern in path:
            logger.warning(
                "Suspicious pattern detected in URL path",
                path=request.url.path,
                pattern=pattern,
                client_ip=request.client.host if request.client else None
            )
            raise HTTPException(
                status_code=400,
                detail="Invalid request path"
            )
    
    # Check request size (prevent large payloads)
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            size = int(content_length)
            max_size = 10 * 1024 * 1024  # 10MB limit
            if size > max_size:
                logger.warning(
                    "Request payload too large",
                    content_length=size,
                    max_allowed=max_size,
                    client_ip=request.client.host if request.client else None
                )
                raise HTTPException(
                    status_code=413,
                    detail="Request payload too large"
                )
        except ValueError:
            pass
    
    return await call_next(request)


def create_global_exception_handler():
    """
    Create global exception handler for the FastAPI application
    """
    
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Global exception handler with structured error responses
        """
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        # Handle PersonalAssistantError and its subclasses
        if isinstance(exc, PersonalAssistantError):
            logger.error(
                "Application error",
                request_id=request_id,
                error_code=exc.error_code,
                message=exc.message,
                context=exc.context,
                exception_type=type(exc).__name__
            )
            
            # Determine HTTP status code based on exception type
            if isinstance(exc, ValidationError):
                status_code = 400
            elif isinstance(exc, AuthenticationError):
                status_code = 401
            elif isinstance(exc, AuthorizationError):
                status_code = 403
            elif isinstance(exc, RateLimitError):
                status_code = 429
            else:
                status_code = 500
            
            return JSONResponse(
                status_code=status_code,
                content={
                    "error": exc.to_dict(),
                    "request_id": request_id,
                    "timestamp": time.time()
                }
            )
        
        # Handle HTTPException
        elif isinstance(exc, HTTPException):
            logger.warning(
                "HTTP exception",
                request_id=request_id,
                status_code=exc.status_code,
                detail=exc.detail
            )
            
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "error_code": f"HTTP_{exc.status_code}",
                        "message": exc.detail,
                        "exception_type": "HTTPException"
                    },
                    "request_id": request_id,
                    "timestamp": time.time()
                }
            )
        
        # Handle unexpected exceptions
        else:
            logger.error(
                "Unhandled exception",
                request_id=request_id,
                path=request.url.path,
                method=request.method,
                exception=str(exc),
                exception_type=type(exc).__name__,
                exc_info=True
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "error_code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "exception_type": "InternalServerError"
                    },
                    "request_id": request_id,
                    "timestamp": time.time()
                }
            )
    
    return global_exception_handler


def validate_webhook_token(token: str, expected_token: str, service_name: str) -> None:
    """
    Validate webhook token with proper error handling
    
    Args:
        token: Provided token
        expected_token: Expected token value
        service_name: Name of the service for logging
        
    Raises:
        AuthenticationError: When token is invalid
    """
    if not token:
        logger.warning(
            "Missing webhook token",
            service=service_name
        )
        raise AuthenticationError(
            f"Missing {service_name} webhook token",
            error_code=f"{service_name.upper()}_TOKEN_MISSING"
        )
    
    if token != expected_token:
        logger.warning(
            "Invalid webhook token",
            service=service_name,
            provided_token_length=len(token) if token else 0
        )
        raise AuthenticationError(
            f"Invalid {service_name} webhook token",
            error_code=f"{service_name.upper()}_TOKEN_INVALID"
        )


def sanitize_input(data: Any, max_length: int = 1000) -> Any:
    """
    Basic input sanitization for user data
    
    Args:
        data: Input data to sanitize
        max_length: Maximum string length allowed
        
    Returns:
        Sanitized data
        
    Raises:
        ValidationError: When data is invalid
    """
    if isinstance(data, str):
        # Check length
        if len(data) > max_length:
            raise ValidationError(
                f"Input too long (max {max_length} characters)",
                error_code="INPUT_TOO_LONG",
                context={"max_length": max_length, "actual_length": len(data)}
            )
        
        # Remove potentially dangerous characters
        dangerous_chars = ["<", ">", "&", "\"", "'", "\x00"]
        for char in dangerous_chars:
            if char in data:
                data = data.replace(char, "")
        
        # Strip whitespace
        data = data.strip()
        
    elif isinstance(data, dict):
        # Recursively sanitize dictionary values
        return {key: sanitize_input(value, max_length) for key, value in data.items()}
    
    elif isinstance(data, list):
        # Recursively sanitize list items
        return [sanitize_input(item, max_length) for item in data]
    
    return data


class RateLimiter:
    """
    Simple in-memory rate limiter
    """
    
    def __init__(self):
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """
        Check if request is allowed under rate limit
        
        Args:
            key: Unique identifier (e.g., IP address)
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            True if request is allowed
        """
        now = time.time()
        
        # Initialize or clean old requests
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests outside the window
        self.requests[key] = [
            req_time for req_time in self.requests[key] 
            if now - req_time < window
        ]
        
        # Check if limit exceeded
        if len(self.requests[key]) >= limit:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """
    Rate limiting middleware
    """
    # Get client identifier
    client_ip = request.client.host if request.client else "unknown"
    
    # Different limits for different endpoints
    if request.url.path.startswith("/api/v1/webhook/"):
        # More restrictive for webhooks
        limit, window = 100, 60  # 100 requests per minute
    else:
        # General API rate limit
        limit, window = 1000, 60  # 1000 requests per minute
    
    if not rate_limiter.is_allowed(client_ip, limit, window):
        logger.warning(
            "Rate limit exceeded",
            client_ip=client_ip,
            path=request.url.path,
            limit=limit,
            window=window
        )
        raise RateLimitError(
            "Rate limit exceeded",
            error_code="RATE_LIMIT_EXCEEDED",
            context={
                "limit": limit,
                "window": window,
                "client_ip": client_ip
            }
        )
    
    return await call_next(request)