import logging
from typing import List, Dict, Any, Tuple, Union, Optional

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from doorbeen.core.assistants.analysis.sql.query.understanding import QueryUnderstanding
from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.assistants.toolkit.sql import TSSQLToolkit
from doorbeen.core.connections.clients.NoSQL.mongo import MongoDBClient
from doorbeen.core.connections.clients.SQL.bigquery import BigQueryClient
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.observe import QueryAnalysisReport
from doorbeen.core.types.sql_schema import DatabaseSchema
from doorbeen.core.types.ts_model import TSModel


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
        """Build a SQL query based on the interpretation and table schemas"""
        # Check if we're in a retry scenario with a specific strategy
        retry_strategy = None
        if state.summary and "[RETRY STRATEGY]:" in state.summary:
            # Extract the last retry strategy mentioned
            summary_lines = state.summary.split('\n')
            for line in reversed(summary_lines):
                if "[RETRY STRATEGY]:" in line:
                    retry_strategy = line.split("[RETRY STRATEGY]:")[1].strip()
                    break
        
        logging.info(f"🔍 [QUERY_GENERATOR] Building query with retry strategy: {retry_strategy}")
        
        # Apply strategy-specific modifications to the approach
        strategy_guidance = self._get_strategy_guidance(retry_strategy) if retry_strategy else ""
        
        system_prompt = self._construct_prompt()
        input_prompt = self._format_input_prompt(interpretation, selected_tables, table_schemas,
                                                 state.query_observation_report, strategy_guidance)
        
        # CRITICAL FIX: Don't force tool choice, let LLM decide what tools to use
        db_tools = TSSQLToolkit(client=self.client, handler=self.handler).get_sql_toolkit().get_tools()
        json_llm = self.handler.model.bind(response_format={"type": "json_object"})
        
        # Check if exploration findings exist and include them
        exploration_context = ""
        if hasattr(state, 'exploration_findings') and state.exploration_findings:
            exploration_context = f"\nData Exploration Findings:\n{state.exploration_findings}\n"
        
        summarized_content = state.summary
        summarized_context = AIMessage(content=f"Here is a summary of all previous conversations\n\n{summarized_content}\n\n{exploration_context}")
        
        request_messages = [
            summarized_context,
            SystemMessage(content=system_prompt),
            HumanMessage(content=input_prompt)
        ]
        
        # Use JSON LLM directly for query generation without forcing tool usage
        response = json_llm.invoke(request_messages)
        return response

    def analyze_and_fix_query(self, erroneous_query: str, error_message: str, selected_tables: List[str],
                              table_schemas: DatabaseSchema) -> Tuple[str, str, Dict[str, Any]]:
        # Get database type for context
        db_type = self.client.credentials.dialect.value
        
        # Get database-specific guidance for error fixing
        dialect_guidance = self._get_error_fixing_guidance(db_type.lower())
        
        prompt = f"""
        The following SQL query resulted in an error:

        Database Type: {db_type}

        Query:
        {erroneous_query}

        Error:
        {error_message}

        Table Schemas:
        {self._format_schema_info(table_schemas)}

        {dialect_guidance}

        Please analyze what went wrong with this query and provide:
        1. An explanation of why the query failed
        2. A corrected version of the query that uses proper {db_type} syntax

        Your response should be in the following format:
        Explanation: [Your explanation here]
        Corrected Query: [Your corrected SQL query here]
        """

        # Use the handler's model for correction
        llm = self.handler.model
        response = llm.invoke(prompt)

        explanation, corrected_query = self._extract_explanation_and_query(response.content)

        # Return simplified response without usage stats for now
        return corrected_query, explanation, {}

    def _get_error_fixing_guidance(self, db_type: str) -> str:
        """Get database-specific guidance for fixing common SQL errors"""
        
        if db_type == 'postgresql':
            return """
PostgreSQL Error Fixing Guidance:
- If you see "function does not exist" errors, check:
  * Use ROUND(column_name::numeric, precision) instead of ROUND(column_name, precision)
  * Use DATE_TRUNC() instead of strftime() for date operations
  * Use TO_CHAR() instead of DATE_FORMAT() for date formatting
  * Use EXTRACT() instead of YEAR(), MONTH(), DAY() functions
  * Use ILIKE for case-insensitive matching instead of LIKE with LOWER()
- PostgreSQL is case-sensitive for unquoted identifiers
- Use proper casting with :: operator (e.g., column_name::text)
"""

        elif db_type == 'mysql':
            return """
MySQL Error Fixing Guidance:
- If you see syntax errors, check:
  * Use DATE_FORMAT() for date formatting instead of TO_CHAR()
  * Use IFNULL() or COALESCE() for NULL handling
  * Use CONCAT() for string concatenation instead of ||
  * Use proper LIMIT syntax: LIMIT n instead of ROWNUM
  * MySQL uses backticks for identifiers with spaces: `column name`
"""

        elif db_type == 'sqlite':
            return """
SQLite Error Fixing Guidance:
- If you see function errors, check:
  * Use strftime() for all date operations and formatting
  * Use || for string concatenation instead of CONCAT()
  * SQLite has limited built-in functions - avoid complex date arithmetic
  * Use CAST() for explicit type conversions
  * Window functions have limited support in older SQLite versions
"""

        elif db_type == 'oracle':
            return """
Oracle Error Fixing Guidance:
- If you see ORA- errors, check:
  * Use TO_CHAR() for date formatting
  * Use NVL() instead of IFNULL() for NULL handling
  * Use ROWNUM for limiting results instead of LIMIT
  * Oracle requires explicit date conversions with TO_DATE()
  * Use proper dual table for single-value selects: SELECT value FROM dual
"""

        else:
            return """
General SQL Error Fixing Guidance:
- Check for database-specific function syntax
- Verify proper data type casting and conversions
- Ensure column names and table names are correctly referenced
- Check for proper NULL handling syntax for your database
- Verify date/time function compatibility with your database type
"""

    def _format_input_prompt(self, interpretation: QueryUnderstanding, selected_tables: List[str],
                             table_schemas: DatabaseSchema,
                             query_observation_report: Optional[QueryAnalysisReport] = None,
                             strategy_guidance: str = "") -> str:
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
        - Query Effectiveness: {"Yes" if query_observation_report.query and query_observation_report.query.query_effective else "No"}
        """
            if query_observation_report.query and query_observation_report.query.met_reasons:
                met_reasons = "\n".join([f"- {reason}" for reason in query_observation_report.query.met_reasons])
                human_prompt += f"""
        Met Objectives Reasons:
        {met_reasons}
        """

            if query_observation_report.query and query_observation_report.query.unmet_reasons:
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

        # Add strategy guidance
        human_prompt += f"""
        Strategy Guidance:
        {strategy_guidance}
        """

        return human_prompt

    def _construct_prompt(self) -> str:
        # Get database type for dialect-specific instructions
        db_type = self.client.credentials.dialect.value.lower()

        # Base instructions that apply to all databases
        base_instructions = """
