import logging
from typing import Any, Optional, Tuple

try:
    import aiosqlite
except ImportError:
    aiosqlite = None

# Import each checkpointer separately to handle missing ones gracefully
try:
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    MemorySaver = None

try:
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
except ImportError:
    AsyncSqliteSaver = None

try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg import AsyncConnection
except ImportError:
    AsyncPostgresSaver = None
    AsyncConnection = None

from doorbeen.core.storage.config import StorageConfig, CheckpointerType


class CheckpointerFactory:
    """Factory class for creating different types of checkpointers."""
    
    @staticmethod
    async def create_checkpointer(config: StorageConfig) -> Tuple[Any, Optional[Any]]:
        """
        Create a checkpointer based on the configuration.
        
        Returns:
            Tuple of (checkpointer, connection) where connection is None for memory checkpointer
        """
        checkpointer_config = config.get_checkpointer_config()
        
        if config.checkpointer_type == CheckpointerType.MEMORY:
            if MemorySaver is None:
                raise ImportError("MemorySaver is not available. Please install langgraph.")
            
            logging.info("Creating memory checkpointer")
            return MemorySaver(), None
            
        elif config.checkpointer_type == CheckpointerType.SQLITE:
            if AsyncSqliteSaver is None or aiosqlite is None:
                raise ImportError("SQLite checkpointer dependencies are not available. Please install langgraph and aiosqlite.")
            
            db_path = checkpointer_config.get("db_path", "checkpoints.db")
            logging.info(f"Creating SQLite checkpointer with path: {db_path}")
            
            conn = await aiosqlite.connect(db_path)
            checkpointer = AsyncSqliteSaver(conn)
            await checkpointer.setup()
            
            return checkpointer, conn
            
        elif config.checkpointer_type == CheckpointerType.POSTGRESQL:
            if AsyncPostgresSaver is None or AsyncConnection is None:
                raise ImportError("PostgreSQL checkpointer dependencies are not available. Please install langgraph and psycopg.")
            
            db_url = checkpointer_config["db_url"]
            logging.info(f"Creating PostgreSQL checkpointer with URL: {db_url}")
            
            conn = await AsyncConnection.connect(db_url)
            checkpointer = AsyncPostgresSaver(conn)
            await checkpointer.setup()
            
            return checkpointer, conn
            
        else:
            raise ValueError(f"Unknown checkpointer type: {config.checkpointer_type}")
    
    @staticmethod
    async def cleanup_checkpointer(checkpointer: Any, connection: Optional[Any]) -> None:
        """
        Clean up checkpointer resources.
        
        Args:
            checkpointer: The checkpointer instance
            connection: The database connection (if any)
        """
        try:
            if connection is not None:
                if hasattr(connection, 'close'):
                    await connection.close()
                elif hasattr(connection, 'aclose'):
                    await connection.aclose()
                    
            logging.info("Checkpointer resources cleaned up successfully")
        except Exception as e:
            logging.error(f"Error cleaning up checkpointer resources: {str(e)}") 