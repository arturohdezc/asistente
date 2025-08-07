import asyncio
import time
from typing import Dict, Optional
from collections import deque
import structlog

logger = structlog.get_logger()

class RateLimiter:
    """Rate limiter to prevent API quota exhaustion"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds (default: 60s)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: deque = deque()
        self._lock = asyncio.Lock()
    
    async def acquire(self, user_id: Optional[str] = None) -> bool:
        """
        Try to acquire permission to make a request
        
        Args:
            user_id: Optional user identifier for logging
            
        Returns:
            True if request is allowed, False if rate limited
        """
        async with self._lock:
            now = time.time()
            
            # Remove old requests outside the time window
            while self.requests and self.requests[0] <= now - self.time_window:
                self.requests.popleft()
            
            # Check if we can make a new request
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                logger.debug(
                    "Rate limiter: Request allowed",
                    user_id=user_id,
                    current_requests=len(self.requests),
                    max_requests=self.max_requests
                )
                return True
            else:
                logger.warning(
                    "Rate limiter: Request denied",
                    user_id=user_id,
                    current_requests=len(self.requests),
                    max_requests=self.max_requests,
                    time_window=self.time_window
                )
                return False
    
    async def wait_for_slot(self, user_id: Optional[str] = None, max_wait: int = 30) -> bool:
        """
        Wait for an available slot in the rate limiter
        
        Args:
            user_id: Optional user identifier for logging
            max_wait: Maximum time to wait in seconds
            
        Returns:
            True if slot acquired, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if await self.acquire(user_id):
                return True
            
            # Wait a bit before trying again
            await asyncio.sleep(1)
        
        logger.error(
            "Rate limiter: Timeout waiting for slot",
            user_id=user_id,
            max_wait=max_wait
        )
        return False
    
    def get_status(self) -> Dict[str, any]:
        """Get current rate limiter status"""
        now = time.time()
        
        # Count recent requests
        recent_requests = sum(1 for req_time in self.requests if req_time > now - self.time_window)
        
        return {
            "current_requests": recent_requests,
            "max_requests": self.max_requests,
            "time_window": self.time_window,
            "available_slots": max(0, self.max_requests - recent_requests),
            "next_reset": min(self.requests) + self.time_window if self.requests else now
        }

# Global rate limiter instance for Gemini API
gemini_rate_limiter = RateLimiter(max_requests=10, time_window=60)  # Conservative: 10 req/min