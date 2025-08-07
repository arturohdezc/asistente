"""
Integration tests for API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json

from main import app
from models.task import Priority, TaskStatus


class TestAPIEndpoints:
    """Integration tests for API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_task_service(self):
        """Mock task service for testing."""
        return AsyncMock()
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Personal Assistant Bot API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
    
    def test_api_health_endpoint(self, client):
        """Test API health check endpoint."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
    
    @patch('api.routes.get_task_service')
    def test_list_tasks_endpoint(self, mock_get_service, client):
        """Test list tasks endpoint."""
        # Mock the task service
        mock_service = AsyncMock()
        mock_service.list_tasks.return_value = {
            "items": [
                {
                    "id": 1,
                    "title": "Test task",
                    "status": TaskStatus.OPEN.value,
                    "priority": Priority.NORMAL.value,
                    "source": "test@example.com",
                    "due": None,
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00"
                }
            ],
            "total": 1,
            "page": 1,
            "size": 20,
            "pages": 1
        }
        mock_get_service.return_value = mock_service
        
        response = client.get("/api/v1/tasks")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Test task"
    
    @patch('api.routes.get_task_service')
    def test_get_task_endpoint(self, mock_get_service, client):
        """Test get single task endpoint."""
        mock_service = AsyncMock()
        mock_task = AsyncMock()
        mock_task.to_dict.return_value = {
            "id": 1,
            "title": "Test task",
            "status": TaskStatus.OPEN.value,
            "priority": Priority.NORMAL.value,
            "source": "test@example.com",
            "due": None,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        mock_service.get_task.return_value = mock_task
        mock_get_service.return_value = mock_service
        
        response = client.get("/api/v1/tasks/1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "Test task"
    
    @patch('api.routes.get_task_service')
    def test_get_task_not_found(self, mock_get_service, client):
        """Test get task endpoint when task doesn't exist."""
        mock_service = AsyncMock()
        mock_service.get_task.return_value = None
        mock_get_service.return_value = mock_service
        
        response = client.get("/api/v1/tasks/999")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    @patch('api.routes.get_task_service')
    def test_update_task_endpoint(self, mock_get_service, client):
        """Test update task endpoint."""
        mock_service = AsyncMock()
        mock_task = AsyncMock()
        mock_task.to_dict.return_value = {
            "id": 1,
            "title": "Updated task",
            "status": TaskStatus.DONE.value,
            "priority": Priority.HIGH.value,
            "source": "test@example.com",
            "due": None,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        mock_service.update_task.return_value = mock_task
        mock_get_service.return_value = mock_service
        
        update_data = {
            "title": "Updated task",
            "status": TaskStatus.DONE.value,
            "priority": Priority.HIGH.value
        }
        
        response = client.put("/api/v1/tasks/1", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated task"
        assert data["status"] == TaskStatus.DONE.value
    
    @patch('api.routes.get_task_service')
    def test_delete_task_endpoint(self, mock_get_service, client):
        """Test delete task endpoint."""
        mock_service = AsyncMock()
        mock_service.delete_task.return_value = True
        mock_get_service.return_value = mock_service
        
        response = client.delete("/api/v1/tasks/1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["task_id"] == 1
    
    @patch('api.routes.get_task_service')
    def test_delete_task_not_found(self, mock_get_service, client):
        """Test delete task endpoint when task doesn't exist."""
        mock_service = AsyncMock()
        mock_service.delete_task.return_value = False
        mock_get_service.return_value = mock_service
        
        response = client.delete("/api/v1/tasks/999")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    @patch('api.routes.get_telegram_service')
    def test_telegram_webhook_invalid_token(self, mock_get_service, client):
        """Test Telegram webhook with invalid token."""
        response = client.post(
            "/api/v1/webhook/telegram",
            json={"message": {"text": "/start", "chat": {"id": 123}}},
            headers={"X-Telegram-Bot-Api-Secret-Token": "invalid_token"}
        )
        
        assert response.status_code == 401
    
    @patch('api.routes.get_summary_service')
    def test_daily_summary_endpoint(self, mock_get_service, client):
        """Test daily summary endpoint."""
        mock_service = AsyncMock()
        mock_service.generate_daily_summary.return_value = {
            "date": "2024-01-01",
            "total_tasks": 5,
            "tasks_by_priority": {
                "urgent": [],
                "high": [],
                "normal": [],
                "low": []
            },
            "priority_counts": {
                "urgent": 1,
                "high": 2,
                "normal": 2,
                "low": 0
            },
            "overdue_tasks": [],
            "today_tasks": [],
            "overdue_count": 0,
            "today_count": 0
        }
        mock_get_service.return_value = mock_service
        
        response = client.get("/api/v1/daily-summary")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 5
        assert data["date"] == "2024-01-01"
    
    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get("/api/v1/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        
        # Check for some expected metrics
        content = response.text
        assert "http_requests_total" in content or "# HELP" in content
    
    def test_circuit_breakers_endpoint(self, client):
        """Test circuit breakers status endpoint."""
        response = client.get("/api/v1/circuit-breakers")
        
        assert response.status_code == 200
        data = response.json()
        assert "circuit_breakers" in data
    
    @patch('api.routes.get_backup_service')
    def test_backup_stats_endpoint(self, mock_get_service, client):
        """Test backup statistics endpoint."""
        mock_service = AsyncMock()
        mock_service.get_backup_stats.return_value = {
            "backup_count": 3,
            "total_size_bytes": 1024000,
            "total_size_mb": 1.0,
            "retention_days": 7,
            "backup_directory": "/home/runner/backups",
            "current_database": {
                "tasks_count": 100,
                "channels_count": 2,
                "tasks_limit": 10000,
                "tasks_limit_usage_percent": 1.0
            }
        }
        mock_get_service.return_value = mock_service
        
        response = client.get("/api/v1/backup/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["backup_count"] == 3
        assert data["current_database"]["tasks_count"] == 100
    
    def test_invalid_endpoint(self, client):
        """Test accessing invalid endpoint."""
        response = client.get("/api/v1/nonexistent")
        
        assert response.status_code == 404
    
    def test_security_headers(self, client):
        """Test that security headers are present."""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        # Check for security headers
        headers = response.headers
        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert "X-XSS-Protection" in headers
        assert "Strict-Transport-Security" in headers
        assert "X-Request-ID" in headers
    
    def test_request_id_header(self, client):
        """Test that request ID is added to responses."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        
        # Request ID should be a UUID-like string
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36  # UUID length
        assert request_id.count("-") == 4  # UUID format