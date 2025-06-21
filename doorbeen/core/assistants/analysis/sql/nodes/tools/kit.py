import json
import logging
from typing import List, Dict, Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

# Import QueryGen tools
from doorbeen.core.assistants.analysis.sql.querygen.tools import (
    set_tool_context
)
from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.generate import GeneratedSQLQuery
from doorbeen.core.types.ts_model import TSModel


class DataExplorationNode(TSModel):
    """
    Enhanced Data Exploration Node using QueryGen Agent Tools
    
    This node combines domain detection with the QueryGen agent tools
    for intelligent data exploration using the Agent Tool-Binding pattern.
    """
    
    handler: ModelHandler

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        """
        Explore the database to understand what data exists before generating queries.
        This phase includes DOMAIN DETECTION to identify domain-specific tables and patterns.
        """
        logging.info("🚀 [DATA_EXPLORATION] Starting enhanced data exploration with QueryGen tools")
        logging.info(f"🔍 [DATA_EXPLORATION] Question: {state.input}")
        
        try:
            configuration = config.get("configurable", {})
            connection: CommonSQLClient = configuration.get("connection", None)
            
            # Log connection status
            if connection:
                logging.info("✅ [DATA_EXPLORATION] Database connection available")
            else:
                logging.warning("⚠️ [DATA_EXPLORATION] No database connection found")
                raise Exception("Database connection required for data exploration")
            
            # Use schema from state
            selected_tables = state.selected_tables or connection.get_table_names(schema_name=connection.credentials.database)
            table_schemas = state.table_schemas or connection.get_schema()
            
            logging.info(f"🔍 [DATA_EXPLORATION] Available tables: {len(selected_tables)}")
            logging.info(f"🔍 [DATA_EXPLORATION] Tables: {', '.join(selected_tables[:5])}{'...' if len(selected_tables) > 5 else ''}")
            
            # Set tool context for QueryGen tools
            set_tool_context(self.handler, connection)
            
            # 🎯 PHASE 1: DOMAIN DETECTION using LLM
            logging.info("🔍 [DATA_EXPLORATION] PHASE 1: Starting domain detection")
            domain_detection_results = await self._detect_domain_and_tables(state.input, selected_tables, table_schemas)
            
            # Priority tables identified by domain detection
            priority_tables = domain_detection_results.get("priority_tables", [])
            domain_insights = domain_detection_results.get("domain_insights", "")
            potential_patterns = domain_detection_results.get("potential_patterns", [])
            
            logging.info(f"✅ [DATA_EXPLORATION] Domain detection completed:")
            logging.info(f"   - Priority tables: {priority_tables}")
            logging.info(f"   - Potential patterns: {len(potential_patterns)}")
            logging.info(f"   - Domain insights length: {len(domain_insights)} chars")
            
            # 🎯 PHASE 2: INTELLIGENT EXPLORATION using QueryGen Agent Tools
            logging.info("🔍 [DATA_EXPLORATION] PHASE 2: Starting intelligent exploration with QueryGen tools")
            
            # Execute predefined exploration queries for priority tables
            executed_queries = []
            
            logging.info(f"🔧 [DATA_EXPLORATION] Executing exploration queries for {len(priority_tables)} priority tables")
            
            for table in priority_tables[:3]:  # Limit to top 3 tables to avoid overwhelming
                try:
                    # Import the execute tool
                    from doorbeen.core.assistants.analysis.sql.querygen.tools import execute_query_tool
                    
                    # Query 1: Sample data structure
                    sample_query = f"SELECT * FROM {table} LIMIT 5;"
                    logging.info(f"🔧 [DATA_EXPLORATION] Executing sample query for {table}")
                    
                    sample_result = await execute_query_tool.ainvoke({
                        'query': sample_query,
                        'dry_run': False,
                        'limit': 5
                    })
                    
                    if sample_result.get('success'):
                        executed_queries.append({
                            'type': 'executed',
                            'objective': f'Explore {table} table structure',
                            'query': sample_query,
                            'success': True,
                            'row_count': sample_result.get('row_count', 0),
                            'results': sample_result.get('results', []),
                            'explanation': f'Sample data from {table} to understand structure and content'
                        })
                        logging.info(f"✅ [DATA_EXPLORATION] Sample query for {table}: {sample_result.get('row_count', 0)} rows")
                    
                    # Query 2: Data volume
                    count_query = f"SELECT COUNT(*) as total_rows FROM {table};"
                    logging.info(f"🔧 [DATA_EXPLORATION] Executing count query for {table}")
                    
                    count_result = await execute_query_tool.ainvoke({
                        'query': count_query,
                        'dry_run': False,
                        'limit': 1
                    })
                    
                    if count_result.get('success'):
                        executed_queries.append({
                            'type': 'executed',
                            'objective': f'Check {table} data volume',
                            'query': count_query,
                            'success': True,
                            'row_count': count_result.get('row_count', 0),
                            'results': count_result.get('results', []),
                            'explanation': f'Total record count in {table} table'
                        })
                        logging.info(f"✅ [DATA_EXPLORATION] Count query for {table}: {count_result.get('row_count', 0)} rows")
                    
                except Exception as e:
                    logging.error(f"❌ [DATA_EXPLORATION] Failed to explore {table}: {e}")
                    executed_queries.append({
                        'type': 'executed',
                        'objective': f'Explore {table} table',
                        'query': f'-- Failed to execute queries for {table}',
                        'success': False,
                        'row_count': 0,
                        'explanation': f'Error exploring {table}: {str(e)}'
                    })
            
            # Process exploration results with actual tool outputs
            exploration_findings = await self._process_exploration_results(None, priority_tables, executed_queries)
            
            logging.info(f"✅ [DATA_EXPLORATION] Exploration completed with {len(exploration_findings)} findings")
            
            # Update state with findings
            summary = state.summary or ""
            summary += "\n\n[CURRENT OPERATION: Enhanced Data Exploration with QueryGen]\n"
            summary += f"Domain detection identified {len(priority_tables)} priority tables.\n"
            summary += f"Exploration findings: {exploration_findings}\n"
            
            # Format executed queries for frontend display
            structured_queries = []
            if executed_queries:
                for query_info in executed_queries:
                    structured_queries.append({
                        "objective": query_info.get('objective', 'Database Exploration'),
                        "query": query_info['query'],
                        "status": "success" if query_info.get('success', False) else "failed",
                        "rowCount": query_info.get('row_count', 0),
                        "results": query_info.get('results', []),
                        "explanation": query_info.get('explanation', '')
                    })
            
            result_message = AIMessage(
                content=json.dumps({
                    "exploration_complete": True,
                    "priority_tables": priority_tables,
                    "domain_insights": domain_insights,
                    "findings": exploration_findings,
                    "patterns_found": potential_patterns,
                    "exploration_queries": structured_queries
                })
            )
            
            return {
                "messages": [result_message],
                "exploration_findings": exploration_findings,
                "exploration_queries": structured_queries,
                "data_exploration_complete": True,
                "selected_tables": priority_tables if priority_tables else selected_tables,
                "summary": summary
            }
            
        except Exception as e:
            logging.error(f"❌ [DATA_EXPLORATION] Exploration failed: {e}")
            
            # Return error state
            error_summary = f"\n\n[ERROR: Data Exploration Failed]\n{str(e)}\n"
            summary = (state.summary or "") + error_summary
            
            error_message = AIMessage(
                content=json.dumps({
                    "exploration_complete": False,
                    "error": str(e),
                    "findings": "Exploration failed - proceeding with available table information",
                    "exploration_queries": []
                })
            )
            
            return {
                "messages": [error_message],
                "exploration_findings": f"Exploration failed: {str(e)}",
                "exploration_queries": [],
                "data_exploration_complete": False,
                "summary": summary
            }
    
    async def _detect_domain_and_tables(self, user_question: str, available_tables: list, table_schemas) -> dict:
        """
        Detect domain and identify priority tables using LLM analysis.
        This is the core domain detection logic preserved from the original implementation.
        """
        logging.info("🔍 [DOMAIN_DETECTION] Starting domain analysis")
        
        try:
            # Build schema summary for domain detection
            schema_summary = self._build_schema_summary_for_domain_detection(table_schemas)
        
            domain_prompt = f"""
You are a domain expert who analyzes database schemas to identify the most relevant tables and patterns for a given question.

USER QUESTION: {user_question}

AVAILABLE TABLES AND SCHEMA SUMMARY:
{schema_summary}

Your task is to analyze this question and database schema to:

1. **IDENTIFY THE DOMAIN**: What domain/industry does this question belong to? (e.g., e-commerce, healthcare, finance, HR, etc.)

2. **PRIORITY TABLES**: Which 3-5 tables are most likely to contain data relevant to answering this question?

3. **POTENTIAL PATTERNS**: What specific data patterns, column names, or relationships should we look for?

4. **DOMAIN INSIGHTS**: What domain-specific knowledge can guide our exploration?

Please provide your analysis in the following JSON format:
{{
    "domain": "identified domain",
    "priority_tables": ["table1", "table2", "table3"],
    "potential_patterns": ["pattern1", "pattern2"],
    "domain_insights": "Detailed explanation of domain context and why these tables are relevant",
    "exploration_strategy": "How to approach exploring this domain's data"
}}

Focus on being specific and actionable in your recommendations.
"""
            
            # Use JSON-bound LLM for structured response
            json_llm = self.handler.model.bind(response_format={"type": "json_object"})
            response = await json_llm.ainvoke([HumanMessage(content=domain_prompt)])
            
            # Parse domain detection results
            domain_data = json.loads(response.content)
            
            # Validate and filter priority tables to ensure they exist
            valid_priority_tables = [
                table for table in domain_data.get("priority_tables", [])
                if table in available_tables
            ]
            
            result = {
                "domain": domain_data.get("domain", "unknown"),
                "priority_tables": valid_priority_tables,
                "potential_patterns": domain_data.get("potential_patterns", []),
                "domain_insights": domain_data.get("domain_insights", ""),
                "exploration_strategy": domain_data.get("exploration_strategy", "")
            }
            
            logging.info(f"✅ [DOMAIN_DETECTION] Identified domain: {result['domain']}")
            logging.info(f"✅ [DOMAIN_DETECTION] Priority tables: {valid_priority_tables}")
            
            return result
            
        except Exception as e:
            logging.error(f"❌ [DOMAIN_DETECTION] Domain detection failed: {e}")
            
            # Fallback to simple table selection
            return {
                "domain": "unknown",
                "priority_tables": available_tables[:5],  # Take first 5 tables as fallback
                "potential_patterns": [],
                "domain_insights": f"Domain detection failed: {str(e)}. Using fallback approach.",
                "exploration_strategy": "Systematic exploration of available tables"
            }
    
    def _build_exploration_request(
        self, 
        user_question: str, 
        priority_tables: list, 
        domain_insights: str,
        potential_patterns: list, 
        all_tables: list, 
        table_schemas
    ) -> str:
        """Build comprehensive exploration request for the QueryGen agent"""
        
        request = f"""
I need to systematically explore this database to understand what data exists that could help answer the user's question.

**USER QUESTION**: {user_question}

**DOMAIN CONTEXT**:
{domain_insights}

**PRIORITY TABLES** (explore these first): {', '.join(priority_tables) if priority_tables else 'None identified'}
**POTENTIAL PATTERNS** to look for: {', '.join(potential_patterns) if potential_patterns else 'Generic patterns'}
**ALL AVAILABLE TABLES**: {', '.join(all_tables)}

**EXPLORATION STRATEGY**:

Please use the available tools to conduct a systematic exploration:

1. **Priority Table Exploration**:
   - Use `generate_sql_query_tool` to create queries for exploring priority tables
   - Use `execute_query_tool` to run sample queries (SELECT * LIMIT 5, COUNT(*), etc.)
   - Focus on understanding data structure, volume, and quality

2. **Pattern Verification**:
   - Look for the specific patterns identified in domain analysis
   - Check for data completeness in key columns
   - Identify temporal ranges and data freshness

3. **Relationship Discovery**:
   - Explore connections between priority tables
   - Look for foreign key relationships
   - Understand data flow and dependencies

4. **Data Quality Assessment**:
   - Check for NULL values in important columns
   - Assess data volume and distribution
   - Identify any data quality issues

**INSTRUCTIONS**:
- Use the `generate_sql_query_tool` to create appropriate exploration queries
- Use the `execute_query_tool` to actually run the queries and gather real data
- Focus on actionable insights that will help with query generation
- Report concrete findings based on actual data, not assumptions

Start with the priority tables and work systematically through the exploration strategy.
"""
        
        return request
    
    async def _execute_agent_tool_calls(self, response: AIMessage, state: SQLAssistantState, selected_tables: list, table_schemas, exploration_context: str) -> List[Dict[str, Any]]:
        """Execute the agent's tool calls and capture their actual outputs"""
        
        executed_queries = []
        
        # Debug: Check if response has tool_calls
        logging.info(f"🔍 [DEBUG] Response type: {type(response)}")
        logging.info(f"🔍 [DEBUG] Response has tool_calls attr: {hasattr(response, 'tool_calls')}")
        if hasattr(response, 'tool_calls'):
            logging.info(f"🔍 [DEBUG] Number of tool_calls: {len(response.tool_calls) if response.tool_calls else 0}")
            if response.tool_calls:
                for i, tc in enumerate(response.tool_calls):
                    logging.info(f"🔍 [DEBUG] Tool call {i}: {tc.get('name', 'unknown')} with args: {list(tc.get('args', {}).keys())}")
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logging.info(f"🔧 [DATA_EXPLORATION] Executing {len(response.tool_calls)} tool calls from agent")
            
            for i, tool_call in enumerate(response.tool_calls, 1):
                tool_name = tool_call.get('name', 'unknown')
                tool_args = tool_call.get('args', {})
                
                logging.info(f"🔧 [DATA_EXPLORATION] Processing tool call {i}: {tool_name}")
                
                try:
                    if tool_name == 'generate_sql_query_tool':
                        logging.info(f"🔧 [DATA_EXPLORATION] Executing generate_sql_query_tool with objective: {tool_args.get('objective', 'Unknown')}")
                        
                        # Import and execute the tool
                        from doorbeen.core.assistants.analysis.sql.querygen.tools import generate_sql_query_tool
                        
                        # Add missing context to tool arguments
                        complete_args = self._complete_tool_args_for_generation(tool_args, state, selected_tables, table_schemas, exploration_context)
                        logging.info(f"🔧 [DATA_EXPLORATION] Complete args keys: {list(complete_args.keys())}")
                        
                        result = await generate_sql_query_tool.ainvoke(complete_args)
                        logging.info(f"🔧 [DATA_EXPLORATION] Tool result: success={result.get('success')}, query_length={len(result.get('query', ''))}")
                        
                        if result.get('success') and result.get('query'):
                            executed_queries.append({
                                'type': 'generated',
                                'objective': tool_args.get('objective', 'Unknown'),
                                'query': result['query'],
                                'explanation': result.get('explanation', ''),
                                'tool_call_index': i
                            })
                            logging.info(f"✅ [DATA_EXPLORATION] Generated query {i}: {result['query']}")
                        else:
                            logging.error(f"❌ [DATA_EXPLORATION] Query generation failed for tool call {i}: {result.get('error', 'Unknown error')}")
                    
                    elif tool_name == 'execute_query_tool':
                        logging.info(f"🔧 [DATA_EXPLORATION] Executing execute_query_tool")
                        
                        # Import and execute the tool
                        from doorbeen.core.assistants.analysis.sql.querygen.tools import execute_query_tool
                        
                        query = tool_args.get('query', '')
                        logging.info(f"🔧 [DATA_EXPLORATION] Query to execute: {query}")
                        
                        result = await execute_query_tool.ainvoke(tool_args)
                        logging.info(f"🔧 [DATA_EXPLORATION] Execution result: success={result.get('success')}, rows={result.get('row_count', 0)}")
                        
                        executed_queries.append({
                            'type': 'executed',
                            'query': query,
                            'success': result.get('success', False),
                            'row_count': result.get('row_count', 0),
                            'results': result.get('results', []),
                            'tool_call_index': i
                        })
                        
                        if result.get('success'):
                            logging.info(f"✅ [DATA_EXPLORATION] Executed query {i}: {query} ({result.get('row_count', 0)} rows)")
                        else:
                            logging.error(f"❌ [DATA_EXPLORATION] Query execution failed for tool call {i}: {result.get('error', 'Unknown error')}")
                    
                    else:
                        logging.warning(f"⚠️ [DATA_EXPLORATION] Unknown tool: {tool_name}")
                
                except Exception as e:
                    logging.error(f"❌ [DATA_EXPLORATION] Error executing tool call {i} ({tool_name}): {e}")
                    import traceback
                    logging.error(f"❌ [DATA_EXPLORATION] Traceback: {traceback.format_exc()}")
        else:
            logging.warning("⚠️ [DATA_EXPLORATION] No tool calls found in agent response")
        
        logging.info(f"🔧 [DATA_EXPLORATION] Executed {len(executed_queries)} tool calls successfully")
        return executed_queries
    
    def _complete_tool_args_for_generation(self, tool_args: Dict[str, Any], state: SQLAssistantState, selected_tables: list, table_schemas, exploration_context: str) -> Dict[str, Any]:
        """Complete tool arguments with context that only the node has access to"""
        
        # Convert DatabaseSchema object to dictionary if needed
        if hasattr(table_schemas, 'model_dump'):
            table_schemas_dict = table_schemas.model_dump()
        elif isinstance(table_schemas, dict):
            table_schemas_dict = table_schemas
        else:
            table_schemas_dict = {}
        
        # Build complete arguments by merging agent args with node context
        complete_args = {
            'objective': tool_args.get('objective', f'Explore data for: {state.input}'),
            'reasoning': tool_args.get('reasoning', 'Data exploration to understand available information'),
            'table_schemas': table_schemas_dict,
            'exploration_context': exploration_context,
            'database_type': tool_args.get('database_type', 'postgresql'),
            'selected_tables': selected_tables,
            'additional_context': tool_args.get('additional_context')
        }
        
        return complete_args
    
    async def _process_exploration_results(self, response: AIMessage = None, priority_tables: list = None, executed_queries: List[Dict[str, Any]] = None) -> str:
        """Process the agent's exploration results and extract findings"""
        
        findings = []
        actual_queries = []
        
        # Extract content from agent response (if available)
        if response and response.content:
            findings.append(f"Agent Analysis: {response.content}")
        
        # Process the actual executed queries if available
        if executed_queries:
            findings.append(f"Successfully executed {len(executed_queries)} exploration operations:")
            
            for query_info in executed_queries:
                if query_info['type'] == 'generated':
                    findings.append(f"- Generated query for: {query_info['objective']}")
                    findings.append(f"  Query: {query_info['query']}")
                    if query_info.get('explanation'):
                        findings.append(f"  Explanation: {query_info['explanation']}")
                    actual_queries.append(query_info['query'])
                    
                elif query_info['type'] == 'executed':
                    status = "✅ Success" if query_info['success'] else "❌ Failed"
                    findings.append(f"- Executed query ({status}): {query_info['query']}")
                    if query_info['success']:
                        findings.append(f"  Results: {query_info['row_count']} rows returned")
                    actual_queries.append(query_info['query'])
        
        # Fallback: Process tool calls from response if executed_queries is empty and response exists
        elif response and hasattr(response, 'tool_calls') and response.tool_calls:
            findings.append(f"Agent attempted {len(response.tool_calls)} tool calls:")
            
            for i, tool_call in enumerate(response.tool_calls, 1):
                tool_name = tool_call.get('name', 'unknown')
                tool_args = tool_call.get('args', {})
                
                if tool_name == 'execute_query_tool':
                    query = tool_args.get('query', 'Unknown query')
                    findings.append(f"- Query {i}: {query}")
                    actual_queries.append(query)
                elif tool_name == 'generate_sql_query_tool':
                    objective = tool_args.get('objective', 'Unknown objective')
                    findings.append(f"- Generated query for: {objective}")
        
        # If no findings yet, add a default message
        if not findings:
            findings.append("Direct database exploration completed")
        
        # Log the actual queries for debugging
        if actual_queries:
            logging.info(f"🔍 [DATA_EXPLORATION] Captured {len(actual_queries)} actual queries:")
            for i, query in enumerate(actual_queries, 1):
                logging.info(f"   Query {i}: {query}")
        
        # Combine all findings
        exploration_summary = "\n".join(findings)
        
        # Add priority table information
        if priority_tables:
            exploration_summary += f"\n\nPriority tables identified: {', '.join(priority_tables)}"
        
        # Add executed queries section for better visibility
        if actual_queries:
            exploration_summary += f"\n\n📋 Exploration Queries Executed ({len(actual_queries)} total):"
            for i, query in enumerate(actual_queries, 1):
                exploration_summary += f"\n{i}. {query}"
        
        return exploration_summary
    
    def _build_schema_summary_for_domain_detection(self, table_schemas) -> str:
        """Build a concise schema summary for domain detection"""
        
        if not table_schemas:
            return "No schema information available"
        
        summary = ""
        
        # Handle different schema formats
        tables = []
        if hasattr(table_schemas, 'tables'):
            tables = table_schemas.tables
        elif isinstance(table_schemas, dict) and 'tables' in table_schemas:
            tables = table_schemas['tables']
        elif isinstance(table_schemas, list):
            tables = table_schemas
        
        for table in tables:
            table_name = table.name if hasattr(table, 'name') else table.get('name', 'unknown')
            summary += f"\n• Table: {table_name}\n"
            
            # Get columns
            columns = []
            if hasattr(table, 'columns'):
                columns = table.columns
            elif isinstance(table, dict) and 'columns' in table:
                columns = table['columns']
            
            if columns:
                column_info = []
                for col in columns[:10]:  # Limit to first 10 columns
                    col_name = col.name if hasattr(col, 'name') else col.get('name', 'unknown')
                    col_type = col.type if hasattr(col, 'type') else col.get('type', 'unknown')
                    column_info.append(f"{col_name}({col_type})")
                
                summary += f"  Columns: {', '.join(column_info)}"
                if len(columns) > 10:
                    summary += f", ... and {len(columns) - 10} more"
                summary += "\n"
        
        return summary


# Keep the existing SQLToolkitNode for backward compatibility
class SQLToolkitNode(TSModel):
    handler: ModelHandler

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        configuration = config.get("configurable", {})
        assert state.should_enrich, "Only enrich if the state should be enriched"
        assert state.grade is not None, "Grade should be present in the state"
        connection: CommonSQLClient = configuration.get("connection", None)
        
        # Use schema from state instead of reloading
        selected_tables = state.selected_tables or connection.get_table_names(schema_name=connection.credentials.database)
        table_schemas = state.table_schemas or connection.get_schema()
        
        # For backward compatibility, use the original QueryGenerator
        from doorbeen.core.assistants.analysis.sql.query.generate import QueryGenerator
        query_generator = QueryGenerator(handler=self.handler, client=connection)
        generated_query = await query_generator.build_query(state.interpretation, selected_tables, table_schemas, state)

        output = {
            "messages": [
                AIMessage(content=generated_query.content)
            ],
            "generated_query": GeneratedSQLQuery(query=json.loads(generated_query.content)['query'])
        }
        return output