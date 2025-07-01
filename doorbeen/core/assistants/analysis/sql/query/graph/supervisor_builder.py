import logging
from typing import Any

from doorbeen.core.assistants.analysis.sql.supervisor.graph import create_sql_supervisor_graph
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.ts_model import TSModel


class SupervisorGraphBuilder(TSModel):
    """
    Builder for supervisor-based multi-agent SQL analysis graph.
    
    This graph uses LangGraph agents with supervisor coordination for
    intelligent multi-agent processing of SQL analysis requests.
    """
    
    handler: ModelHandler
    question: str

    def build(self, checkpointer: Any):
        """Build the supervisor-based multi-agent graph"""
        logging.info("🤖 [SUPERVISOR_BUILDER] Building supervisor-based multi-agent graph")
        
        try:
            # Create the supervisor graph using the correct graph.py
            # This returns a compiled graph ready for execution with checkpointer applied
            supervisor_graph = create_sql_supervisor_graph(
                handler=self.handler,
                connection=None,  # Connection will be provided at runtime via config
                question=self.question,
                checkpointer=checkpointer  # Pass checkpointer during graph creation
            )
            
            logging.info("✅ [SUPERVISOR_BUILDER] Supervisor graph created and compiled successfully")
            
            return supervisor_graph
            
        except Exception as e:
            logging.error(f"❌ [SUPERVISOR_BUILDER] Failed to create supervisor graph: {e}")
            raise e 