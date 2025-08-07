"""
Circuit Breaker Pattern Implementation

This module implements the circuit breaker pattern to handle failures
in external service calls gracefully and prevent cascading failures.
"""

import asyncio
import time
from enum import Enum
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass
import structlog

from .exceptions import CircuitBreakerOpenError, CircuitBreakerTimeoutError

logger = structlog.get_logger()


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5          # Number of failures to open circuit
    recovery_timeout: int = 60          # Seconds to wait before trying again
    expected_exception: type = Exception  # Exception type that counts as failure
    timeout: int = 30                   # Timeout for individual calls
    success_threshold: int = 3          # Successes needed to close circuit in half-open


class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.call_count = 0
        self.success_total = 0
        self.failure_total = 0
        
        logger.info(
            "Circuit breaker initialized",
            name=self.name,
            config=config.__dict__
        )
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function call through the circuit breaker
        
        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: When circuit is open
            CircuitBreakerTimeoutError: When call times out
        """
        self.call_count += 1
        
        # Check if circuit should transition from open to half-open
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(
                    "Circuit breaker transitioning to half-open",
                    name=self.name
                )
            else:
                logger.warning(
                    "Circuit breaker is open, rejecting call",
                    name=self.name,
                    time_until_retry=self.config.recovery_timeout - (time.time() - self.last_failure_time)
                )
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is open",
                    error_code="CIRCUIT_BREAKER_OPEN",
                    context={
                        "circuit_name": self.name,
                        "state": self.state.value,
                        "failure_count": self.failure_count,
                        "time_until_retry": self.config.recovery_timeout - (time.time() - self.last_failure_time)
                    }
                )
        
        try:
            # Execute the function with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs),
                timeout=self.config.timeout
            )
            
            # Call succeeded
            await self._on_success()
            return result
            
        except asyncio.TimeoutError as e:
            logger.error(
                "Circuit breaker call timed out",
                name=self.name,
                timeout=self.config.timeout
            )
            await self._on_failure()
            raise CircuitBreakerTimeoutError(
                f"Circuit breaker '{self.name}' call timed out after {self.config.timeout}s",
                error_code="CIRCUIT_BREAKER_TIMEOUT",
                context={
                    "circuit_name": self.name,
                    "timeout": self.config.timeout
                },
                original_error=e
            )
            
        except self.config.expected_exception as e:
            logger.error(
                "Circuit breaker call failed",
                name=self.name,
                error=str(e),
                exception_type=type(e).__name__
            )
            await self._on_failure()
            raise
            
        except Exception as e:
            # Unexpected exception, don't count as failure
            logger.error(
                "Circuit breaker call failed with unexpected exception",
                name=self.name,
                error=str(e),
                exception_type=type(e).__name__
            )
            raise
    
    async def _on_success(self):
        """Handle successful call"""
        self.success_total += 1
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                # Close the circuit
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(
                    "Circuit breaker closed after successful recovery",
                    name=self.name,
                    success_count=self.success_count
                )
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    async def _on_failure(self):
        """Handle failed call"""
        self.failure_total += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                # Open the circuit
                self.state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker opened due to failures",
                    name=self.name,
                    failure_count=self.failure_count,
                    threshold=self.config.failure_threshold
                )
        elif self.state == CircuitState.HALF_OPEN:
            # Go back to open state
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker returned to open state after failure in half-open",
                name=self.name
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "call_count": self.call_count,
            "success_total": self.success_total,
            "failure_total": self.failure_total,
            "failure_count": self.failure_count,
            "success_rate": self.success_total / max(self.call_count, 1),
            "last_failure_time": self.last_failure_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "timeout": self.config.timeout,
                "success_threshold": self.config.success_threshold
            }
        }


class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers
    """
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
    
    def get_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """
        Get or create a circuit breaker
        
        Args:
            name: Circuit breaker name
            config: Configuration (uses default if not provided)
            
        Returns:
            CircuitBreaker instance
        """
        if name not in self.breakers:
            if config is None:
                config = CircuitBreakerConfig()
            self.breakers[name] = CircuitBreaker(name, config)
        
        return self.breakers[name]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        return {name: breaker.get_stats() for name, breaker in self.breakers.items()}


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()


# Convenience function for common external services
def get_gemini_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker for Gemini API calls"""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=30,
        timeout=30,
        success_threshold=2
    )
    return circuit_breaker_manager.get_breaker("gemini_api", config)


def get_telegram_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker for Telegram API calls"""
    config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60,
        timeout=15,
        success_threshold=3
    )
    return circuit_breaker_manager.get_breaker("telegram_api", config)


def get_gmail_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker for Gmail API calls"""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=120,
        timeout=30,
        success_threshold=2
    )
    return circuit_breaker_manager.get_breaker("gmail_api", config)


def get_calendar_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker for Calendar API calls"""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=120,
        timeout=30,
        success_threshold=2
    )
    return circuit_breaker_manager.get_breaker("calendar_api", config)