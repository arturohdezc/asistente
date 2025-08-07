"""
Unit tests for TelegramService.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from services.telegram_service import TelegramService, TelegramServiceError
from services.task_service import TaskService
from services.calendar_service import CalendarService
from models.task import Task, Priority, TaskStatus


class TestTelegramService:
    """Test cases for TelegramService."""
    
    @pytest.fixture
    def mock_task_service(self):
        """Mock TaskService."""
        return AsyncMock(spec=TaskService)
    
    @pytest.fixture
    def mock_calendar_service(self):
        """Mock CalendarService."""
        return AsyncMock(spec=CalendarService)
    
    @pytest.fixture
    def telegram_service(self, mock_task_service, mock_calendar_service):
        """TelegramService instance with mocked dependencies."""
        with patch('services.telegram_service.Bot'):
            service = TelegramService(mock_task_service, mock_calendar_service)
            service._send_message = AsyncMock(return_value=True)
            return service
    
    @pytest.fixture
    def sample_task(self):
        """Sample task instance."""
        task = MagicMock(spec=Task)
        task.id = 1
        task.title = "Test task"
        task.priority = Priority.NORMAL.value
        task.status = TaskStatus.OPEN.value
        task.source = "telegram_user_123"
        task.due = None
        return task
    
    def test_validate_webhook_token_valid(self, telegram_service):
        """Test webhook token validation with valid token."""
        with patch('services.telegram_service.settings') as mock_settings:
            mock_settings.telegram_webhook_secret = "valid_token"
            
            result = telegram_service.validate_webhook_token("valid_token")
            assert result is True
    
    def test_validate_webhook_token_invalid(self, telegram_service):
        """Test webhook token validation with invalid token."""
        with patch('services.telegram_service.settings') as mock_settings:
            mock_settings.telegram_webhook_secret = "valid_token"
            
            result = telegram_service.validate_webhook_token("invalid_token")
            assert result is False
    
    def test_validate_webhook_token_missing(self, telegram_service):
        """Test webhook token validation with missing token."""
        result = telegram_service.validate_webhook_token(None)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_process_update_add_command(self, telegram_service, mock_task_service, sample_task):
        """Test processing /add command."""
        mock_task_service.create_task.return_value = sample_task
        
        update_data = {
            "message": {
                "text": "/add Test task description",
                "chat": {"id": 123},
                "from": {"id": 456}
            }
        }
        
        result = await telegram_service.process_update(update_data)
        
        assert result["status"] == "processed"
        mock_task_service.create_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_update_done_command(self, telegram_service, mock_task_service, sample_task):
        """Test processing /done command."""
        mock_task_service.get_task.return_value = sample_task
        mock_task_service.update_task.return_value = sample_task
        
        update_data = {
            "message": {
                "text": "/done 1",
                "chat": {"id": 123},
                "from": {"id": 456}
            }
        }
        
        result = await telegram_service.process_update(update_data)
        
        assert result["status"] == "processed"
        mock_task_service.get_task.assert_called_once_with(1)
        mock_task_service.update_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_update_list_command(self, telegram_service, mock_task_service):
        """Test processing /list command."""
        mock_task_service.get_tasks_for_summary.return_value = {
            Priority.URGENT.value: [],
            Priority.HIGH.value: [],
            Priority.NORMAL.value: [],
            Priority.LOW.value: []
        }
        
        update_data = {
            "message": {
                "text": "/list",
                "chat": {"id": 123},
                "from": {"id": 456}
            }
        }
        
        result = await telegram_service.process_update(update_data)
        
        assert result["status"] == "processed"
        mock_task_service.get_tasks_for_summary.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_update_help_command(self, telegram_service):
        """Test processing /help command."""
        update_data = {
            "message": {
                "text": "/help",
                "chat": {"id": 123},
                "from": {"id": 456}
            }
        }
        
        result = await telegram_service.process_update(update_data)
        
        assert result["status"] == "processed"
        assert "Available Commands" in result["response"]
    
    @pytest.mark.asyncio
    async def test_process_update_invalid_message(self, telegram_service):
        """Test processing update with invalid message."""
        update_data = {"invalid": "data"}
        
        result = await telegram_service.process_update(update_data)
        
        assert result["status"] == "ignored"
        assert "No message in update" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_send_daily_summary_empty(self, telegram_service):
        """Test sending daily summary with no tasks."""
        tasks_by_priority = {
            Priority.URGENT.value: [],
            Priority.HIGH.value: [],
            Priority.NORMAL.value: [],
            Priority.LOW.value: []
        }
        
        result = await telegram_service.send_daily_summary(123, tasks_by_priority)
        
        assert result is True
        telegram_service._send_message.assert_called_once()
        
        # Check that the message contains "No open tasks"
        call_args = telegram_service._send_message.call_args
        assert "No open tasks" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_send_daily_summary_with_tasks(self, telegram_service, sample_task):
        """Test sending daily summary with tasks."""
        tasks_by_priority = {
            Priority.URGENT.value: [sample_task],
            Priority.HIGH.value: [],
            Priority.NORMAL.value: [],
            Priority.LOW.value: []
        }
        
        result = await telegram_service.send_daily_summary(123, tasks_by_priority)
        
        assert result is True
        telegram_service._send_message.assert_called_once()
        
        # Check that the message contains task information
        call_args = telegram_service._send_message.call_args
        message_text = call_args[0][1]
        assert "Daily Task Summary" in message_text
        assert sample_task.title in message_text
    
    @pytest.mark.asyncio
    async def test_send_task_notification_created(self, telegram_service, sample_task):
        """Test sending task creation notification."""
        result = await telegram_service.send_task_notification(123, sample_task, "created")
        
        assert result is True
        telegram_service._send_message.assert_called_once()
        
        call_args = telegram_service._send_message.call_args
        message_text = call_args[0][1]
        assert "New Task Created" in message_text
        assert sample_task.title in message_text
    
    @pytest.mark.asyncio
    async def test_send_task_notification_urgent(self, telegram_service, sample_task):
        """Test sending urgent task notification."""
        sample_task.due = datetime.utcnow()
        
        result = await telegram_service.send_task_notification(123, sample_task, "urgent")
        
        assert result is True
        telegram_service._send_message.assert_called_once()
        
        call_args = telegram_service._send_message.call_args
        message_text = call_args[0][1]
        assert "Urgent Task Alert" in message_text
        assert "within 24 hours" in message_text
    
    @pytest.mark.asyncio
    async def test_send_meeting_context(self, telegram_service):
        """Test sending meeting context."""
        context_text = "Meeting context with related tasks"
        
        result = await telegram_service.send_meeting_context(context_text, 123)
        
        assert result is True
        telegram_service._send_message.assert_called_once_with(123, context_text)
    
    def test_get_priority_emoji(self, telegram_service):
        """Test priority emoji mapping."""
        assert telegram_service._get_priority_emoji(Priority.URGENT) == "🔴"
        assert telegram_service._get_priority_emoji(Priority.HIGH) == "🟡"
        assert telegram_service._get_priority_emoji(Priority.NORMAL) == "🟢"
        assert telegram_service._get_priority_emoji(Priority.LOW) == "⚪"