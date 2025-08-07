"""
Unit tests for GeminiService with mocked API calls.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch
import httpx
import respx

from app.services.gemini_service import GeminiService, GeminiServiceError
from app.models.task import Priority


class TestGeminiService:
    """Test cases for GeminiService."""
    
    @pytest.fixture
    def gemini_service(self):
        """GeminiService instance."""
        with patch('app.services.gemini_service.get_settings') as mock_settings:
            mock_settings.return_value.gemini_api_key = "test_api_key"
            return GeminiService()
    
    @pytest.fixture
    def sample_gemini_response(self):
        """Sample successful Gemini API response."""
        return {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "tasks": [
                                {
                                    "title": "Buy groceries",
                                    "due": "2024-01-15T18:00:00Z",
                                    "priority": "normal"
                                },
                                {
                                    "title": "Call dentist",
                                    "due": None,
                                    "priority": "high"
                                }
                            ],
                            "context": "Email about daily tasks and appointments",
                            "overall_priority": "high"
                        })
                    }]
                }
            }]
        }
    
    @pytest.fixture
    def sample_urgent_response(self):
        """Sample Gemini response with urgent task."""
        return {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "tasks": [
                                {
                                    "title": "URGENT: Submit report by EOD",
                                    "due": "2024-01-15T17:00:00Z",
                                    "priority": "urgent"
                                }
                            ],
                            "context": "Urgent work email about deadline",
                            "overall_priority": "urgent"
                        })
                    }]
                }
            }]
        }
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_analyze_text_success(self, gemini_service, sample_gemini_response):
        """Test successful text analysis."""
        # Mock the Gemini API endpoint
        respx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"
        ).mock(return_value=httpx.Response(200, json=sample_gemini_response))
        
        # Analyze text
        result = await gemini_service.analyze_text(
            "Remember to buy groceries today and call the dentist",
            "test@example.com"
        )
        
        # Verify results
        assert len(result.tasks) == 2
        assert result.tasks[0].title == "Buy groceries"
        assert result.tasks[0].priority == Priority.NORMAL
        assert result.tasks[1].title == "Call dentist"
        assert result.tasks[1].priority == Priority.HIGH
        assert result.context == "Email about daily tasks and appointments"
        assert result.priority == Priority.HIGH
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_analyze_text_urgent_priority(self, gemini_service, sample_urgent_response):
        """Test analysis with urgent priority classification."""
        respx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"
        ).mock(return_value=httpx.Response(200, json=sample_urgent_response))
        
        result = await gemini_service.analyze_text(
            "URGENT: Please submit the quarterly report by end of day!",
            "boss@company.com"
        )
        
        assert len(result.tasks) == 1
        assert result.tasks[0].priority == Priority.URGENT
        assert result.priority == Priority.URGENT
        assert "URGENT" in result.tasks[0].title
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_analyze_text_with_retry_success(self, gemini_service, sample_gemini_response):
        """Test successful analysis after initial failure."""
        # Mock first call to fail, second to succeed
        respx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"
        ).mock(side_effect=[
            httpx.Response(500, text="Internal Server Error"),
            httpx.Response(200, json=sample_gemini_response)
        ])
        
        result = await gemini_service.analyze_text("Test text", "test@example.com")
        
        assert len(result.tasks) == 2
        assert result.context == "Email about daily tasks and appointments"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_analyze_text_rate_limit_retry(self, gemini_service, sample_gemini_response):
        """Test retry logic with rate limiting."""
        # Mock rate limit then success
        respx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"
        ).mock(side_effect=[
            httpx.Response(429, text="Rate limit exceeded"),
            httpx.Response(200, json=sample_gemini_response)
        ])
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await gemini_service.analyze_text("Test text", "test@example.com")
            
            # Verify sleep was called for backoff
            mock_sleep.assert_called_once()
            assert len(result.tasks) == 2
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_analyze_text_max_retries_exceeded(self, gemini_service):
        """Test failure after max retries exceeded."""
        # Mock all attempts to fail
        respx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"
        ).mock(return_value=httpx.Response(500, text="Server Error"))
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(GeminiServiceError, match="Failed after 3 attempts"):
                await gemini_service.analyze_text("Test text", "test@example.com")
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_analyze_text_invalid_json_response(self, gemini_service):
        """Test handling of invalid JSON response."""
        invalid_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": "This is not valid JSON"
                    }]
                }
            }]
        }
        
        respx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"
        ).mock(return_value=httpx.Response(200, json=invalid_response))
        
        result = await gemini_service.analyze_text("Test text", "test@example.com")
        
        # Should return empty result for invalid JSON
        assert len(result.tasks) == 0
        assert result.context == "Failed to analyze content"
        assert result.priority == Priority.NORMAL
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_analyze_text_empty_response(self, gemini_service):
        """Test handling of empty response."""
        empty_response = {"candidates": []}
        
        respx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"
        ).mock(return_value=httpx.Response(200, json=empty_response))
        
        result = await gemini_service.analyze_text("Test text", "test@example.com")
        
        assert len(result.tasks) == 0
        assert result.context == "Failed to analyze content"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_analyze_text_malformed_task_data(self, gemini_service):
        """Test handling of malformed task data in response."""
        malformed_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "tasks": [
                                {
                                    "title": "Valid task",
                                    "priority": "normal"
                                },
                                {
                                    # Missing title
                                    "priority": "invalid_priority"
                                },
                                {
                                    "title": "Another valid task",
                                    "due": "invalid_date_format",
                                    "priority": "high"
                                }
                            ],
                            "context": "Mixed valid and invalid tasks",
                            "overall_priority": "normal"
                        })
                    }]
                }
            }]
        }
        
        respx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"
        ).mock(return_value=httpx.Response(200, json=malformed_response))
        
        result = await gemini_service.analyze_text("Test text", "test@example.com")
        
        # Should only include valid tasks
        assert len(result.tasks) == 2
        assert result.tasks[0].title == "Valid task"
        assert result.tasks[1].title == "Another valid task"
    
    def test_create_analysis_prompt(self, gemini_service):
        """Test analysis prompt creation."""
        prompt = gemini_service._create_analysis_prompt("Test email content", "test@example.com")
        
        assert "Test email content" in prompt
        assert "test@example.com" in prompt
        assert "JSON only" in prompt
        assert "urgent|high|normal|low" in prompt
    
    def test_create_empty_result(self, gemini_service):
        """Test empty result creation."""
        result = gemini_service._create_empty_result()
        
        assert len(result.tasks) == 0
        assert result.context == "Failed to analyze content"
        assert result.priority == Priority.NORMAL