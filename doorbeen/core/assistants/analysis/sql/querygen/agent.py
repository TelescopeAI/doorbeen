"""
Query Generation Agent

This module implements the main QueryGenerationAgent that orchestrates
the SQL query generation workflow using the Agent Tool-Binding pattern.
The agent coordinates between generation, validation, and error analysis tools.
"""

import logging
import time
from typing import Dict, Any, Optional

from langchain_core.messages import HumanMessage, AIMessage

from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.ts_model import TSModel
from .state import QueryGenerationState, QueryGenerationContext
from .tools import (
    generate_sql_query_tool,
    validate_query_syntax_tool,
    analyze_query_error_tool,
    execute_query_tool,
    set_tool_context
)
from .types import QueryGenerationRequest, QueryGenerationResponse


class QueryGenerationAgent(TSModel):
    """
    Dedicated agent for SQL query generation using the Agent Tool-Binding pattern.
    
    This agent coordinates the complete query generation workflow:
    1. Generate initial query based on objective and context
    2. Validate query syntax and semantics
    3. Analyze and fix errors if needed
    4. Retry with different strategies if necessary
    5. Return final validated query
    """
    
    handler: ModelHandler
    
    def __init__(self, handler: ModelHandler, **kwargs):
        super().__init__(handler=handler, **kwargs)
        self.handler = handler
    
    async def generate_query(
        self,
        request: QueryGenerationRequest,
        connection: CommonSQLClient,
        context: Optional[QueryGenerationContext] = None
    ) -> QueryGenerationResponse:
        """
        Main entry point for query generation.
        
        Args:
            request: Query generation request with objective and context
            connection: Database connection for validation and execution
            context: Additional context for generation process
            
        Returns:
            QueryGenerationResponse with generated query and metadata
        """
        
        logging.info(f"🤖 [QUERY_AGENT] Starting query generation workflow")
        logging.info(f"🎯 [QUERY_AGENT] Objective: {request.objective}")
        
        # Initialize state
        state = QueryGenerationState(
            request=request,
            generation_start_time=time.time()
        )
        
        # Set tool context for the tools to access
        set_tool_context(self.handler, connection)
        
        try:
            # Create agent with all query generation tools
            agent_with_tools = self.handler.model.bind_tools([
                generate_sql_query_tool,
                validate_query_syntax_tool,
                analyze_query_error_tool,
                execute_query_tool
            ])
            
            # Build comprehensive request for the agent
            agent_request = self._build_agent_request(request, context)
            
            # Let the agent orchestrate the query generation process
            response = await agent_with_tools.ainvoke([HumanMessage(content=agent_request)])
            
            # Extract and process the agent's work
            final_result = await self._process_agent_response(response, state, connection)
            
            # Update processing time
            state.total_processing_time = time.time() - state.generation_start_time
            
            logging.info(f"✅ [QUERY_AGENT] Workflow completed in {state.total_processing_time:.2f}s")
            return final_result
            
        except Exception as e:
            logging.error(f"❌ [QUERY_AGENT] Workflow failed: {e}")
            
            # Return error response
            error_response = QueryGenerationResponse(
                success=False,
                query="",
                explanation=f"Query generation workflow failed: {str(e)}",
                confidence=0.0,
                complexity="low",
                error=str(e)
            )
            
            state.final_result = error_response
            state.status = "failed"
            state.total_processing_time = time.time() - state.generation_start_time
            
            return error_response
    
    def _build_agent_request(
        self,
        request: QueryGenerationRequest,
        context: Optional[QueryGenerationContext] = None
    ) -> str:
        """Build comprehensive request for the agent to process"""
        
        agent_request = f"""
I need to generate a high-quality SQL query using the available tools. Here's what I need to accomplish:

**OBJECTIVE**: {request.objective}

**REASONING**: {request.reasoning}

**DATABASE CONTEXT**:
- Database Type: {request.database_type}
- Available Schemas: {request.table_schemas}

**ADDITIONAL CONTEXT**:
"""
        
        if request.selected_tables:
            agent_request += f"- Priority Tables: {', '.join(request.selected_tables)}\n"
        
        if request.exploration_context:
            agent_request += f"- Exploration Findings: {request.exploration_context}\n"
        
        if request.retry_strategy:
            agent_request += f"- Retry Strategy: {request.retry_strategy}\n"
        
        if request.additional_context:
            agent_request += f"- Additional Context: {request.additional_context}\n"
        
        if context:
            agent_request += f"- Query Complexity: {context.query_complexity}\n"
            agent_request += f"- Expected Result Size: {context.expected_result_size}\n"
            
            if context.domain_hints:
                agent_request += f"- Domain Hints: {', '.join(context.domain_hints)}\n"
            
            if context.performance_requirements:
                agent_request += f"- Performance Requirements: {', '.join(context.performance_requirements)}\n"
        
        agent_request += f"""

**WORKFLOW INSTRUCTIONS**:

Please use the available tools to complete this query generation workflow:

1. **Generate Query**: Use the `generate_sql_query_tool` to create an initial SQL query based on the objective and context.

2. **Validate Query**: Use the `validate_query_syntax_tool` to check the generated query for syntax and semantic issues.

3. **Handle Errors** (if needed): If validation fails, use the `analyze_query_error_tool` to understand the issues and generate a corrected version.

4. **Test Query** (optional): You may use the `execute_query_tool` with dry_run=True to further validate the query.

5. **Iterate** (if needed): If the query still has issues, repeat the generation and validation process with the insights gained.

**SUCCESS CRITERIA**:
- Query must be syntactically correct for {request.database_type}
- Query must accomplish the stated objective
- Query should be optimized for performance where possible
- Query should handle edge cases appropriately

Please work through this systematically and provide a final summary of the generated query and its quality.
"""
        
        return agent_request
    
    async def _process_agent_response(
        self,
        response: AIMessage,
        state: QueryGenerationState,
        connection: CommonSQLClient
    ) -> QueryGenerationResponse:
        """Process the agent's response and extract the final query result"""
        
        logging.info("🔍 [QUERY_AGENT] Processing agent response")
        
        # The agent's response will contain tool calls and their results
        # We need to extract the final query from the tool usage
        
        final_query = ""
        final_explanation = ""
        confidence = 0.0
        complexity = "medium"
        potential_issues = []
        
        # Check if the agent used tools and extract results
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logging.info(f"🔧 [QUERY_AGENT] Agent used {len(response.tool_calls)} tools")
            
            # Process tool calls to find the final successful query generation
            for tool_call in response.tool_calls:
                if tool_call['name'] == 'generate_sql_query_tool':
                    # Extract the query generation result
                    tool_args = tool_call.get('args', {})
                    
                    # Execute the tool to get the result
                    try:
                        tool_result = await generate_sql_query_tool.ainvoke(tool_args)
                        
                        if tool_result.get('success', False):
                            final_query = tool_result.get('query', '')
                            final_explanation = tool_result.get('explanation', '')
                            confidence = tool_result.get('confidence', 0.0)
                            complexity = tool_result.get('complexity', 'medium')
                            potential_issues = tool_result.get('potential_issues', [])
                            
                            logging.info("✅ [QUERY_AGENT] Found successful query generation")
                            break
                            
                    except Exception as e:
                        logging.error(f"❌ [QUERY_AGENT] Error processing tool result: {e}")
        
        # If no successful query was found in tool calls, try to extract from response content
        if not final_query and response.content:
            logging.info("🔍 [QUERY_AGENT] Attempting to extract query from response content")
            
            # Try to find SQL query in the response content
            content = response.content
            if 'SELECT' in content.upper() or 'WITH' in content.upper():
                # Simple extraction - in a real implementation, you'd use more sophisticated parsing
                lines = content.split('\n')
                query_lines = []
                in_query = False
                
                for line in lines:
                    line_upper = line.upper().strip()
                    if any(keyword in line_upper for keyword in ['SELECT', 'WITH', 'INSERT', 'UPDATE', 'DELETE']):
                        in_query = True
                    
                    if in_query:
                        query_lines.append(line)
                        if line.strip().endswith(';'):
                            break
                
                if query_lines:
                    final_query = '\n'.join(query_lines).strip()
                    final_explanation = "Query extracted from agent response"
                    confidence = 0.7  # Lower confidence for extracted queries
        
        # Create final response
        if final_query:
            result = QueryGenerationResponse(
                success=True,
                query=final_query,
                explanation=final_explanation,
                confidence=confidence,
                complexity=complexity,
                potential_issues=potential_issues
            )
            
            state.final_result = result
            state.status = "completed"
            
            logging.info("✅ [QUERY_AGENT] Successfully generated query")
            
        else:
            result = QueryGenerationResponse(
                success=False,
                query="",
                explanation="Agent was unable to generate a valid query",
                confidence=0.0,
                complexity="low",
                error="No valid query found in agent response"
            )
            
            state.final_result = result
            state.status = "failed"
            
            logging.error("❌ [QUERY_AGENT] Failed to extract valid query from agent response")
        
        return result
    
    async def quick_generate(
        self,
        objective: str,
        reasoning: str,
        table_schemas: Dict[str, Any],
        connection: CommonSQLClient,
        database_type: str = "sqlite"
    ) -> QueryGenerationResponse:
        """
        Quick query generation for simple use cases.
        
        Args:
            objective: What the query should accomplish
            reasoning: Why this query is needed
            table_schemas: Available database schemas
            connection: Database connection
            database_type: Target database type
            
        Returns:
            QueryGenerationResponse with generated query
        """
        
        request = QueryGenerationRequest(
            objective=objective,
            reasoning=reasoning,
            table_schemas=table_schemas,
            database_type=database_type
        )
        
        return await self.generate_query(request, connection)
    
    def get_supported_databases(self) -> list[str]:
        """Get list of supported database types"""
        return [
            "sqlite",
            "postgresql", 
            "mysql",
            "oracle",
            "bigquery",
            "snowflake"
        ]
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about this agent"""
        return {
            "name": "QueryGenerationAgent",
            "version": "1.0.0",
            "description": "Dedicated agent for SQL query generation using Agent Tool-Binding pattern",
            "supported_databases": self.get_supported_databases(),
            "tools": [
                "generate_sql_query_tool",
                "validate_query_syntax_tool", 
                "analyze_query_error_tool",
                "execute_query_tool"
            ],
            "capabilities": [
                "SQL query generation",
                "Syntax validation",
                "Error analysis and correction",
                "Performance optimization",
                "Multi-database support"
            ]
        } 