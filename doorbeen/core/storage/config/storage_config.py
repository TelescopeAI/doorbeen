import os
from enum import Enum
from typing import Optional

from pydantic import Field, ConfigDict

from doorbeen.core.types.ts_model import TSModel


class CheckpointerType(str, Enum):
    """Enum for different checkpointer types."""
    MEMORY = "memory"
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class StorageConfig(TSModel):
    """Configuration for the storage system."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Checkpointer configuration
    checkpointer_type: CheckpointerType = Field(
        default_factory=lambda: CheckpointerType(os.getenv("CHECKPOINTER_TYPE", "memory"))
    )
    checkpointer_db_url: Optional[str] = Field(
        default_factory=lambda: os.getenv("CHECKPOINTER_DB_URL")
    )
    checkpointer_db_path: Optional[str] = Field(
        default_factory=lambda: os.getenv("CHECKPOINTER_DB_PATH", "checkpoints.db")
    )
    
    # Storage database configuration
    storage_db_url: Optional[str] = Field(
        default_factory=lambda: os.getenv("STORAGE_DB_URL", "sqlite+aiosqlite:///storage.db")
    )
    
    # Connection pool settings
    pool_size: int = Field(
        default_factory=lambda: int(os.getenv("STORAGE_POOL_SIZE", "5"))
    )
    max_overflow: int = Field(
        default_factory=lambda: int(os.getenv("STORAGE_MAX_OVERFLOW", "10"))
    )
    
    # Logging configuration
    enable_sql_logging: bool = Field(
        default_factory=lambda: os.getenv("STORAGE_SQL_LOGGING", "false").lower() == "true"
    )
    
    def get_checkpointer_config(self) -> dict:
        """Get checkpointer-specific configuration."""
        if self.checkpointer_type == CheckpointerType.POSTGRESQL:
            if not self.checkpointer_db_url:
                raise ValueError("checkpointer_db_url is required for PostgreSQL checkpointer")
            return {"db_url": self.checkpointer_db_url}
        elif self.checkpointer_type == CheckpointerType.SQLITE:
            return {"db_path": self.checkpointer_db_path}
        else:  # MEMORY
            return {}
    
    def get_storage_config(self) -> dict:
        """Get storage database configuration."""
        return {
            "url": self.storage_db_url,
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "echo": self.enable_sql_logging
        } 