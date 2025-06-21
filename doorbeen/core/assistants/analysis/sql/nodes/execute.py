import json
import logging

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.assistants.utils.sql import convert_sqlalchemy_rows_to_dict
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.exceptions.SQLClients import CSQLInvalidQuery
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.execute import ExecutionResults, CorrectedSQLQuery
from doorbeen.core.types.generate import GeneratedSQLQuery
from doorbeen.core.types.sql_schema import DatabaseSchema
from doorbeen.core.types.ts_model import TSModel


class ExecuteSQLQueryNode(TSModel):
    handler: ModelHandler

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        logging.info("🚀 [EXECUTE_NODE] Starting SQL query execution")
        
        # CRITICAL: Circuit breaker check FIRST
        if getattr(state, 'circuit_breaker_triggered', False):
            logging.warning("⚠️ [EXECUTE_NODE] Circuit breaker already triggered - aborting execution")
            return {
                "circuit_breaker_triggered": True,
                "execution_failed": True,
                "error_message": "Circuit breaker triggered - execution aborted",
                "last_execution_failed": True,
                "messages": [AIMessage(content="Execution aborted due to circuit breaker")]
            }
        
        # Check retry limits before attempting execution
        retry_count = getattr(state, 'retry_count', 0)
        max_retries = getattr(state, 'max_retries', 3)
        logging.info(f"🔍 [EXECUTE_NODE] Retry status: {retry_count}/{max_retries}")
        
        if retry_count >= max_retries:
            logging.warning(f"⚠️ [EXECUTE_NODE] Retry limit exceeded - triggering circuit breaker")
            state.circuit_breaker_triggered = True
            return {
                "circuit_breaker_triggered": True,
                "execution_failed": True,
                "error_message": f"Maximum retry limit ({max_retries}) exceeded",
                "retry_count_exceeded": True,
                "last_execution_failed": True,
                "messages": [AIMessage(content=f"Execution terminated after {max_retries} failed attempts")]
            }
        
        configuration = config.get("configurable", {})
        assert state.generated_query is not None, "Generated query should be present in the state"
        connection: CommonSQLClient = configuration.get("connection", None)
        generated_query = state.generated_query
        
        logging.info(f"🔍 [EXECUTE_NODE] Executing query: {generated_query.query}")
        logging.info(f"🔍 [EXECUTE_NODE] Database connection: {'Available' if connection else 'Missing'}")
        
        try:
            logging.info("🔍 [EXECUTE_NODE] Attempting query execution...")
            result = connection.query(generated_query.query)
            output = ExecutionResults(query=generated_query.query, result=result, error=None)
            
            logging.info("✅ [EXECUTE_NODE] Query executed successfully")
            logging.info(f"🔍 [EXECUTE_NODE] Result count: {len(result) if result else 0}")
            
            # SUCCESS: Reset circuit breaker state
            state.retry_count = 0
            state.circuit_breaker_triggered = False
            state.execution_error_history.clear()
            state.last_execution_error = None
            
            logging.info("✅ [EXECUTE_NODE] Circuit breaker state reset after successful execution")
            
        except Exception as e:
            logging.error(f"❌ [EXECUTE_NODE] Query execution failed: {str(e)}")
            logging.error(f"❌ [EXECUTE_NODE] Error type: {type(e).__name__}")
            
            # Handle failed transaction state first
            error_str = str(e).lower()
            if "transaction is aborted" in error_str or "commands ignored until end of transaction" in error_str:
                logging.info("🔄 [EXECUTE_NODE] Attempting transaction rollback...")
                try:
                    # Try to rollback the failed transaction
                    connection.query("ROLLBACK;")
                    logging.info("✅ [EXECUTE_NODE] Transaction rolled back, retrying query...")
                    # Retry the original query after rollback
                    result = connection.query(generated_query.query)
                    output = ExecutionResults(query=generated_query.query, result=result, error=None)
                    
                    logging.info("✅ [EXECUTE_NODE] Query succeeded after rollback")
                    
                    # SUCCESS after rollback: Reset circuit breaker state
                    state.retry_count = 0
                    state.circuit_breaker_triggered = False
                    state.execution_error_history.clear()
                    state.last_execution_error = None
                    
                except Exception as retry_error:
                    logging.error(f"❌ [EXECUTE_NODE] Retry after rollback also failed: {str(retry_error)}")
                    # If retry also fails, treat as failure
                    e = retry_error
            
            # If we reach here, it's a genuine failure
            if 'output' not in locals():
                logging.warning("⚠️ [EXECUTE_NODE] Handling execution failure")
                
                # FAILURE: Update circuit breaker state
                state.retry_count += 1
                state.last_execution_error = str(e)
                state.execution_error_history.append(str(e))
                
                logging.info(f"🔍 [EXECUTE_NODE] Updated retry count: {state.retry_count}/{state.max_retries}")
                logging.info(f"🔍 [EXECUTE_NODE] Can retry: {state.can_retry}")
                
                # Check if we should trigger circuit breaker
                if not state.can_retry:
                    logging.warning("⚠️ [EXECUTE_NODE] TRIGGERING CIRCUIT BREAKER - no more retries available")
                    state.circuit_breaker_triggered = True
                
            sql_exceptions = [CSQLInvalidQuery]
            is_sql_error = False
            error = None
            if any([isinstance(e, exception) for exception in sql_exceptions]):
                error = e.message
                is_sql_error = True
                logging.info(f"🔍 [EXECUTE_NODE] Identified as SQL error: {error}")
            else:
                logging.error(f"❌ [EXECUTE_NODE] General execution error: {e}")
                error = str(e)
            output = ExecutionResults(query=generated_query.query, result=None, error=error,
                                      is_sql_error=is_sql_error)

        result_message = AIMessage(
            content=output.model_dump_json(exclude={'result'})
        )
        last_execution_failed = output.error is not None and output.result is None
        summary = state.summary
        summary += "\n\n[CURRENT OPERATION: SQL Query Execution]\n"
        summary += (f"We tried executing this query and it was {'' if output.error is None else 'not'} successful."
                    f"Here are some details about the execution output.\n")
        summary += f"Query: {generated_query.query}\n\n"
        
        # Add circuit breaker status to summary
        if state.retry_count > 0:
            summary += f"[Circuit Breaker Status: Retry {state.retry_count}/{state.max_retries}]\n"
        
        if state.circuit_breaker_triggered:
            summary += f"[CIRCUIT BREAKER TRIGGERED: Execution terminated]\n"
            logging.warning("⚠️ [EXECUTE_NODE] Circuit breaker status added to summary")
        
        if not last_execution_failed:
            result_count = 0 if output.result is None else len(output.result)
            RESULT_SUMMARY_THRESHOLD = 30
            summary += f"There are {result_count} records in the result of the executed query.\n"
            included_results = output.result[:RESULT_SUMMARY_THRESHOLD] if output.result is not None else []
            if len(included_results) > 0:
                included_results = convert_sqlalchemy_rows_to_dict(included_results)
            if result_count > RESULT_SUMMARY_THRESHOLD:
                summary += (f"The results displayed below have been trimmed due to memory limitations. Execute the query "
                            f"if required to access the full set of results\n Query: {generated_query.query}\n")
            for result in included_results:
                summary += json.dumps(result, indent=2) + "\n"
            
            logging.info(f"✅ [EXECUTE_NODE] Execution completed successfully with {result_count} results")
        else:
            summary += f"This error occurred: {output.error}\n"
            logging.error(f"❌ [EXECUTE_NODE] Execution failed with error: {output.error}")

        execution_result = {
            "messages": [result_message],
            "execution_results": [output],
            "last_execution_failed": last_execution_failed,
            "summary": summary,
            "retry_count": state.retry_count,
            "circuit_breaker_triggered": state.circuit_breaker_triggered
        }
        
        logging.info(f"🔍 [EXECUTE_NODE] Execution node completed:")
        logging.info(f"   - Success: {not last_execution_failed}")
        logging.info(f"   - Retry count: {state.retry_count}")
        logging.info(f"   - Circuit breaker: {state.circuit_breaker_triggered}")
        
        return execution_result


