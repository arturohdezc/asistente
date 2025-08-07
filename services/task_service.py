from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import structlog

from models.task import Task, TaskStatus, Priority
from config.settings import settings

logger = structlog.get_logger()

class TaskServiceError(Exception):
    """Task service specific errors"""
    pass

class TaskService:
    """Service for managing tasks with CRUD operations"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_task(
        self, 
        title: str, 
        source: str, 
        due: Optional[datetime] = None,
        priority: Priority = Priority.NORMAL,
        status: TaskStatus = TaskStatus.OPEN
    ) -> Task:
        """Create a new task"""
        try:
            # Check task limit
            await self._check_task_limit()
            
            # Auto-classify as urgent if due within 24 hours
            if due and due <= datetime.utcnow() + timedelta(hours=24):
                priority = Priority.URGENT
            
            task = Task(
                title=title.strip(),
                source=source.lower(),
                due=due,
                priority=priority.value,
                status=status.value
            )
            
            self.db.add(task)
            await self.db.commit()
            await self.db.refresh(task)
            
            logger.info(
                "Task created",
                task_id=task.id,
                title=task.title,
                source=task.source,
                priority=task.priority
            )
            
            return task
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to create task", error=str(e), exc_info=True)
            raise TaskServiceError(f"Failed to create task: {str(e)}")
    
    async def get_task(self, task_id: int) -> Optional[Task]:
        """Get task by ID"""
        try:
            result = await self.db.execute(
                select(Task).where(Task.id == task_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get task", task_id=task_id, error=str(e))
            raise TaskServiceError(f"Failed to get task: {str(e)}")
    
    async def update_task(
        self, 
        task_id: int, 
        updates: Dict[str, Any]
    ) -> Optional[Task]:
        """Update task with given updates"""
        try:
            # Get existing task
            task = await self.get_task(task_id)
            if not task:
                return None
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            
            # Auto-classify as urgent if due within 24 hours
            if 'due' in updates and updates['due']:
                if updates['due'] <= datetime.utcnow() + timedelta(hours=24):
                    task.priority = Priority.URGENT.value
            
            await self.db.commit()
            await self.db.refresh(task)
            
            logger.info(
                "Task updated",
                task_id=task_id,
                updates=updates
            )
            
            return task
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to update task", task_id=task_id, error=str(e))
            raise TaskServiceError(f"Failed to update task: {str(e)}")
    
    async def delete_task(self, task_id: int) -> bool:
        """Delete task by ID"""
        try:
            result = await self.db.execute(
                delete(Task).where(Task.id == task_id)
            )
            await self.db.commit()
            
            deleted = result.rowcount > 0
            if deleted:
                logger.info("Task deleted", task_id=task_id)
            
            return deleted
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to delete task", task_id=task_id, error=str(e))
            raise TaskServiceError(f"Failed to delete task: {str(e)}")
    
    async def list_tasks(
        self,
        priority: Optional[List[Priority]] = None,
        status: Optional[List[TaskStatus]] = None,
        source: Optional[str] = None,
        page: int = 1,
        size: int = 20,
        sort: str = "created_at",
        order: str = "desc"
    ) -> Dict[str, Any]:
        """List tasks with filtering and pagination"""
        try:
            # Build query
            query = select(Task)
            
            # Apply filters
            conditions = []
            
            if priority:
                priority_values = [p.value for p in priority]
                conditions.append(Task.priority.in_(priority_values))
            
            if status:
                status_values = [s.value for s in status]
                conditions.append(Task.status.in_(status_values))
            
            if source:
                conditions.append(Task.source == source.lower())
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Apply sorting
            sort_column = getattr(Task, sort, Task.created_at)
            if order.lower() == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination
            offset = (page - 1) * size
            query = query.offset(offset).limit(size)
            
            # Execute query
            result = await self.db.execute(query)
            tasks = result.scalars().all()
            
            return {
                "items": [task.to_dict() for task in tasks],
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size
            }
            
        except Exception as e:
            logger.error("Failed to list tasks", error=str(e))
            raise TaskServiceError(f"Failed to list tasks: {str(e)}")
    
    async def get_tasks_by_priority(self, priority: Priority) -> List[Task]:
        """Get all tasks by priority"""
        try:
            result = await self.db.execute(
                select(Task)
                .where(Task.priority == priority.value)
                .where(Task.status == TaskStatus.OPEN.value)
                .order_by(Task.due.asc().nullslast(), Task.created_at.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error("Failed to get tasks by priority", priority=priority, error=str(e))
            raise TaskServiceError(f"Failed to get tasks by priority: {str(e)}")
    
    async def get_tasks_for_summary(self) -> Dict[str, List[Task]]:
        """Get tasks grouped by priority for daily summary"""
        try:
            result = await self.db.execute(
                select(Task)
                .where(Task.status == TaskStatus.OPEN.value)
                .order_by(Task.due.asc().nullslast(), Task.created_at.desc())
            )
            tasks = list(result.scalars().all())
            
            grouped = {
                Priority.URGENT.value: [],
                Priority.HIGH.value: [],
                Priority.NORMAL.value: [],
                Priority.LOW.value: []
            }
            
            for task in tasks:
                grouped[task.priority].append(task)
            
            return grouped
            
        except Exception as e:
            logger.error("Failed to get tasks for summary", error=str(e))
            raise TaskServiceError(f"Failed to get tasks for summary: {str(e)}")
    
    async def find_related_tasks(self, keywords: List[str], attendees: List[str] = None) -> List[Task]:
        """Find tasks related to meeting keywords and attendees"""
        try:
            conditions = []
            
            # Search in task titles
            if keywords:
                keyword_conditions = []
                for keyword in keywords:
                    keyword_conditions.append(Task.title.ilike(f"%{keyword}%"))
                conditions.append(or_(*keyword_conditions))
            
            # Search by source (attendees)
            if attendees:
                attendee_conditions = []
                for attendee in attendees:
                    attendee_conditions.append(Task.source == attendee.lower())
                conditions.append(or_(*attendee_conditions))
            
            if not conditions:
                return []
            
            query = select(Task).where(
                and_(
                    Task.status == TaskStatus.OPEN.value,
                    or_(*conditions)
                )
            ).order_by(Task.priority.desc(), Task.due.asc().nullslast())
            
            result = await self.db.execute(query)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error("Failed to find related tasks", error=str(e))
            raise TaskServiceError(f"Failed to find related tasks: {str(e)}")
    
    async def _check_task_limit(self):
        """Check if task limit is exceeded"""
        try:
            result = await self.db.execute(
                select(func.count(Task.id))
            )
            count = result.scalar()
            
            if count >= settings.max_tasks_limit:
                logger.warning(
                    "Task limit exceeded",
                    current_count=count,
                    limit=settings.max_tasks_limit
                )
                raise TaskServiceError(
                    f"Task limit of {settings.max_tasks_limit} exceeded. "
                    "Consider migrating to PostgreSQL for better performance."
                )
                
        except TaskServiceError:
            raise
        except Exception as e:
            logger.error("Failed to check task limit", error=str(e))
            # Don't fail task creation for limit check errors
    
    async def get_task_count(self) -> int:
        """Get total task count"""
        try:
            result = await self.db.execute(
                select(func.count(Task.id))
            )
            return result.scalar()
        except Exception as e:
            logger.error("Failed to get task count", error=str(e))
            return 0