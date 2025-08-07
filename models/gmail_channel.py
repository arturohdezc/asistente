from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Integer, Index, func
from datetime import datetime
from .base import Base

class GmailChannel(Base):
    """Gmail channel model for storing watch channel information"""
    __tablename__ = "gmail_channels"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    channel_id: Mapped[str] = mapped_column(String(100), nullable=False)
    history_id: Mapped[str] = mapped_column(String(50), nullable=False)
    expiration: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now())
    
    __table_args__ = (
        Index('idx_email', 'email'),
        Index('idx_expiration', 'expiration'),
    )
    
    def __repr__(self) -> str:
        return f"<GmailChannel(id={self.id}, email='{self.email}', channel_id='{self.channel_id}')>"
    
    @property
    def is_expired(self) -> bool:
        """Check if channel is expired or will expire soon (within 2 hours)"""
        from datetime import timedelta
        now = datetime.utcnow()
        return self.expiration <= now + timedelta(hours=2)
    
    def to_dict(self) -> dict:
        """Convert channel to dictionary"""
        return {
            "id": self.id,
            "email": self.email,
            "channel_id": self.channel_id,
            "history_id": self.history_id,
            "expiration": self.expiration.isoformat(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }