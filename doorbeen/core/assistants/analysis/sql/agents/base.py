from abc import abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import Field

from doorbeen.core.types.ts_model import TSModel
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState
from doorbeen.core.assistants.analysis.sql.context.agent_contexts import AgentHandoff


class BaseAgent(TSModel):
    """Base class for all SQL analysis agents in the multi-agent system"""
    
    name: str = Field(description="Name of the agent")
    agent_type: str = Field(description="Type/role of the agent")
    max_retries: int = Field(description="Maximum number of retries allowed")
    current_retries: int = Field(default=0, description="Current number of retries")
    description: str = Field(description="Description of agent's purpose and capabilities")
    
    # Agent capabilities and tools
    available_tools: List[str] = Field(default_factory=list, description="List of available tools")
    required_context: List[str] = Field(default_factory=list, description="Required context for operation")
    
    @abstractmethod
    async def execute(self, state: SQLSupervisorState) -> SQLSupervisorState:
        """
        Execute the agent's primary function
        
        Args:
            state: Current SQL supervisor context
            
        Returns:
            Updated context after agent execution
        """
        pass
    
    @abstractmethod
    def can_handle_request(self, state: SQLSupervisorState) -> bool:
        """
        Determine if this agent can handle the current request
        
        Args:
            state: Current SQL supervisor context
            
        Returns:
            True if agent can handle the request, False otherwise
        """
        pass
    
    @abstractmethod
    def get_handoff_reasoning(self, state: SQLSupervisorState, target_agent: str) -> str:
        """
        Get reasoning for why this agent should hand off to another agent
        
        Args:
            state: Current SQL supervisor context
            target_agent: Name of the target agent
            
        Returns:
            Reasoning string for the handoff
        """
        pass
    
    def can_retry(self) -> bool:
        """Check if agent can attempt another retry"""
        return self.current_retries < self.max_retries
    
    def increment_retry(self, error_message: str = ""):
        """Increment retry count and log the attempt"""
        self.current_retries += 1
        # Log the retry attempt in agent coordination context
        # This will be handled by the supervisor
    
    def reset_retries(self):
        """Reset retry count (used when agent successfully completes)"""
        self.current_retries = 0
    
    def create_handoff(self, target_agent: str, state: SQLSupervisorState, reason: str = None) -> AgentHandoff:
        """
        Create a handoff to another agent
        
        Args:
            target_agent: Name of the target agent
            state: Current context
            reason: Reason for handoff (if not provided, uses get_handoff_reasoning)
            
        Returns:
            AgentHandoff object
        """
        if reason is None:
            reason = self.get_handoff_reasoning(state, target_agent)
        
        return AgentHandoff(
            source_agent=self.name,
            target_agent=target_agent,
            reason=reason,
            context=self.get_handoff_context(state)
        )
    
    def get_handoff_context(self, state: SQLSupervisorState) -> Dict[str, Any]:
        """
        Get context to pass during handoff
        
        Args:
            state: Current context
            
        Returns:
            Context dictionary for handoff
        """
        return {
            "agent_type": self.agent_type,
            "retries_used": self.current_retries,
            "max_retries": self.max_retries,
            "tools_available": self.available_tools,
        }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status for monitoring"""
        return {
            "name": self.name,
            "type": self.agent_type,
            "retries": f"{self.current_retries}/{self.max_retries}",
            "can_retry": self.can_retry(),
            "tools": self.available_tools,
            "description": self.description,
        }
    
    async def handle_error(self, error: Exception, state: SQLSupervisorState) -> SQLSupervisorState:
        """
        Handle errors that occur during agent execution
        
        Args:
            error: The exception that occurred
            state: Current context
            
        Returns:
            Updated context with error handling
        """
        error_message = str(error)
        
        # Update agent retry configuration in coordination context
        agent_retry_config = state.agent_coordination.get_agent_retry_config(self.name)
        agent_retry_config.increment_retry("error_retry", error_message)
        
        # Mark agent as failed if no more retries
        if not agent_retry_config.can_retry:
            state.agent_coordination.mark_agent_failed(self.name)
        
        # Add error to context
        state.error = {
            "agent": self.name,
            "error": error_message,
            "retry_count": agent_retry_config.current_retries,
            "can_retry": agent_retry_config.can_retry,
        }
        
        return state
    
    def log_completion(self, state: SQLSupervisorState, success: bool = True):
        """
        Log agent completion
        
        Args:
            state: Current context
            success: Whether agent completed successfully
        """
        if success:
            state.agent_coordination.mark_agent_completed(self.name)
            self.reset_retries()
        else:
            state.agent_coordination.mark_agent_failed(self.name)
    
    def update_agent_context(self, state: SQLSupervisorState, context_updates: Dict[str, Any]):
        """
        Update agent-specific context in the coordination context
        
        Args:
            state: Current context
            context_updates: Updates to apply to agent context
        """
        # This will be implemented by specific agents to update their contexts
        pass
    
    def get_agent_context(self, state: SQLSupervisorState) -> Dict[str, Any]:
        """
        Get agent-specific context from coordination context
        
        Args:
            state: Current context
            
        Returns:
            Agent-specific context
        """
        # This will be implemented by specific agents to return their contexts
        return {}
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = True 