Given the following user question and table schemas, generate a SQL query to meet the objective:

General Instructions:
1. Generate a SQL query to answer the user's objective.
2. Your output should purely be in JSON and should stick to the JSON Syntax.
3. Make sure that the query should be valid and executable for the database type.
4. Do not include markdown formatting or SQL keywords.
5. Make sure that if a column name contains any whitespace or special characters, it is properly escaped.
6. The query should start directly with the SQL command (e.g., SELECT, INSERT, etc.).
7. IMPORTANT: Use table names EXACTLY as provided in the schema without any prefix. Do NOT add database or schema prefixes unless explicitly shown in the table schemas.
8. Take a look at the example data to understand the structure of the tables. Use appropriate date formats based on the example if required.
9. Make sure to include an explanation of the SQL you're generating in the output. 
10. Never apply a LIMIT clause to the query unless it's required for the objective.
11. Think like a Data Analyst and group the data by one or more column if it makes sense to do so to meet the objective. Always remember that this data would be presented to a non-technical person.
12. You can assume that there might be multiple datapoints for a single entity in the table so you'll have to group by one or more columns to get the desired output. In case if the user has asked for either a specific entity or requested to see all the data, then you can skip the grouping.
13. [OPTIONAL] Use Common Table Expressions (CTEs) if there's a requirement to query a query. Using CTEs is a great way to modularize and break down your code.
14. [OPTIONAL] Use advanced SQL operations like window functions, subqueries, etc. only if required to meet the objective.
"""

        # Database-specific instructions
        dialect_instructions = self._get_dialect_specific_instructions(db_type)

        # JSON format instruction
        json_format = """
[JSON Syntax]
{
    "query": "<Your SQL query here>",
    "logic": "<Explanation about what this query is supposed to do>"
}
"""

        return base_instructions + dialect_instructions + json_format

    def _get_dialect_specific_instructions(self, db_type: str) -> str:
        """Get database-specific SQL syntax instructions"""
        
        if db_type == 'postgresql':
            return """
PostgreSQL-Specific Instructions:
15. For date operations, use PostgreSQL functions:
    - DATE_TRUNC('month', date_column) for truncating dates
    - EXTRACT(YEAR FROM date_column) for extracting date parts
    - TO_CHAR(date_column, 'YYYY-MM') for date formatting
    - AGE(date1, date2) for date differences
16. For rounding numbers: ROUND(column_name::numeric, precision)
17. For string operations: Use ILIKE for case-insensitive matching, || for concatenation
18. For conditional logic: Use CASE WHEN ... THEN ... ELSE ... END
19. For NULL handling: Use COALESCE(column, default_value)
20. For JSON operations: Use -> for JSON field access, ->> for text extraction
21. Window functions: Use OVER (PARTITION BY ... ORDER BY ...) for analytics
22. Array operations: Use ARRAY_AGG() for aggregating into arrays
23. For regex: Use ~ for regex matching, ~* for case-insensitive regex
"""

        elif db_type == 'mysql':
            return """
MySQL-Specific Instructions:
15. For date operations, use MySQL functions:
    - DATE_FORMAT(date_column, '%Y-%m') for date formatting
    - YEAR(date_column), MONTH(date_column), DAY(date_column) for date parts
    - DATEDIFF(date1, date2) for date differences
    - NOW() for current timestamp
16. For rounding numbers: ROUND(column_name, precision)
17. For string operations: Use LIKE for pattern matching, CONCAT() for concatenation
18. For conditional logic: Use CASE WHEN ... THEN ... ELSE ... END
19. For NULL handling: Use IFNULL(column, default_value) or COALESCE()
20. For string functions: Use SUBSTRING(), LENGTH(), LOWER(), UPPER()
21. Window functions: Use OVER (PARTITION BY ... ORDER BY ...) for analytics
22. For grouping: Use GROUP_CONCAT() for string aggregation
23. Use LIMIT for row limiting, not TOP
"""

        elif db_type == 'sqlite':
            return """
SQLite-Specific Instructions:
15. For date operations, use SQLite functions:
    - strftime('%Y-%m', date_column) for date formatting
    - strftime('%Y', date_column) for year extraction
    - DATE(date_column) for date conversion
    - datetime('now') for current timestamp
16. For rounding numbers: ROUND(column_name, precision)
17. For string operations: Use LIKE for pattern matching, || for concatenation
18. For conditional logic: Use CASE WHEN ... THEN ... ELSE ... END
19. For NULL handling: Use COALESCE(column, default_value)
20. Limited window function support - use carefully
21. For aggregation: Use GROUP_CONCAT() for string aggregation
22. Data types are flexible but be explicit with CAST() when needed
23. Use LIMIT for row limiting
"""

        elif db_type == 'oracle':
            return """
Oracle-Specific Instructions:
15. For date operations, use Oracle functions:
    - TO_CHAR(date_column, 'YYYY-MM') for date formatting
    - EXTRACT(YEAR FROM date_column) for date parts
    - TRUNC(date_column, 'MM') for date truncation
    - SYSDATE for current date
