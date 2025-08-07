from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Integer, Index, func
from datetime import datetime
from typing import Optional
from enum import Enum
from .base import Base

class Priority(str, Enum):
    """Task priority levels"""
    URGENT = "urgent"
    HIGH = "high" 
    NORMAL = "normal"
    LOW = "low"

class TaskStatus(str, Enum):
    """Task status values"""
    OPEN = "open"
    DONE = "done"

class Task(Base):
    """Task model for storing user tasks"""
    __tablename__ = "tasks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    due: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.OPEN.value)
    source: Mapped[str] = mapped_column(String(100), nullable=False)  # email origen
    priority: Mapped[str] = mapped_column(String(10), default=Priority.NORMAL.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Índices para optimización
    __table_args__ = (
        Index('idx_status_priority_due', 'status', 'priority', 'due'),
        Index('idx_source', 'source'),
        Index('idx_created_at', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}', priority='{self.priority}')>"
    
    @property
    def is_urgent(self) -> bool:
        """Check if task is urgent based on due date"""
        if not self.due:
            return False
        
        from datetime import timedelta
        now = datetime.utcnow()
        return self.due <= now + timedelta(hours=24)
    
    def to_dict(self) -> dict:
        """Convert task to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "due": self.due.isoformat() if self.due else None,
            "status": self.status,
            "source": self.source,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }