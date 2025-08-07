import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
import json

from services.gemini_service import GeminiService, CalendarAnalysisResult
from core.exceptions import GeminiServiceError


class TestCalendarGeminiService:
    """Test calendar event analysis functionality in GeminiService"""
    
    @pytest.fixture
    def gemini_service(self):
        """Create GeminiService instance for testing"""
        return GeminiService()
    
    @pytest.fixture
    def mock_gemini_response(self):
        """Mock successful Gemini API response for calendar event"""
        return {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "title": "Team Meeting",
                            "event_datetime": "2024-01-15T14:30:00Z",
                            "duration_minutes": 60,
                            "description": "Weekly team sync"
                        })
                    }]
                }
            }]
        }
    
    @pytest.mark.asyncio
    async def test_analyze_calendar_event_success(self, gemini_service, mock_gemini_response):
        """Test successful calendar event analysis"""
        with patch.object(gemini_service, '_call_gemini_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_gemini_response
            
            result = await gemini_service.analyze_calendar_event(
                text="Team meeting tomorrow at 2:30pm",
                source="test_user"
            )
            
            assert isinstance(result, CalendarAnalysisResult)
            assert result.title == "Team Meeting"
            assert result.event_datetime == datetime(2024, 1, 15, 14, 30, 0, tzinfo=datetime.fromisoformat("2024-01-15T14:30:00Z").tzinfo)
            assert result.duration_minutes == 60
            assert result.description == "Weekly team sync"
    
    @pytest.mark.asyncio
    async def test_analyze_calendar_event_no_datetime(self, gemini_service):
        """Test calendar event analysis when no datetime can be extracted"""
        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "title": "Some Meeting",
                            "event_datetime": None,
                            "duration_minutes": 60,
                            "description": None
                        })
                    }]
                }
            }]
        }
        
        with patch.object(gemini_service, '_call_gemini_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            
            result = await gemini_service.analyze_calendar_event(
                text="Some meeting",
                source="test_user"
            )
            
            assert result.title == "Some Meeting"
            assert result.event_datetime is None
            assert result.duration_minutes == 60
            assert result.description is None
    
    @pytest.mark.asyncio
    async def test_analyze_calendar_event_with_duration(self, gemini_service):
        """Test calendar event analysis with custom duration"""
        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "title": "Long Meeting",
                            "event_datetime": "2024-01-15T09:00:00Z",
                            "duration_minutes": 120,
                            "description": "Extended planning session"
                        })
                    }]
                }
            }]
        }
        
        with patch.object(gemini_service, '_call_gemini_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            
            result = await gemini_service.analyze_calendar_event(
                text="Long meeting tomorrow 9am for 2 hours",
                source="test_user"
            )
            
            assert result.title == "Long Meeting"
            assert result.duration_minutes == 120
            assert result.description == "Extended planning session"
    
    @pytest.mark.asyncio
    async def test_analyze_calendar_event_invalid_json(self, gemini_service):
        """Test calendar event analysis with invalid JSON response"""
        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": "invalid json response"
                    }]
                }
            }]
        }
        
        with patch.object(gemini_service, '_call_gemini_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            
            result = await gemini_service.analyze_calendar_event(
                text="Meeting tomorrow",
                source="test_user"
            )
            
            # Should return default values when JSON parsing fails
            assert result.title == "Event"
            assert result.event_datetime is None
            assert result.duration_minutes == 60
            assert result.description is None
    
    @pytest.mark.asyncio
    async def test_analyze_calendar_event_invalid_duration(self, gemini_service):
        """Test calendar event analysis with invalid duration"""
        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "title": "Test Meeting",
                            "event_datetime": "2024-01-15T14:30:00Z",
                            "duration_minutes": -30,  # Invalid duration
                            "description": None
                        })
                    }]
                }
            }]
        }
        
        with patch.object(gemini_service, '_call_gemini_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            
            result = await gemini_service.analyze_calendar_event(
                text="Test meeting",
                source="test_user"
            )
            
            # Should default to 60 minutes for invalid duration
            assert result.title == "Test Meeting"
            assert result.duration_minutes == 60
    
    @pytest.mark.asyncio
    async def test_analyze_calendar_event_markdown_json(self, gemini_service):
        """Test calendar event analysis with markdown-wrapped JSON"""
        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": "```json\n" + json.dumps({
                            "title": "Markdown Meeting",
                            "event_datetime": "2024-01-15T14:30:00Z",
                            "duration_minutes": 90,
                            "description": "Meeting with markdown response"
                        }) + "\n```"
                    }]
                }
            }]
        }
        
        with patch.object(gemini_service, '_call_gemini_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            
            result = await gemini_service.analyze_calendar_event(
                text="Markdown meeting tomorrow",
                source="test_user"
            )
            
            assert result.title == "Markdown Meeting"
            assert result.duration_minutes == 90
            assert result.description == "Meeting with markdown response"
    
    def test_create_calendar_analysis_prompt(self, gemini_service):
        """Test calendar analysis prompt creation"""
        prompt = gemini_service._create_calendar_analysis_prompt(
            text="Meeting tomorrow at 2pm",
            source="test_user"
        )
        
        assert "Meeting tomorrow at 2pm" in prompt
        assert "test_user" in prompt
        assert "calendar event information" in prompt
        assert "ISO format" in prompt
        assert "duration_minutes" in prompt
    
    def test_parse_calendar_gemini_response_success(self, gemini_service, mock_gemini_response):
        """Test successful parsing of calendar Gemini response"""
        result = gemini_service._parse_calendar_gemini_response(mock_gemini_response)
        
        assert isinstance(result, CalendarAnalysisResult)
        assert result.title == "Team Meeting"
        assert result.duration_minutes == 60
        assert result.description == "Weekly team sync"
    
    def test_parse_calendar_gemini_response_no_candidates(self, gemini_service):
        """Test parsing calendar response with no candidates"""
        response = {"candidates": []}
        
        with pytest.raises(GeminiServiceError, match="No candidates in Gemini response"):
            gemini_service._parse_calendar_gemini_response(response)
    
    def test_parse_calendar_gemini_response_no_parts(self, gemini_service):
        """Test parsing calendar response with no parts"""
        response = {
            "candidates": [{
                "content": {"parts": []}
            }]
        }
        
        with pytest.raises(GeminiServiceError, match="No parts in Gemini response"):
            gemini_service._parse_calendar_gemini_response(response)
    
    def test_parse_calendar_gemini_response_empty_text(self, gemini_service):
        """Test parsing calendar response with empty text"""
        response = {
            "candidates": [{
                "content": {
                    "parts": [{"text": ""}]
                }
            }]
        }
        
        with pytest.raises(GeminiServiceError, match="Empty text in Gemini response"):
            gemini_service._parse_calendar_gemini_response(response)