16. For rounding numbers: ROUND(column_name, precision)
17. For string operations: Use LIKE for pattern matching, || for concatenation
18. For conditional logic: Use CASE WHEN ... THEN ... ELSE ... END
19. For NULL handling: Use NVL(column, default_value) or COALESCE()
20. Window functions: Use OVER (PARTITION BY ... ORDER BY ...) for analytics
21. For aggregation: Use LISTAGG() for string aggregation
22. Use ROWNUM for row limiting (e.g., WHERE ROWNUM <= 10)
23. Be explicit with data type conversions using TO_NUMBER(), TO_DATE()
"""

        elif db_type in ['bigquery', 'snowflake', 'redshift']:
            return """
Modern SQL Warehouse Instructions:
15. For date operations, use standard SQL functions:
    - DATE_TRUNC(date_column, MONTH) for date truncation
    - EXTRACT(YEAR FROM date_column) for date parts
    - FORMAT_DATE('%Y-%m', date_column) for formatting (BigQuery)
    - CURRENT_DATE() for current date
16. For rounding numbers: ROUND(column_name, precision)
17. For string operations: Use LIKE for pattern matching, CONCAT() for concatenation
18. For conditional logic: Use CASE WHEN ... THEN ... ELSE ... END
19. For NULL handling: Use COALESCE(column, default_value)
20. Full window function support: Use OVER (PARTITION BY ... ORDER BY ...)
21. For aggregation: Use STRING_AGG() or ARRAY_AGG() as appropriate
22. Use LIMIT for row limiting
23. Advanced analytics functions available (PERCENTILE_CONT, etc.)
"""

        else:
            # Generic SQL instructions for unknown databases
            return """
Standard SQL Instructions:
15. For date operations: Use standard SQL functions where possible
16. For rounding: ROUND(column_name, precision)
17. For string operations: Use LIKE, basic string functions
18. Use CASE WHEN ... THEN ... ELSE ... END for conditional logic
19. Use COALESCE() for NULL handling
20. Window functions: OVER (PARTITION BY ... ORDER BY ...)
21. Use LIMIT for row limiting where supported
22. Be conservative with database-specific functions
"""

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

    def _get_strategy_guidance(self, strategy: str) -> str:
        """Get specific guidance based on the retry strategy"""
        strategy_instructions = {
            "refine_interpretation": """
        **RETRY STRATEGY - REFINE INTERPRETATION**:
        - Re-examine the original question with fresh perspective
        - Look for alternative interpretations or implicit requirements
        - Consider if the question asks for related but different data
        - Use broader search terms and more flexible matching criteria
        """,
            "broader_search": """
        **RETRY STRATEGY - BROADER SEARCH**:
        - Use less restrictive WHERE clauses and filtering
        - Include related data that might provide context
        - Look for patterns rather than exact matches
        - Consider using LIKE operators with wildcards for text searches
        - Include adjacent time periods or similar categories
        """,
            "alternative_tables": """
        **RETRY STRATEGY - ALTERNATIVE TABLES**:
        - Consider using different tables that might contain relevant data
        - Look for lookup tables, dimension tables, or fact tables
        - Join multiple tables to get a more complete picture
        - Consider aggregated data sources if detail data is unavailable
        """,
            "simplified_query": """
        **RETRY STRATEGY - SIMPLIFIED QUERY**:
        - Start with the most basic possible query that could provide any relevant data
        - Remove complex conditions and focus on core data availability
        - Use simple SELECT statements without complex aggregations initially
        - Focus on getting any data first, then refine
        """,
            "related_analysis": """
        **RETRY STRATEGY - RELATED ANALYSIS**:
        - Look for related metrics or data that could provide insights
        - Consider proxy measurements or alternative indicators
        - Explore data patterns that might indirectly answer the question
        - Focus on trends, correlations, or comparative analysis
        """
        }
        
        return strategy_instructions.get(strategy, "")

    def _get_human_prompt(self, interpretation: QueryUnderstanding, selected_tables: List[str], table_schemas: DatabaseSchema,
                          state: SQLAssistantState, strategy_guidance: str = ""):
        # Implementation of _get_human_prompt method
        pass
