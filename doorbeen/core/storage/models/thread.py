import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.orm import relationship

from doorbeen.core.types.ts_model import TSModel
from .base import Base, GUID


class ThreadModel(Base):
    """SQLAlchemy model for conversation threads."""
    __tablename__ = 'threads'
    
    id = Column(GUID(), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    thread_metadata = Column(Text, default='{}')
    
    # Relationship to messages
    messages = relationship("MessageModel", back_populates="thread", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert SQLAlchemy model to dictionary."""
        metadata = {}
        if self.thread_metadata:
            try:
                metadata = json.loads(self.thread_metadata)
            except (json.JSONDecodeError, TypeError) as e:
                logging.warning(f"Failed to parse thread metadata JSON: {e}. Raw data: {self.thread_metadata}")
                metadata = {}
        
        return {
            'id': self.id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'metadata': metadata,
            'message_count': 0  # Will be set separately by the storage manager
        }


class Thread(TSModel):
    """Pydantic model for conversation threads."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    message_count: Optional[int] = Field(default=0, description="Number of messages in the thread")
    
    @classmethod
    def from_model(cls, model: ThreadModel) -> 'Thread':
        """Create Thread from SQLAlchemy model."""
        return cls(**model.to_dict())
    
    def to_model_dict(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for SQLAlchemy model creation."""
        data = self.model_dump(exclude={'message_count'})
        data['thread_metadata'] = json.dumps(data.pop('metadata', {}))
        return data 