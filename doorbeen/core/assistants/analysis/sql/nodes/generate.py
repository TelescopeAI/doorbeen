import json
import logging

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.generate import GeneratedSQLQuery
from doorbeen.core.types.ts_model import TSModel

# Import the new QueryGen tools
from doorbeen.core.assistants.analysis.sql.querygen.tools import (
    generate_sql_query_tool,
    validate_query_syntax_tool,
    analyze_query_error_tool,
    set_tool_context
)
from doorbeen.core.assistants.analysis.sql.querygen.types import QueryGenerationRequest


class GenerateSQLQueryNode(TSModel):
    """
    SQL Query Generation Node using QueryGen Agent Tools
    
    This node now uses the Agent Tool-Binding pattern where the LLM agent
    decides which tools to use for query generation, validation, and error handling.
    """
    
    handler: ModelHandler

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        logging.info("🚀 [GENERATE_NODE] Starting query generation with QueryGen agent tools")
        
        try:
            configuration = config.get("configurable", {})
            connection: CommonSQLClient = configuration.get("connection", None)
            
            if not connection:
                logging.error("❌ [GENERATE_NODE] No database connection available")
                return self._create_error_response("No database connection available", state)
            
            # Prepare context for query generation
            selected_tables = state.selected_tables or connection.get_table_names(schema_name=connection.credentials.database)
            table_schemas = state.table_schemas.model_dump() if state.table_schemas else connection.get_schema().model_dump()
            exploration_context = getattr(state, 'exploration_findings', None)
            
            # Build objective and reasoning from context
            objective = self._build_objective_from_state(state)
            reasoning = self._build_reasoning_from_state(state)
            
            # Set tool context for the querygen tools
            set_tool_context(self.handler, connection)
            
            # Create agent with query generation tools
            query_agent = self.handler.model.bind_tools([
                generate_sql_query_tool,
                validate_query_syntax_tool,
                analyze_query_error_tool
            ])
            
            # Let the agent decide how to generate the best query
            agent_request = f"""
            I need to generate a high-quality SQL query for this analysis task.
            
            **OBJECTIVE**: {objective}
            
            **REASONING**: {reasoning}
            
            **DATABASE CONTEXT**:
            - Database Type: {connection.credentials.dialect.value if hasattr(connection.credentials, 'dialect') else "sqlite"}
            - Available Schemas: {json.dumps(table_schemas, indent=2)}
            - Selected Tables: {selected_tables}
            
            **ADDITIONAL CONTEXT**:
            - Original Question: {state.input}
            - Interpretation Available: {state.interpretation is not None}
            """
            
            if exploration_context:
                agent_request += f"- Data Exploration Findings: {exploration_context}\n"
            
            if hasattr(state, 'enriched_question') and state.enriched_question:
                agent_request += f"- Enriched Question: {state.enriched_question}\n"
            
            # Check for retry context
            retry_strategy = self._get_retry_strategy_from_state(state)
            if retry_strategy:
                agent_request += f"- Retry Strategy: {retry_strategy}\n"
            
            agent_request += """
            
            **INSTRUCTIONS**:
            
            Please use the available tools to generate the best possible SQL query:
            
            1. **Generate Query**: Use `generate_sql_query_tool` to create a SQL query that accomplishes the objective
            2. **Validate Query**: Use `validate_query_syntax_tool` to ensure the query is syntactically correct
            3. **Handle Errors** (if needed): If validation fails, use `analyze_query_error_tool` to fix issues
            
            **SUCCESS CRITERIA**:
            - Query must be syntactically correct for the target database
            - Query should accomplish the stated objective effectively
            - Query should be optimized for performance where possible
            - Query should handle edge cases appropriately
            
            Work systematically through the tools to ensure a high-quality result.
            """
            
            logging.info("🤖 [GENERATE_NODE] Invoking agent with query generation tools")
            response = await query_agent.ainvoke([HumanMessage(content=agent_request)])
            
            # Extract the generated query from the agent's tool usage
            generated_query_result = await self._extract_query_from_agent_response(response, state, table_schemas, selected_tables, exploration_context)
            
            if generated_query_result and generated_query_result.get("success"):
                logging.info("✅ [GENERATE_NODE] Query generated successfully by agent")
                return self._create_success_response(generated_query_result, state)
            else:
                logging.error("❌ [GENERATE_NODE] Agent failed to generate valid query")
                return self._create_error_response("Query generation failed", state)
                
        except Exception as e:
            logging.error(f"❌ [GENERATE_NODE] Query generation failed with exception: {e}")
            return self._create_error_response(f"Query generation failed: {str(e)}", state)
    
    def _build_objective_from_state(self, state: SQLAssistantState) -> str:
        """Build objective from current context"""
        if state.interpretation:
            return state.interpretation.objective
        else:
            return f"Generate SQL query to answer: {state.input}"
    
    def _build_reasoning_from_state(self, state: SQLAssistantState) -> str:
        """Build reasoning from current context"""
        reasoning_parts = []
        
        if state.interpretation:
            reasoning_parts.append(f"Interpretation reasoning: {state.interpretation.reasoning}")
        
        if hasattr(state, 'exploration_findings') and state.exploration_findings:
            reasoning_parts.append("Data exploration has been performed to understand available data")
        
        if hasattr(state, 'enriched_question') and state.enriched_question:
            reasoning_parts.append("Question has been enriched with additional context")
        
        if not reasoning_parts:
            reasoning_parts.append(f"Need to generate SQL query for user question: {state.input}")
        
        return ". ".join(reasoning_parts)
    
    def _get_retry_strategy_from_state(self, state: SQLAssistantState) -> str:
        """Extract retry strategy from context if available"""
        if hasattr(state, 'objective_retry_strategies') and state.objective_retry_strategies:
            return state.objective_retry_strategies[-1]  # Get the latest strategy
        return None
    
    async def _extract_query_from_agent_response(self, response: AIMessage, state: SQLAssistantState, table_schemas: dict, selected_tables: list, exploration_context: str) -> dict:
        """Extract the generated query from agent's tool usage"""
        
        # Check if the agent used the generate_sql_query_tool
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.get('name') == 'generate_sql_query_tool':
                    try:
                        # Get the tool arguments from the agent
                        agent_args = tool_call.get('args', {})
                        
                        # Build the complete tool arguments with context from the node
                        tool_args = {
                            'objective': agent_args.get('objective', self._build_objective_from_state(state)),
                            'reasoning': agent_args.get('reasoning', self._build_reasoning_from_state(state)),
                            'table_schemas': table_schemas,
                            'exploration_context': exploration_context,
                            'database_type': agent_args.get('database_type', 'postgresql'),
                            'selected_tables': selected_tables,
                            'additional_context': agent_args.get('additional_context')
                        }
                        
                        # Add retry strategy if available
                        retry_strategy = self._get_retry_strategy_from_state(state)
                        if retry_strategy:
                            tool_args['retry_strategy'] = retry_strategy
                        
                        result = await generate_sql_query_tool.ainvoke(tool_args)
                        return result
                    except Exception as e:
                        logging.error(f"❌ [GENERATE_NODE] Error executing generate tool: {e}")
        
        # Fallback: try to extract query from response content
        if response.content:
            try:
                # Look for JSON in the response
                content = response.content
                if '{' in content and '}' in content:
                    # Try to extract JSON
                    start = content.find('{')
                    end = content.rfind('}') + 1
                    json_str = content[start:end]
                    parsed = json.loads(json_str)
                    
                    if 'query' in parsed:
                        return {
                            "success": True,
                            "query": parsed['query'],
                            "explanation": parsed.get('explanation', 'Query extracted from agent response'),
                            "confidence": parsed.get('confidence', 0.7)
                        }
            except Exception as e:
                logging.error(f"❌ [GENERATE_NODE] Error parsing response content: {e}")
        
        return None
    
    def _create_success_response(self, query_result: dict, state: SQLAssistantState) -> dict:
        """Create successful response with generated query"""
        
        generated_query = GeneratedSQLQuery(query=query_result['query'])
        
        # Update summary
        summary = state.summary or ""
        summary += "\n\n[CURRENT OPERATION: Query Generation with QueryGen Agent]\n"
        summary += f"Successfully generated SQL query using Agent Tool-Binding pattern.\n"
        summary += f"Query confidence: {query_result.get('confidence', 'N/A')}\n"
        
        if query_result.get('explanation'):
            summary += f"Query explanation: {query_result['explanation']}\n"
        
        if state.exploration_findings:
            summary += "Data exploration findings were used to inform this query.\n"
        
        summary += f"Generated Query: {generated_query.query}\n"
        
        result_message = AIMessage(
            content=generated_query.model_dump_json()
        )
        
        return {
            "messages": [result_message],
            "generated_query": generated_query,
            "summary": summary
        }
    
    def _create_error_response(self, error_message: str, state: SQLAssistantState) -> dict:
        """Create error response when query generation fails"""
        
        summary = state.summary or ""
        summary += f"\n\n[ERROR: Query Generation Failed]\n{error_message}\n"
        
        error_message_obj = AIMessage(
            content=json.dumps({
                "error": error_message,
                "query": "",
                "success": False
            })
        )
        
        return {
            "messages": [error_message_obj],
            "generated_query": None,
            "summary": summary,
            "error": error_message
        }
