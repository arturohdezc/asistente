"""
Cloud Function Proxy for Gmail and Calendar Webhooks

This proxy handles cold-start detection and implements exponential backoff
retry logic for forwarding webhooks to the main Replit application.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional
import httpx
from google.cloud import functions_v1
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Configuration
REPLIT_BASE_URL = "https://your-repl-name.your-username.repl.co"  # Update with actual Repl URL
MAX_RETRIES = 5
BASE_DELAY = 1  # Base delay in seconds for exponential backoff
COLD_START_THRESHOLD = 10  # Seconds to consider as cold start
TIMEOUT = 30  # Request timeout in seconds

class ProxyError(Exception):
    """Proxy specific errors"""
    pass

async def forward_webhook_with_retry(
    endpoint: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    max_retries: int = MAX_RETRIES
) -> Dict[str, Any]:
    """
    Forward webhook to Replit with exponential backoff retry logic
    
    Args:
        endpoint: Target endpoint path (e.g., "/api/v1/webhook/gmail")
        payload: Webhook payload
        headers: Request headers
        max_retries: Maximum number of retry attempts
        
    Returns:
        Response data from the target service
    """
    url = f"{REPLIT_BASE_URL}{endpoint}"
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            delay = BASE_DELAY * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s, 8s, 16s
            
            if attempt > 0:
                logger.info(
                    "Retrying webhook forward",
                    attempt=attempt + 1,
                    delay=delay,
                    url=url
                )
                await asyncio.sleep(delay)
            
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers
                )
                
                response_time = time.time() - start_time
                
                # Check for cold start (slow response)
                is_cold_start = response_time > COLD_START_THRESHOLD
                
                logger.info(
                    "Webhook forwarded",
                    attempt=attempt + 1,
                    status_code=response.status_code,
                    response_time=response_time,
                    is_cold_start=is_cold_start,
                    url=url
                )
                
                # Raise for HTTP errors
                response.raise_for_status()
                
                # Return successful response
                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "is_cold_start": is_cold_start,
                    "attempt": attempt + 1,
                    "response_data": response.json() if response.content else {}
                }
                
        except httpx.TimeoutException as e:
            last_exception = e
            logger.warning(
                "Webhook forward timeout",
                attempt=attempt + 1,
                error=str(e),
                url=url
            )
        except httpx.HTTPStatusError as e:
            last_exception = e
            logger.warning(
                "Webhook forward HTTP error",
                attempt=attempt + 1,
                status_code=e.response.status_code,
                error=str(e),
                url=url
            )
            # Don't retry on 4xx errors (except rate limiting and cold start indicators)
            if 400 <= e.response.status_code < 500 and e.response.status_code not in [429, 503]:
                break
        except Exception as e:
            last_exception = e
            logger.warning(
                "Webhook forward error",
                attempt=attempt + 1,
                error=str(e),
                url=url
            )
    
    # All retries failed
    logger.error(
        "All webhook forward retries failed",
        max_retries=max_retries,
        last_error=str(last_exception),
        url=url
    )
    
    return {
        "status": "failed",
        "error": str(last_exception),
        "attempts": max_retries,
        "url": url
    }

def gmail_webhook_proxy(request):
    """
    Cloud Function entry point for Gmail webhook proxy
    
    Args:
        request: HTTP request object
        
    Returns:
        HTTP response
    """
    try:
        # Extract request data
        request_json = request.get_json(silent=True)
        if not request_json:
            logger.error("No JSON payload in Gmail webhook")
            return {"error": "No JSON payload"}, 400
        
        # Extract headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Gmail-Webhook-Proxy/1.0",
            "X-Forwarded-For": request.headers.get("X-Forwarded-For", ""),
            "X-Proxy-Timestamp": str(int(time.time()))
        }
        
        # Add original headers that might be important
        important_headers = [
            "Authorization",
            "X-Goog-Channel-ID",
            "X-Goog-Channel-Token",
            "X-Goog-Message-Number",
            "X-Goog-Resource-ID",
            "X-Goog-Resource-State",
            "X-Goog-Resource-URI"
        ]
        
        for header in important_headers:
            if header in request.headers:
                headers[header] = request.headers[header]
        
        logger.info(
            "Processing Gmail webhook",
            payload_size=len(json.dumps(request_json)),
            headers_count=len(headers)
        )
        
        # Forward webhook asynchronously
        result = asyncio.run(
            forward_webhook_with_retry(
                endpoint="/api/v1/webhook/gmail",
                payload=request_json,
                headers=headers
            )
        )
        
        if result["status"] == "success":
            return {"status": "forwarded", "proxy_result": result}, 200
        else:
            return {"status": "failed", "proxy_result": result}, 502
            
    except Exception as e:
        logger.error(
            "Gmail webhook proxy error",
            error=str(e),
            exc_info=True
        )
        return {"error": "Proxy internal error", "details": str(e)}, 500

def calendar_webhook_proxy(request):
    """
    Cloud Function entry point for Calendar webhook proxy
    
    Args:
        request: HTTP request object
        
    Returns:
        HTTP response
    """
    try:
        # Extract request data
        request_json = request.get_json(silent=True)
        if not request_json:
            logger.error("No JSON payload in Calendar webhook")
            return {"error": "No JSON payload"}, 400
        
        # Extract headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Calendar-Webhook-Proxy/1.0",
            "X-Forwarded-For": request.headers.get("X-Forwarded-For", ""),
            "X-Proxy-Timestamp": str(int(time.time()))
        }
        
        # Add original headers that might be important
        important_headers = [
            "Authorization",
            "X-Goog-Channel-ID",
            "X-Goog-Channel-Token",
            "X-Goog-Message-Number",
            "X-Goog-Resource-ID",
            "X-Goog-Resource-State",
            "X-Goog-Resource-URI"
        ]
        
        for header in important_headers:
            if header in request.headers:
                headers[header] = request.headers[header]
        
        logger.info(
            "Processing Calendar webhook",
            payload_size=len(json.dumps(request_json)),
            headers_count=len(headers)
        )
        
        # Forward webhook asynchronously
        result = asyncio.run(
            forward_webhook_with_retry(
                endpoint="/api/v1/webhook/calendar",
                payload=request_json,
                headers=headers
            )
        )
        
        if result["status"] == "success":
            return {"status": "forwarded", "proxy_result": result}, 200
        else:
            return {"status": "failed", "proxy_result": result}, 502
            
    except Exception as e:
        logger.error(
            "Calendar webhook proxy error",
            error=str(e),
            exc_info=True
        )
        return {"error": "Proxy internal error", "details": str(e)}, 500

# Health check endpoint
def proxy_health_check(request):
    """Health check endpoint for the proxy"""
    return {
        "status": "ok",
        "timestamp": int(time.time()),
        "service": "webhook-proxy",
        "version": "1.0.0"
    }, 200