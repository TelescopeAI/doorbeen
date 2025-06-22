import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field
from sqlalchemy import Column, DateTime, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from doorbeen.core.types.ts_model import TSModel
from .base import Base, GUID


class MessageModel(Base):
    """SQLAlchemy model for conversation messages."""
    __tablename__ = 'messages'
    
    id = Column(GUID(), primary_key=True, default=uuid4)
    thread_id = Column(GUID(), ForeignKey('threads.id', ondelete='CASCADE'), nullable=False)
    content = Column(Text, nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system, tool
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    message_metadata = Column(Text, default='{}')
    
    # Relationship to thread
    thread = relationship("ThreadModel", back_populates="messages")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert SQLAlchemy model to dictionary."""
        metadata = {}
        if self.message_metadata:
            try:
                metadata = json.loads(self.message_metadata)
            except (json.JSONDecodeError, TypeError) as e:
                logging.warning(f"Failed to parse message metadata JSON: {e}. Raw data: {self.message_metadata}")
                metadata = {}
        
        return {
            'id': self.id,
            'thread_id': self.thread_id,
            'content': self.content,
            'role': self.role,
            'created_at': self.created_at,
            'metadata': metadata
        }


class Message(TSModel):
    """Pydantic model for conversation messages."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    thread_id: UUID
    content: str
    role: str = Field(..., description="Message role: user, assistant, system, or tool")
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def from_model(cls, model: MessageModel) -> 'Message':
        """Create Message from SQLAlchemy model."""
        return cls(**model.to_dict())
    
    def to_model_dict(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for SQLAlchemy model creation."""
        data = self.model_dump()
        data['message_metadata'] = json.dumps(data.pop('metadata', {}))
        return data 