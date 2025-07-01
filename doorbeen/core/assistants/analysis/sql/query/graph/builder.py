import json
import logging
from typing import Any

from langgraph.constants import START, END
from langgraph.graph import StateGraph

from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.ts_model import TSModel


class SQLGraphBuilder(TSModel):
    """
    Factory class that creates either Linear or Supervisor graphs based on mode.
    
    Two completely separate architectures:
    1. Linear: Uses traditional nodes with conditional routing
    2. Supervisor: Uses LangGraph agents with supervisor coordination
    """
    
    handler: ModelHandler
    question: str
    
    def build_linear_graph(self, checkpointer: Any):
        """Build the traditional linear node graph"""
        from doorbeen.core.assistants.analysis.sql.query.graph.linear_builder import LinearGraphBuilder
        
        logging.info("📝 [GRAPH_BUILDER] Building LINEAR graph with traditional nodes")
        
        linear_builder = LinearGraphBuilder(
            handler=self.handler,
            question=self.question
        )
        
        return linear_builder.build(checkpointer)
    
    def build_supervisor_graph(self, checkpointer: Any):
        """Build the supervisor-based multi-agent graph"""
        from doorbeen.core.assistants.analysis.sql.query.graph.supervisor_builder import SupervisorGraphBuilder
        
        logging.info("🤖 [GRAPH_BUILDER] Building SUPERVISOR graph with LangGraph agents")
        
        supervisor_builder = SupervisorGraphBuilder(
            handler=self.handler,
            question=self.question
        )
        
        return supervisor_builder.build(checkpointer)
    
    def build(self, mode: str, checkpointer: Any):
        """
        Build the appropriate graph based on mode
        
        Args:
            mode: "linear" or "supervisor"
            checkpointer: LangGraph checkpointer
            
        Returns:
            Compiled graph for the specified mode
        """
        if mode == "linear":
            return self.build_linear_graph(checkpointer)
        elif mode == "supervisor":
            return self.build_supervisor_graph(checkpointer)
        else:
            raise ValueError(f"Unknown mode: {mode}. Must be 'linear' or 'supervisor'")
