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
        configuration = config.get("configurable", {})
        assert state.generated_query is not None, "Generated query should be present in the state"
        connection: CommonSQLClient = configuration.get("connection", None)
        generated_query = state.generated_query
        try:
            result = connection.query(generated_query.query)
            output = ExecutionResults(query=generated_query.query, result=result, error=None)
        except Exception as e:
            sql_exceptions = [CSQLInvalidQuery]
            is_sql_error = False
            error = None
            if any([isinstance(e, exception) for exception in sql_exceptions]):
                error = e.message
                is_sql_error = True
            else:
                logging.error(f"Error executing query: {e}")
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
        else:
            summary += f"This error occurred: {output.error}\n"

        output = {
            "messages": [result_message],
            "execution_results": [output],
            "last_execution_failed": last_execution_failed,
            "summary": summary
        }
        return output


class AnalyseExecutionFailure(TSModel):
    handler: ModelHandler

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        configuration = config.get("configurable", {})
        is_last_execution_failed = state.last_execution_failed is not None and state.last_execution_failed
        assert is_last_execution_failed, "This node should only be called if the last execution failed"
        connection: CommonSQLClient = configuration.get("connection", None)
        failed_execution = state.execution_results[-1]
        error = failed_execution.error
        selected_tables = connection.get_table_names(schema_name=connection.credentials.database)
        table_schemas = connection.get_schema()
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
