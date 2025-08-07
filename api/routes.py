from fastapi import APIRouter, HTTPException, Depends, Header, Request, BackgroundTasks
from fastapi.responses import Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
from datetime import datetime
import structlog

from database import get_db_session
from services.task_service import TaskService, TaskServiceError
from services.telegram_service import TelegramService, TelegramServiceError
from services.gemini_service import GeminiService, GeminiServiceError
from services.calendar_service import CalendarService, CalendarServiceError
from services.summary_service import SummaryService, SummaryServiceError
from services.backup_service import BackupService, BackupServiceError
from models.task import Priority, TaskStatus
from config.settings import settings
from core.metrics import generate_metrics, get_metrics_content_type, metrics_collector
from core.middleware import validate_webhook_token
from core.exceptions import AuthenticationError

logger = structlog.get_logger()

# Create API router
router = APIRouter()

# Dependency to get services
async def get_task_service(db: AsyncSession = Depends(get_db_session)) -> TaskService:
    """Get TaskService instance"""
    return TaskService(db)

async def get_calendar_service() -> CalendarService:
    """Get CalendarService instance"""
    return CalendarService()

async def get_gemini_service() -> GeminiService:
    """Get GeminiService instance"""
    return GeminiService()

async def get_telegram_service(
    task_service: TaskService = Depends(get_task_service),
    calendar_service: CalendarService = Depends(get_calendar_service)
) -> TelegramService:
    """Get TelegramService instance"""
    return TelegramService(task_service, calendar_service)

async def get_summary_service() -> SummaryService:
    """Get SummaryService instance"""
    return SummaryService()

async def get_backup_service() -> BackupService:
    """Get BackupService instance"""
    return BackupService()

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

