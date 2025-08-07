import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from services.telegram_service import TelegramService
from services.gemini_service import CalendarAnalysisResult
from services.task_service import TaskService
from services.calendar_service import CalendarService


class TestTelegramCalendarCommand:
    """Test improved calendar command in TelegramService"""
    
    @pytest.fixture
    def mock_task_service(self):
        """Mock TaskService"""
        return AsyncMock(spec=TaskService)
    
    @pytest.fixture
    def mock_calendar_service(self):
        """Mock CalendarService"""
        mock_service = AsyncMock(spec=CalendarService)
        mock_service.create_event.return_value = {
            'id': 'test_event_123',
            'summary': 'Test Event'
        }
        return mock_service
    
    @pytest.fixture
    def mock_gemini_service(self):
        """Mock GeminiService"""
        return AsyncMock()
    
    @pytest.fixture
    def telegram_service(self, mock_task_service, mock_calendar_service, mock_gemini_service):
        """Create TelegramService with mocked dependencies"""
        return TelegramService(
            task_service=mock_task_service,
            calendar_service=mock_calendar_service,
            gemini_service=mock_gemini_service
        )
    
    @pytest.mark.asyncio
    async def test_calendar_command_natural_language(self, telegram_service, mock_gemini_service, mock_calendar_service):
        """Test calendar command with natural language input"""
        # Mock Gemini analysis result
        analysis_result = CalendarAnalysisResult(
            title="Team Meeting",
            event_datetime=datetime(2024, 1, 15, 14, 30),
            duration_minutes=60,
            description="Weekly team sync"
        )
        mock_gemini_service.analyze_calendar_event.return_value = analysis_result
        
        # Test the command
        response = await telegram_service._handle_calendar_command(
            args="Team meeting tomorrow at 2:30pm",
            user_id=123
        )
        
        # Verify Gemini was called
        mock_gemini_service.analyze_calendar_event.assert_called_once_with(
            text="Team meeting tomorrow at 2:30pm",
            source="telegram_user_123"
        )
        
        # Verify calendar event was created
        mock_calendar_service.create_event.assert_called_once_with(
            title="Team Meeting",
            start_time=datetime(2024, 1, 15, 14, 30),
            duration_minutes=60,
            description="Weekly team sync"
        )
        
        # Verify response
        assert "📅 Calendar event created successfully!" in response
        assert "Team Meeting" in response
        assert "2024-01-15 14:30" in response
        assert "60 minutes" in response
        assert "Weekly team sync" in response
    
    @pytest.mark.asyncio
    async def test_calendar_command_no_datetime_extracted(self, telegram_service, mock_gemini_service):
        """Test calendar command when no datetime can be extracted"""
        # Mock Gemini analysis result with no datetime
        analysis_result = CalendarAnalysisResult(
            title="Some Meeting",
            event_datetime=None,
            duration_minutes=60,
            description=None
        )
        mock_gemini_service.analyze_calendar_event.return_value = analysis_result
        
        # Test the command
        response = await telegram_service._handle_calendar_command(
            args="Some vague meeting",
            user_id=123
        )
        
        # Verify error response
        assert "❌ Could not extract date/time from your message" in response
        assert "Please include when the event should happen" in response
    
    @pytest.mark.asyncio
    async def test_calendar_command_empty_args(self, telegram_service):
        """Test calendar command with empty arguments"""
        response = await telegram_service._handle_calendar_command(
            args="",
            user_id=123
        )
        
        # Verify help response
        assert "❌ Please provide event details" in response
        assert "Usage: /calendar" in response
        assert "Meeting tomorrow at 2pm" in response
    
    @pytest.mark.asyncio
    async def test_calendar_command_no_calendar_service(self, mock_task_service, mock_gemini_service):
        """Test calendar command when calendar service is not available"""
        # Create service without calendar service
        telegram_service = TelegramService(
            task_service=mock_task_service,
            calendar_service=None,
            gemini_service=mock_gemini_service
        )
        
        response = await telegram_service._handle_calendar_command(
            args="Meeting tomorrow",
            user_id=123
        )
        
        assert "❌ Calendar service not available" in response
    
    @pytest.mark.asyncio
    async def test_calendar_command_with_custom_duration(self, telegram_service, mock_gemini_service, mock_calendar_service):
        """Test calendar command with custom duration"""
        # Mock Gemini analysis result with custom duration
        analysis_result = CalendarAnalysisResult(
            title="Long Meeting",
            event_datetime=datetime(2024, 1, 15, 9, 0),
            duration_minutes=120,
            description="Extended planning session"
        )
        mock_gemini_service.analyze_calendar_event.return_value = analysis_result
        
        # Test the command
        response = await telegram_service._handle_calendar_command(
            args="Long meeting tomorrow 9am for 2 hours",
            user_id=123
        )
        
        # Verify calendar event was created with custom duration
        mock_calendar_service.create_event.assert_called_once_with(
            title="Long Meeting",
            start_time=datetime(2024, 1, 15, 9, 0),
            duration_minutes=120,
            description="Extended planning session"
        )
        
        # Verify response shows custom duration
        assert "120 minutes" in response
    
    @pytest.mark.asyncio
    async def test_calendar_command_gemini_error(self, telegram_service, mock_gemini_service):
        """Test calendar command when Gemini service fails"""
        # Mock Gemini service to raise an exception
        mock_gemini_service.analyze_calendar_event.side_effect = Exception("Gemini API error")
        
        response = await telegram_service._handle_calendar_command(
            args="Meeting tomorrow",
            user_id=123
        )
        
        assert "❌ Failed to create calendar event" in response
        assert "Gemini API error" in response
    
    @pytest.mark.asyncio
    async def test_calendar_command_calendar_service_error(self, telegram_service, mock_gemini_service, mock_calendar_service):
        """Test calendar command when calendar service fails"""
        # Mock successful Gemini analysis
        analysis_result = CalendarAnalysisResult(
            title="Test Meeting",
            event_datetime=datetime(2024, 1, 15, 14, 30),
            duration_minutes=60,
            description=None
        )
        mock_gemini_service.analyze_calendar_event.return_value = analysis_result
        
        # Mock calendar service to raise an exception
        mock_calendar_service.create_event.side_effect = Exception("Calendar API error")
        
        response = await telegram_service._handle_calendar_command(
            args="Meeting tomorrow at 2:30pm",
            user_id=123
        )
        
        assert "❌ Failed to create calendar event" in response
        assert "Calendar API error" in response
    
    @pytest.mark.asyncio
    async def test_calendar_command_no_description(self, telegram_service, mock_gemini_service, mock_calendar_service):
        """Test calendar command without description"""
        # Mock Gemini analysis result without description
        analysis_result = CalendarAnalysisResult(
            title="Quick Meeting",
            event_datetime=datetime(2024, 1, 15, 14, 30),
            duration_minutes=30,
            description=None
        )
        mock_gemini_service.analyze_calendar_event.return_value = analysis_result
        
        # Test the command
        response = await telegram_service._handle_calendar_command(
            args="Quick meeting tomorrow at 2:30pm for 30 minutes",
            user_id=123
        )
        
        # Verify response doesn't include description section
        assert "📅 Calendar event created successfully!" in response
        assert "Quick Meeting" in response
        assert "30 minutes" in response
        assert "Description:" not in response