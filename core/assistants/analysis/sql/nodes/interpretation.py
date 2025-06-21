import json
import logging
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from doorbeen.core.assistants.analysis.sql.query.understanding import QueryUnderstandingEngine, QueryUnderstanding
from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.ts_model import TSModel


class InterpretInputNode(TSModel):
    handler: ModelHandler

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        logging.info("🚀 [INTERPRET_NODE] Starting input interpretation")
        logging.info(f"🔍 [INTERPRET_NODE] Input question: {state.input}")
        
        try:
            configuration = config.get("configurable", {})
            assert state.grade is not None, "Grade should be present in the state"
            connection: CommonSQLClient = configuration.get("connection", None)
            
            # Log connection status
            if connection:
                logging.info("✅ [INTERPRET_NODE] Database connection available")
            else:
                logging.warning("⚠️ [INTERPRET_NODE] No database connection found")
            
            # Use schema from state if available, otherwise load from connection
            if state.table_schemas:
                logging.info("✅ [INTERPRET_NODE] Using cached table schemas from state")
                table_schemas = state.table_schemas
            else:
                logging.info("🔍 [INTERPRET_NODE] Loading table schemas from database")
                table_schemas = connection.get_schema()
                logging.info(f"✅ [INTERPRET_NODE] Loaded {len(table_schemas.tables)} tables")
            
            # Get selected tables
            selected_tables = connection.get_table_names(schema_name=connection.credentials.database)
            
            # Check if we have enrichment context
            enriched_question = getattr(state, 'enriched_question', None)
            if enriched_question and enriched_question != state.input:
                logging.info(f"🔍 [INTERPRET_NODE] Using enriched question: {enriched_question}")
                question_to_interpret = enriched_question
            else:
                logging.info("🔍 [INTERPRET_NODE] Using original question (no enrichment)")
                question_to_interpret = state.input
            
            # Log enrichment context if available
            assumptions_made = getattr(state, 'assumptions_made', [])
            enrichment_strategy = getattr(state, 'enrichment_strategy', None)
            
            if assumptions_made:
                logging.info(f"🔍 [INTERPRET_NODE] Enrichment context available:")
                logging.info(f"   - Assumptions: {len(assumptions_made)}")
                logging.info(f"   - Strategy: {enrichment_strategy}")
            
            # Use QueryUnderstandingEngine to get the prompt
            logging.info("🔍 [INTERPRET_NODE] Creating interpretation prompt")
            prompt_message = await QueryUnderstandingEngine(llm=self.handler.model).get_prompt(
                question_to_interpret,
                selected_tables,
                table_schemas
            )
            
            # Create context message
            summarized_content = state.summary
            summarized_context = AIMessage(content=f"Here is a summary of all of the previous conversations\n\n {summarized_content}\n\n")
            
            request_messages = [
                summarized_context,
                prompt_message
            ]
            
            # Call the interpretation function
            logging.info("🔍 [INTERPRET_NODE] Invoking LLM for question interpretation")
            json_llm = self.handler.model.bind(response_format={"type": "json_object"})
            response = await json_llm.ainvoke(request_messages)
            response = json.loads(response.content)
            interpretation = QueryUnderstanding(**response)
            
            logging.info("✅ [INTERPRET_NODE] LLM interpretation completed")
            logging.info(f"🔍 [INTERPRET_NODE] Objective: {interpretation.objective}")
            
            logging.info(f"🔍 [INTERPRET_NODE] Interpretation results:")
            logging.info(f"   - Objective: {interpretation.objective}")
            logging.info(f"   - Reasoning: {interpretation.reasoning}")
            
            # Create result message
            result_message = AIMessage(content=interpretation.model_dump_json())
            
            # Update summary
            summary = state.summary + f"\n\n[INTERPRETATION]: Objective defined as '{interpretation.objective}'"
            summary += f"\nReasoning: {interpretation.reasoning}"
            
            logging.info("✅ [INTERPRET_NODE] Interpretation process completed successfully")
            
            return {
                "messages": [result_message],
                "interpretation": interpretation,
                "table_schemas": table_schemas,
                "summary": summary
            }
            
        except Exception as e:
            logging.error(f"❌ [INTERPRET_NODE] Interpretation failed with error: {str(e)}")
            logging.error(f"❌ [INTERPRET_NODE] Error type: {type(e).__name__}")
            logging.error(f"❌ [INTERPRET_NODE] This may cause downstream failures")
            
            # Return fallback interpretation
            fallback_interpretation = QueryUnderstanding(
                objective=f"Analyze the question: {state.input}",
                reasoning="Basic data analysis due to interpretation error",
                plan={"groups": []},
                tests=[],
                operations=[]
            )
            
            return {
                "messages": [AIMessage(content=f"Interpretation failed: {str(e)}")],
                "interpretation": fallback_interpretation,
                "interpretation_error": str(e),
                "summary": state.summary + f"\n\n[INTERPRETATION ERROR]: {str(e)}"
            }
    
    def _analyze_table_purposes(self, table_schemas) -> str:
        """Analyze what each table might contain based on column names - completely dataset agnostic"""
        analysis = ""
        for table in table_schemas.tables:
            analysis += f"\n• Table: {table.name}\n"
            analysis += f"  Columns ({len(table.columns)} total): "
            
            # Just list column names and types without assumptions
            column_info = []
            for col in table.columns:
                column_info.append(f"{col.name}({col.type})")
            
            analysis += ", ".join(column_info[:5])  # Show first 5 columns
            if len(table.columns) > 5:
                analysis += f", ... and {len(table.columns) - 5} more"
            analysis += "\n"
            
            # Generic categorization without domain-specific assumptions  
            potential_identifiers = [col.name for col in table.columns if 'id' in col.name.lower() or col.name.lower().endswith('_key')]
            potential_timestamps = [col.name for col in table.columns if any(time_word in col.name.lower() for time_word in ['time', 'date', 'timestamp', 'created', 'updated'])]
            potential_categories = [col.name for col in table.columns if any(cat_word in col.name.lower() for cat_word in ['type', 'category', 'status', 'class', 'group'])]
            potential_measurements = [col.name for col in table.columns if col.type.upper() in ['REAL', 'FLOAT', 'DECIMAL', 'NUMERIC', 'INTEGER', 'INT']]
            
            if potential_identifiers:
                analysis += f"  - Potential identifiers: {', '.join(potential_identifiers[:3])}\n"
            if potential_timestamps:
                analysis += f"  - Potential time columns: {', '.join(potential_timestamps[:3])}\n"
            if potential_categories:
                analysis += f"  - Potential category columns: {', '.join(potential_categories[:3])}\n"
            if potential_measurements:
                analysis += f"  - Potential numeric measurements: {', '.join(potential_measurements[:3])}\n"
            
        return analysis 