# Telegram webhook endpoint
@router.post("/webhook/telegram")
@router.post("/webhook/telegram/{token}")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    token: Optional[str] = None,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
    telegram_service: TelegramService = Depends(get_telegram_service)
):
    """Handle Telegram webhook updates"""
    try:
        # Validate webhook token (from header or path parameter)
        webhook_token = token or x_telegram_bot_api_secret_token or ""
        validate_webhook_token(
            webhook_token,
            settings.telegram_webhook_secret,
            "Telegram"
        )
        
        # Get request body
        update_data = await request.json()
        
        # Record webhook metrics
        metrics_collector.record_webhook_request("telegram", "received")
        
        # Process update in background
        background_tasks.add_task(
            telegram_service.process_update,
            update_data
        )
        
        return {"status": "ok"}
        
    except AuthenticationError:
        metrics_collector.record_webhook_request("telegram", "auth_failed")
        raise
    except Exception as e:
        metrics_collector.record_webhook_request("telegram", "error")
        logger.error("Telegram webhook error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Gmail webhook endpoint
@router.post("/webhook/gmail")
async def gmail_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    task_service: TaskService = Depends(get_task_service),
    gemini_service: GeminiService = Depends(get_gemini_service)
):
    """Handle Gmail push notifications"""
    try:
        # Get request body
        notification_data = await request.json()
        
        logger.info("Received Gmail notification", data=notification_data)
        
        # Process Gmail notification in background
        background_tasks.add_task(
            process_gmail_notification,
            notification_data,
            task_service,
            gemini_service
        )
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error("Gmail webhook error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Calendar webhook endpoint
@router.post("/webhook/calendar")
async def calendar_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    calendar_service: CalendarService = Depends(get_calendar_service),
    task_service: TaskService = Depends(get_task_service),
    telegram_service: TelegramService = Depends(get_telegram_service)
):
    """Handle Calendar push notifications"""
    try:
        # Get request headers (Calendar webhooks send data in headers)
        notification_data = {
            "resourceId": request.headers.get("X-Goog-Resource-ID"),
            "resourceState": request.headers.get("X-Goog-Resource-State"),
            "resourceUri": request.headers.get("X-Goog-Resource-URI"),
            "channelId": request.headers.get("X-Goog-Channel-ID"),
            "channelToken": request.headers.get("X-Goog-Channel-Token"),
            "messageNumber": request.headers.get("X-Goog-Message-Number")
        }
        
        logger.info("Received Calendar notification", data=notification_data)
        
        # Process Calendar notification in background
        background_tasks.add_task(
            process_calendar_notification,
            notification_data,
            calendar_service,
            task_service,
            telegram_service
        )
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error("Calendar webhook error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Daily summary endpoints
@router.get("/daily-summary")
async def get_daily_summary(
    task_service: TaskService = Depends(get_task_service),
    summary_service: SummaryService = Depends(get_summary_service)
):
    """Get daily task summary data"""
    try:
        summary_data = await summary_service.generate_daily_summary(task_service)
        return summary_data
        
    except SummaryServiceError as e:
        logger.error("Summary service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Get daily summary error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/cron/daily-summary")
async def daily_summary_cron(
    cron_token: str = Header(..., alias="Authorization"),
    task_service: TaskService = Depends(get_task_service),
    telegram_service: TelegramService = Depends(get_telegram_service),
    summary_service: SummaryService = Depends(get_summary_service)
):
    """Generate and send daily task summary"""
    try:
        # Validate cron token
        expected_token = f"Bearer {settings.cron_token}"
        validate_webhook_token(cron_token, expected_token, "Cron")
        
        # TODO: Get Telegram chat ID from user settings
        # For now, this would need to be configured per user
        chat_id = None  # This should come from user configuration
        
        if chat_id:
            result = await summary_service.send_daily_summary(
                task_service,
                telegram_service,
                chat_id
            )
            
            if result["status"] == "sent":
                logger.info("Daily summary sent successfully")
                return result
            else:
                logger.error("Failed to send daily summary", result=result)
                return result
        else:
            logger.info("No chat ID configured for daily summary")
            return {"status": "skipped", "reason": "No chat ID configured"}
        
    except AuthenticationError:
        raise
    except SummaryServiceError as e:
        logger.error("Summary service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Daily summary cron error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Task management endpoints
@router.get("/tasks")
async def list_tasks(
    priority: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    sort: str = "created_at",
    order: str = "desc",
    task_service: TaskService = Depends(get_task_service)
):
    """List tasks with filtering and pagination"""
    try:
        # Parse priority filter
        priority_filter = None
        if priority:
            try:
                priority_values = [Priority(p.strip()) for p in priority.split(",")]
                priority_filter = priority_values
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid priority: {str(e)}")
        
        # Parse status filter
        status_filter = None
        if status:
            try:
                status_values = [TaskStatus(s.strip()) for s in status.split(",")]
                status_filter = status_values
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid status: {str(e)}")
        
        # Get tasks
        result = await task_service.list_tasks(
            priority=priority_filter,
            status=status_filter,
            source=source,
            page=page,
            size=size,
            sort=sort,
            order=order
        )
        
        return result
        
    except HTTPException:
        raise
    except TaskServiceError as e:
        logger.error("Task service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("List tasks error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/tasks/{task_id}")
async def get_task(
    task_id: int,
    task_service: TaskService = Depends(get_task_service)
):
    """Get task by ID"""
    try:
        task = await task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return task.to_dict()
        
    except HTTPException:
        raise
    except TaskServiceError as e:
        logger.error("Task service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Get task error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/tasks/{task_id}")
async def update_task(
    task_id: int,
    updates: Dict[str, Any],
    task_service: TaskService = Depends(get_task_service)
):
    """Update task"""
    try:
        # Validate updates
        allowed_fields = {"title", "due", "status", "priority"}
        invalid_fields = set(updates.keys()) - allowed_fields
        if invalid_fields:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid fields: {', '.join(invalid_fields)}"
            )
        
        # Validate enum values
        if "status" in updates:
            try:
                TaskStatus(updates["status"])
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid status value")
        
        if "priority" in updates:
            try:
                Priority(updates["priority"])
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid priority value")
        
        # Parse due date if provided
        if "due" in updates and updates["due"]:
            try:
                if isinstance(updates["due"], str):
                    updates["due"] = datetime.fromisoformat(updates["due"].replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid due date format")
        
        # Update task
        task = await task_service.update_task(task_id, updates)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return task.to_dict()
        
    except HTTPException:
        raise
    except TaskServiceError as e:
        logger.error("Task service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Update task error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    task_service: TaskService = Depends(get_task_service)
):
    """Delete task"""
    try:
        success = await task_service.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {"status": "deleted", "task_id": task_id}
        
    except HTTPException:
        raise
    except TaskServiceError as e:
        logger.error("Task service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Delete task error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Calendar endpoints
@router.get("/calendar/events")
async def get_upcoming_events(
    hours_ahead: int = 24,
    calendar_service: CalendarService = Depends(get_calendar_service)
):
    """Get upcoming calendar events"""
    try:
        events = await calendar_service.get_upcoming_events(hours_ahead)
        return {"events": events, "hours_ahead": hours_ahead}
        
    except CalendarServiceError as e:
        logger.error("Calendar service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Get events error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/calendar/events")
async def create_calendar_event(
    event_data: Dict[str, Any],
    calendar_service: CalendarService = Depends(get_calendar_service)
):
    """Create calendar event"""
    try:
        # Validate required fields
        required_fields = {"title", "start_time"}
        missing_fields = required_fields - set(event_data.keys())
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields: {', '.join(missing_fields)}"
            )
        
        # Parse start time
        try:
            start_time = datetime.fromisoformat(event_data["start_time"].replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format")
        
        # Create event
        event = await calendar_service.create_event(
            title=event_data["title"],
            start_time=start_time,
            duration_minutes=event_data.get("duration_minutes", 60),
            description=event_data.get("description"),
            attendees=event_data.get("attendees")
        )
        
        return event
        
    except HTTPException:
        raise
    except CalendarServiceError as e:
        logger.error("Calendar service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Create event error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Background task functions
async def process_gmail_notification(
    notification_data: Dict[str, Any],
    task_service: TaskService,
    gemini_service: GeminiService
):
    """Process Gmail push notification in background"""
    try:
        logger.info("Processing Gmail notification", data=notification_data)
        
        # TODO: Implement Gmail message processing
        # This would involve:
        # 1. Decode the notification data
        # 2. Fetch the actual email content using Gmail API
        # 3. Analyze the email content with Gemini
        # 4. Create tasks based on the analysis
        
        # For now, just log the notification
        logger.info("Gmail notification processed (placeholder implementation)")
        
    except Exception as e:
        logger.error("Failed to process Gmail notification", error=str(e), exc_info=True)

async def process_calendar_notification(
    notification_data: Dict[str, Any],
    calendar_service: CalendarService,
    task_service: TaskService,
    telegram_service: TelegramService
):
    """Process Calendar push notification in background"""
    try:
        logger.info("Processing Calendar notification", data=notification_data)
        
        # Process the notification and send meeting context
        result = await calendar_service.process_webhook_notification(
            notification_data,
            task_service,
            telegram_service
        )
        
        logger.info("Calendar notification processed", result=result)
        
    except Exception as e:
        logger.error("Failed to process Calendar notification", error=str(e), exc_info=True)

# Backup endpoints
@router.post("/backup/create")
async def create_backup(
    backup_service: BackupService = Depends(get_backup_service)
):
    """Create a manual backup"""
    try:
        result = await backup_service.create_daily_backup()
        return result
        
    except BackupServiceError as e:
        logger.error("Backup service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Create backup error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/backup/list")
async def list_backups(
    backup_service: BackupService = Depends(get_backup_service)
):
    """List all available backups"""
    try:
        backups = await backup_service.list_backups()
        return {"backups": backups}
        
    except BackupServiceError as e:
        logger.error("Backup service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("List backups error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/backup/stats")
async def get_backup_stats(
    backup_service: BackupService = Depends(get_backup_service)
):
    """Get backup statistics"""
    try:
        stats = await backup_service.get_backup_stats()
        return stats
        
    except BackupServiceError as e:
        logger.error("Backup service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Get backup stats error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/backup/restore/{backup_filename}")
async def restore_backup(
    backup_filename: str,
    backup_service: BackupService = Depends(get_backup_service)
):
    """Restore from a backup file"""
    try:
        result = await backup_service.restore_from_backup(backup_filename)
        return result
        
    except BackupServiceError as e:
        logger.error("Backup service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Restore backup error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Metrics endpoint
@router.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    try:
        metrics_data = generate_metrics()
        return Response(
            content=metrics_data,
            media_type=get_metrics_content_type()
        )
    except Exception as e:
        logger.error("Failed to generate metrics", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate metrics")

# Circuit breaker status endpoint
@router.get("/circuit-breakers")
async def get_circuit_breaker_status():
    """Get circuit breaker status for all services"""
    try:
        from core.circuit_breaker import circuit_breaker_manager
        stats = circuit_breaker_manager.get_all_stats()
        return {"circuit_breakers": stats}
    except Exception as e:
        logger.error("Failed to get circuit breaker status", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")