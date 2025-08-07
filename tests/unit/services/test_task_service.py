"""
Unit tests for TaskService.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from services.task_service import TaskService, TaskServiceError
from models.task import Task, Priority, TaskStatus


class TestTaskService:
    """Test cases for TaskService."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def task_service(self, mock_db_session):
        """TaskService instance with mocked database."""
        return TaskService(mock_db_session)
    
    @pytest.fixture
    def sample_task_data(self):
        """Sample task creation data."""
        return {
            "title": "Test task",
            "source": "test@example.com",
            "priority": Priority.NORMAL
        }
    
    @pytest.fixture
    def sample_task(self):
        """Sample task instance."""
        return Task(
            id=1,
            title="Test task",
            source="test@example.com",
            priority=Priority.NORMAL,
            status=TaskStatus.OPEN,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.mark.asyncio
    async def test_create_task_success(self, task_service, sample_task_data, mock_db_session):
        """Test successful task creation."""
        # Mock the task limit check
        with patch.object(task_service, '_check_task_limit', return_value=None):
            # Mock database operations
            mock_db_session.add = AsyncMock()
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()
            
            # Create task
            result = await task_service.create_task(
                title=sample_task_data["title"],
                source=sample_task_data["source"],
                priority=sample_task_data["priority"]
            )
            
            # Verify task was created with correct properties
            assert isinstance(result, Task)
            assert result.title == sample_task_data["title"]
            assert result.source == sample_task_data["source"]
            assert result.priority == sample_task_data["priority"].value
            assert result.status == TaskStatus.OPEN.value
            
            # Verify database operations were called
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_task_urgent_due_date(self, task_service, mock_db_session):
        """Test task creation with urgent due date."""
        # Create task data with due date in 1 hour (should be urgent)
        urgent_due = datetime.utcnow() + timedelta(hours=1)
        
        with patch.object(task_service, '_check_task_limit', return_value=None):
            mock_db_session.add = AsyncMock()
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()
            
            result = await task_service.create_task(
                title="Urgent task",
                source="test@example.com",
                priority=Priority.NORMAL,
                due=urgent_due
            )
            
            # Should be auto-classified as urgent
            assert result.priority == Priority.URGENT.value
    
    @pytest.mark.asyncio
    async def test_get_task_success(self, task_service, sample_task, mock_db_session):
        """Test successful task retrieval."""
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_task
        mock_db_session.execute.return_value = mock_result
        
        result = await task_service.get_task(1)
        
        assert result == sample_task
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_task_not_found(self, task_service, mock_db_session):
        """Test task retrieval when task doesn't exist."""
        # Mock database query returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        result = await task_service.get_task(999)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_task_success(self, task_service, sample_task, mock_db_session):
        """Test successful task update."""
        # Mock get_task to return existing task
        with patch.object(task_service, 'get_task', return_value=sample_task):
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()
            
            update_data = TaskUpdate(title="Updated task", status=TaskStatus.DONE)
            result = await task_service.update_task(1, update_data)
            
            assert result.title == "Updated task"
            assert result.status == TaskStatus.DONE
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_task_not_found(self, task_service, mock_db_session):
        """Test task update when task doesn't exist."""
        with patch.object(task_service, 'get_task', return_value=None):
            update_data = TaskUpdate(title="Updated task")
            result = await task_service.update_task(999, update_data)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_mark_task_done_success(self, task_service, sample_task, mock_db_session):
        """Test marking task as done."""
        with patch.object(task_service, 'get_task', return_value=sample_task):
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()
            
            result = await task_service.mark_task_done(1)
            
            assert result.status == TaskStatus.DONE
            mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mark_task_done_already_done(self, task_service, mock_db_session):
        """Test marking task as done when already done."""
        done_task = Task(
            id=1,
            title="Done task",
            source="test@example.com",
            status=TaskStatus.DONE,
            priority=Priority.NORMAL,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch.object(task_service, 'get_task', return_value=done_task):
            result = await task_service.mark_task_done(1)
            
            assert result.status == TaskStatus.DONE
            # Should not call commit since no change needed
            mock_db_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self, task_service, mock_db_session):
        """Test listing tasks with filters."""
        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 0
        
        mock_db_session.execute.side_effect = [mock_result, mock_count_result]
        
        filters = TaskFilters(
            priority=[Priority.HIGH],
            status=[TaskStatus.OPEN],
            page=1,
            size=20
        )
        
        tasks, total = await task_service.list_tasks(filters)
        
        assert isinstance(tasks, list)
        assert total == 0
        assert mock_db_session.execute.call_count == 2
    
    def test_is_due_urgent_true(self, task_service):
        """Test urgent due date detection - true case."""
        urgent_due = datetime.utcnow() + timedelta(hours=1)
        assert task_service._is_due_urgent(urgent_due) is True
    
    def test_is_due_urgent_false(self, task_service):
        """Test urgent due date detection - false case."""
        future_due = datetime.utcnow() + timedelta(days=2)
        assert task_service._is_due_urgent(future_due) is False
    
    def test_is_due_urgent_none(self, task_service):
        """Test urgent due date detection - None case."""
        assert task_service._is_due_urgent(None) is False