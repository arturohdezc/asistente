"""
Unit tests for Circuit Breaker implementation.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime

from core.circuit_breaker import (
    CircuitBreaker, 
    CircuitBreakerConfig, 
    CircuitState,
    CircuitBreakerManager,
    get_gemini_circuit_breaker
)
from core.exceptions import CircuitBreakerOpenError, CircuitBreakerTimeoutError


class TestCircuitBreaker:
    """Test cases for CircuitBreaker."""
    
    @pytest.fixture
    def config(self):
        """Circuit breaker configuration for testing."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=5,
            timeout=1,
            success_threshold=2
        )
    
    @pytest.fixture
    def circuit_breaker(self, config):
        """Circuit breaker instance."""
        return CircuitBreaker("test_service", config)
    
    @pytest.mark.asyncio
    async def test_successful_call(self, circuit_breaker):
        """Test successful function call through circuit breaker."""
        async def success_func():
            return "success"
        
        result = await circuit_breaker.call(success_func)
        
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.success_total == 1
        assert circuit_breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_failed_call(self, circuit_breaker):
        """Test failed function call through circuit breaker."""
        async def failing_func():
            raise Exception("Test error")
        
        with pytest.raises(Exception, match="Test error"):
            await circuit_breaker.call(failing_func)
        
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_total == 1
        assert circuit_breaker.failure_count == 1
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self, circuit_breaker):
        """Test circuit opens after reaching failure threshold."""
        async def failing_func():
            raise Exception("Test error")
        
        # Fail 3 times to reach threshold
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)
        
        # Circuit should now be open
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Next call should raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.call(failing_func)
    
    @pytest.mark.asyncio
    async def test_circuit_timeout(self, circuit_breaker):
        """Test circuit breaker timeout handling."""
        async def slow_func():
            await asyncio.sleep(2)  # Longer than timeout (1s)
            return "success"
        
        with pytest.raises(CircuitBreakerTimeoutError):
            await circuit_breaker.call(slow_func)
        
        assert circuit_breaker.failure_count == 1
    
    @pytest.mark.asyncio
    async def test_half_open_to_closed_transition(self, circuit_breaker):
        """Test transition from half-open to closed state."""
        async def failing_func():
            raise Exception("Test error")
        
        async def success_func():
            return "success"
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)
        
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Manually transition to half-open (simulate timeout)
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker.success_count = 0
        
        # Succeed twice to close circuit
        await circuit_breaker.call(success_func)
        assert circuit_breaker.state == CircuitState.HALF_OPEN
        
        await circuit_breaker.call(success_func)
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_half_open_to_open_transition(self, circuit_breaker):
        """Test transition from half-open back to open state."""
        async def failing_func():
            raise Exception("Test error")
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)
        
        # Manually transition to half-open
        circuit_breaker.state = CircuitState.HALF_OPEN
        
        # Fail once - should go back to open
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_func)
        
        assert circuit_breaker.state == CircuitState.OPEN
    
    def test_get_stats(self, circuit_breaker):
        """Test circuit breaker statistics."""
        stats = circuit_breaker.get_stats()
        
        assert stats["name"] == "test_service"
        assert stats["state"] == CircuitState.CLOSED.value
        assert stats["call_count"] == 0
        assert stats["success_total"] == 0
        assert stats["failure_total"] == 0
        assert "config" in stats
    
    @pytest.mark.asyncio
    async def test_sync_function_call(self, circuit_breaker):
        """Test calling synchronous function through circuit breaker."""
        def sync_func():
            return "sync_success"
        
        result = await circuit_breaker.call(sync_func)
        
        assert result == "sync_success"
        assert circuit_breaker.success_total == 1


class TestCircuitBreakerManager:
    """Test cases for CircuitBreakerManager."""
    
    @pytest.fixture
    def manager(self):
        """Circuit breaker manager instance."""
        return CircuitBreakerManager()
    
    def test_get_breaker_creates_new(self, manager):
        """Test getting a new circuit breaker creates it."""
        config = CircuitBreakerConfig(failure_threshold=5)
        breaker = manager.get_breaker("new_service", config)
        
        assert breaker.name == "new_service"
        assert breaker.config.failure_threshold == 5
        assert "new_service" in manager.breakers
    
    def test_get_breaker_returns_existing(self, manager):
        """Test getting existing circuit breaker returns same instance."""
        config = CircuitBreakerConfig(failure_threshold=5)
        breaker1 = manager.get_breaker("existing_service", config)
        breaker2 = manager.get_breaker("existing_service")
        
        assert breaker1 is breaker2
    
    def test_get_all_stats(self, manager):
        """Test getting statistics for all circuit breakers."""
        config = CircuitBreakerConfig()
        manager.get_breaker("service1", config)
        manager.get_breaker("service2", config)
        
        stats = manager.get_all_stats()
        
        assert "service1" in stats
        assert "service2" in stats
        assert len(stats) == 2


class TestCircuitBreakerHelpers:
    """Test cases for circuit breaker helper functions."""
    
    def test_get_gemini_circuit_breaker(self):
        """Test getting Gemini circuit breaker."""
        breaker = get_gemini_circuit_breaker()
        
        assert breaker.name == "gemini_api"
        assert breaker.config.failure_threshold == 3
        assert breaker.config.recovery_timeout == 30
        assert breaker.config.timeout == 30
        assert breaker.config.success_threshold == 2