class AnalyseExecutionFailure(TSModel):
    handler: ModelHandler

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        logging.info("🚀 [FAILURE_ANALYSIS] Starting execution failure analysis")
        
        # CRITICAL: Check circuit breaker before analyzing failure
        if not state.can_retry:
            error_msg = f"Circuit breaker triggered - cannot retry after {state.retry_count} failed attempts"
            logging.warning(f"⚠️ [FAILURE_ANALYSIS] {error_msg}")
            return {
                "circuit_breaker_triggered": True,
                "execution_failed": True,
                "error_message": error_msg,
                "retry_count_exceeded": True,
                "last_execution_failed": True,
                "messages": [AIMessage(content=f"Analysis terminated due to circuit breaker: {error_msg}")]
            }
        
        configuration = config.get("configurable", {})
        is_last_execution_failed = state.last_execution_failed is not None and state.last_execution_failed
        assert is_last_execution_failed, "This node should only be called if the last execution failed"
        connection: CommonSQLClient = configuration.get("connection", None)
        failed_execution = state.execution_results[-1]
        error = failed_execution.error
        
        logging.info(f"🔍 [FAILURE_ANALYSIS] Analyzing failure: {error}")
        logging.info(f"🔍 [FAILURE_ANALYSIS] Failed query: {failed_execution.query}")
        
        # Use schema from state instead of reloading
        selected_tables = state.selected_tables or connection.get_table_names(schema_name=connection.credentials.database)
        table_schemas = state.table_schemas or connection.get_schema()
        
        logging.info(f"🔍 [FAILURE_ANALYSIS] Using {len(selected_tables)} tables for analysis")
        
        formatted_schema = self._format_schema_info(table_schemas)
        examples = connection.get_examples(selected_tables)
        system_prompt = f"""
You have just generated a query which resulted in an error. Take a look at the error message below and provide 
an explanation of why the query failed and a corrected version of the query. You were supposed to meet the
task objective but the query failed.

Instructions:
1. Provide an explanation of why the query failed.
2. Provide a corrected version of the query.
3. Make sure the output is in JSON format only.

JSON Format:
{{{{
    "explanation": "Your explanation about why it failed",
    "corrected_query": "Your corrected SQL query here",
    "modification_plan": "What changes did you make and how are they supposed to fix the issue"
}}}}
"""
        input_prompt = f"""
Objective: {state.interpretation.objective}

Error: {error}

Query: {failed_execution.query}

Table Schemas:
{formatted_schema}

Selected Tables:
{selected_tables}

Example Data:
{examples}

        """
        summarized_content = state.summary
        summarized_context = AIMessage(content=f"Here is a summary of all of the previous "
                                               f"conversations\n\n {summarized_content}\n\n")
        request_messages = [
            summarized_context,
            SystemMessage(content=system_prompt),
            AIMessage(content=input_prompt)
        ]
        
        logging.info("🔍 [FAILURE_ANALYSIS] Invoking LLM for failure analysis")
        
        json_llm = self.handler.model.bind(response_format={"type": "json_object"})
        response = json_llm.invoke(request_messages)
        response = json.loads(response.content)
        corrected_query = CorrectedSQLQuery(**response, raw_query=failed_execution.query)
        updated_query = GeneratedSQLQuery(query=corrected_query.corrected_query)
        result_message = AIMessage(
            content=corrected_query.model_dump_json()
        )

        summary = state.summary
        summary += "\n\n[CURRENT OPERATION: Analyse Why SQL Execution Failed]\n"
        summary += f"This is the reason why the query failed and what approach we've taken to fix it.\n\n"
        summary += corrected_query.model_dump_json(indent=2) + "\n"
        summary += f"[Circuit Breaker Status: Attempt {state.retry_count + 1}/{state.max_retries}]\n"
        
        logging.info("✅ [FAILURE_ANALYSIS] Failure analysis completed")
        logging.info(f"🔍 [FAILURE_ANALYSIS] Corrected query: {corrected_query.corrected_query}")
        
        output = {
            "messages": [result_message],
            "generated_query": updated_query,
            "summary": summary
        }
        return output

    def _format_schema_info(self, database_schema: DatabaseSchema) -> str:
        schema_info = ""
        for table in database_schema.tables:
            schema_info += f"Table: {table.name}\n"
            for column in table.columns:
                schema_info += f"  - {column.name}: {column.type}\n"
            schema_info += "\n"
        return schema_info
