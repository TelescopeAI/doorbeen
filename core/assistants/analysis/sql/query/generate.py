from typing import List, Dict, Any, Tuple, Union, Optional

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from core.assistants.analysis.sql.query.understanding import QueryUnderstanding
from core.assistants.analysis.sql.state import SQLAssistantState
from core.assistants.hooks.callback import CallbackManager
from core.assistants.toolkit.sql import TSSQLToolkit
from core.connections.clients.NoSQL.mongo import MongoDBClient
from core.connections.clients.SQL.bigquery import BigQueryClient
from core.connections.clients.SQL.common import CommonSQLClient
from core.models.provider import ModelProvider, ModelHandler
from core.types.observe import QueryAnalysisReport
from core.types.sql_schema import DatabaseSchema
from core.types.ts_model import TSModel


class QueryAttempt(TSModel):
    query: str
    error: str | None
    reasoning: str | None


class QueryGenerator(TSModel):
    handler: ModelHandler
    client: Union[CommonSQLClient, BigQueryClient, MongoDBClient]

    async def build_query(self, interpretation: QueryUnderstanding,
                          selected_tables: List[str],
                          table_schemas: DatabaseSchema,
                          state: SQLAssistantState
                          ) -> AIMessage:
        system_prompt = self._construct_prompt()
        input_prompt = self._format_input_prompt(interpretation, selected_tables, table_schemas,
                                                 state.query_observation_report)
        db_tools = TSSQLToolkit(client=self.client, handler=self.handler).get_sql_toolkit().get_tools()
        json_llm = self.handler.model.bind(response_format={"type": "json_object"})
        llm_with_tools = json_llm.bind_tools(tools=db_tools, tool_choice="sql_db_query_checker")
        response = None
        called_tool = False
        summarized_content = state.summary
        summarized_context = AIMessage(content=f"Here is a summary of all of the previous "
                                               f"conversations\n\n {summarized_content}\n\n")
        request_messages = [
            summarized_context,
            SystemMessage(content=system_prompt),
            HumanMessage(content=input_prompt)
        ]
        response = llm_with_tools.invoke(request_messages)
        called_tool = len(response.tool_calls) > 0
        assert called_tool is not False, "No tool was called"
        if called_tool:
            response.content = response.tool_calls[0]['args']
        return response

    def analyze_and_fix_query(self, erroneous_query: str, error_message: str, selected_tables: List[str],
                              table_schemas: DatabaseSchema) -> Tuple[str, str, Dict[str, Any]]:
        prompt = f"""
        The following SQL query resulted in an error:

        Query:
        {erroneous_query}

        Error:
        {error_message}

        Table Schemas:
        {self._format_schema_info(selected_tables, table_schemas)}

        Please analyze what went wrong with this query and provide:
        1. An explanation of why the query failed
        2. A corrected version of the query

        Your response should be in the following format:
        Explanation: [Your explanation here]
        Corrected Query: [Your corrected SQL query here]
        """

        llm = ModelProvider().get_model_instance(self.model.name, api_key=self.model.api_key, plaintext=True)

        with CallbackManager.get_callback(self.model.provider, self.model.name) as cb:
            response = llm.invoke(prompt)

            if hasattr(cb, 'update'):
                cb.update(response)

        usage_stats = CallbackManager.get_usage_from_callback(cb, self.model.provider, self.model.name)

        explanation, corrected_query = self._extract_explanation_and_query(response.content)

        return corrected_query, explanation, usage_stats

    def _format_input_prompt(self, interpretation: QueryUnderstanding, selected_tables: List[str],
                             table_schemas: DatabaseSchema,
                             query_observation_report: Optional[QueryAnalysisReport] = None) -> str:
        formatted_schema = self._format_schema_info(table_schemas)
        examples = self.client.get_examples(selected_tables)
        selected_tables = ', '.join(selected_tables)

        # Base prompt structure
        human_prompt = f"""
        Database Type: {self.client.credentials.dialect.value}
        DB Schema Name: {self.client.credentials.database}

        Objective: {interpretation.objective}

        Reasoning: {interpretation.reasoning}

        Plan: {interpretation.plan}
        """

        # Add unmet objectives section if they exist
        if (query_observation_report and
                query_observation_report.unmet_objectives and
                len(query_observation_report.unmet_objectives) > 0):

            unmet_objectives = "\n".join([f"- {obj}" for obj in query_observation_report.unmet_objectives])
            human_prompt += f"""
        Unmet Objectives:
        {unmet_objectives}

        Previous Query Insights:
        - Query Effectiveness: {"Yes" if query_observation_report.query.query_effective else "No"}
        """
            if query_observation_report.query.met_reasons:
                met_reasons = "\n".join([f"- {reason}" for reason in query_observation_report.query.met_reasons])
                human_prompt += f"""
        Met Objectives Reasons:
        {met_reasons}
        """

            if query_observation_report.query.unmet_reasons:
                unmet_reasons = "\n".join([f"- {reason}" for reason in query_observation_report.query.unmet_reasons])
                human_prompt += f"""
        Unmet Objectives Reasons:
        {unmet_reasons}
        """

        # Add schema and examples information
        human_prompt += f"""
        Table Schemas:
        {formatted_schema}

        Selected Tables:
        {selected_tables}

        Example Data:
        {examples}
        """

        return human_prompt

    def _construct_prompt(self) -> str:

        base_prompt = f"""
Given the following user question and table schemas, generate a SQL query to meet the objective:

Instructions:
1. Generate a SQL query to answer the user's objective.
2. Your output should purely be in JSON and should stick to the JSON Syntax.
3. Make sure that the query should be valid and executable for the database type.
4. Do not include markdown formatting or SQL keywords.
5. Make sure that if a column name contains any whitespace or special characters, it is properly escaped.
6. The query should start directly with the SQL command (e.g., SELECT, INSERT, etc.).
7. While writing FROM statements, check if DB Schema Name is present. If it's available then always 
prefix the table name with the db_schema name.
8. Take a look at the example data to understand the structure of the tables. Use appropriate date formats
based on the example if required.
8. In case if there are any date or number columns that are stored as strings, please convert them to the
appropriate data type.
9. Make sure to include an explanation of the SQL you're generating in the output. 
10. Never apply a LIMIT clause to the query unless it's required for the objective.
11. Think like a Data Analyst and group the data by one or more column if it makes sense to do so to meet the 
objective. Always remember that this data would be presented to a non-technical person.
12. You can assume that there might be multiple datapoints for a single entity in the table so you'll have to group
by one or more columns to get the desired output. In case if the user has asked for either a specific entity or 
requested to see all the data, then you can skip the grouping.
13. [OPTIONAL] Use Common Table Expressions (CTEs) if there's a requirement to query a query. Using CTEs is a great way to modularize and break down your code.
14. [OPTIONAL] Use advanced SQL operations like window functions, subqueries, etc. only if required to meet the objective.

[JSON Syntax]
{{
    "query": "<Your SQL query here>",
    "logic: "<Explanation about what this query is supposed to do>"
}}


"""
        return base_prompt
        # if previous_attempts:
        #     base_prompt += "\nPrevious attempts and their outcomes:\n"
        #     for i, attempt in enumerate(previous_attempts, 1):
        #         base_prompt += f"\nAttempt {i}:\nQuery: {attempt.query}\n"
        #         if attempt.error:
        #             base_prompt += f"Error: {attempt.error}\n"
        #         if attempt.reasoning:
        #             base_prompt += f"Reasoning: {attempt.reasoning}\n"
        #
        #     base_prompt += "\nPlease consider these previous attempts and their outcomes when generating a new query."
        #
        # base_prompt += "\nGenerate the SQL query:"
        #
        # return base_prompt
        return formatted_prompt[0].content

    def _format_schema_info(self, database_schema: DatabaseSchema) -> str:
        schema_info = ""
        for table in database_schema.tables:
            schema_info += f"Table: {table.name}\n"
            for column in table.columns:
                schema_info += f"  - {column.name}: {column.type}\n"
            schema_info += "\n"
        return schema_info

    def _extract_query(self, model_output: str) -> str:
        # Remove any markdown formatting
        lines = model_output.strip().split('\n')
        cleaned_lines = [line for line in lines if not line.startswith('```')]

        # Join the lines and strip any leading/trailing whitespace
        query = ' '.join(cleaned_lines).strip()

        # If the query starts with 'sql', remove it
        if query.lower().startswith('sql'):
            query = query[3:].strip()

        return query

    def _extract_explanation_and_query(self, model_output: str) -> Tuple[str, str]:
        explanation = ""
        query = ""
        current_section = None

        for line in model_output.split('\n'):
            if line.startswith("Explanation:"):
                current_section = "explanation"
                explanation = line[len("Explanation:"):].strip()
            elif line.startswith("Corrected Query:"):
                current_section = "query"
                query = line[len("Corrected Query:"):].strip()
            elif current_section == "explanation":
                explanation += " " + line.strip()
            elif current_section == "query":
                query += " " + line.strip()

        return explanation.strip(), query.strip()
