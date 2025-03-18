from typing import List, Dict, Optional
from pydantic import Field
from core.assistants.analysis.sql.query.understanding import QueryUnderstanding
from core.assistants.hooks.callback import CallbackManager
from core.models.invoker import ModelInvoker
from core.models.provider import ModelProvider
from core.models.model import ModelInstance
from core.types.sql_schema import ColumnSchema
from core.types.ts_model import TSModel


class QueryPlan(TSModel):
    query: str = Field(description="The generated SQL query")
    explanation: str = Field(description="Explanation of the query structure")
    fixed_approach: Optional[str] = Field(description="In case if the query was fixed by the model, "
                                                      "what was the approach")


class QueryPlanningEngine(TSModel):
    model: ModelInstance

    def generate_query(self, understanding: QueryUnderstanding,
                       table_schemas: Dict[str, List[ColumnSchema]],
                       previous_error_summary: Optional[str] = None) -> QueryPlan:
        formatted_table_schema = self._format_schema_info(table_schemas)
        prompt = f"""
Based on the following query understanding and table schemas, generate an SQL query:

Objective: {understanding.objective}
Reasoning: {understanding.reasoning}

Table Schemas:
{formatted_table_schema}

Generate an SQL query that achieves the objective. Pay special attention to:
1. Correct column names and table references
2. Proper JOIN clauses if needed
3. Correct date/time formatting and comparisons
4. Appropriate GROUP BY, ORDER BY, and LIMIT clauses
5. Wrap each column name with single quotes to ensure that even if it contains whitespaces, it is treated as a single entity

Your response should be in the following JSON format:
`{{
    "query": "Your SQL query here.",
    "explanation": "Detailed explanation of the query structure and why it meets the objective"
    "fixed_approach": "Detailed explanation on what has been changed from the last attempt to fix the query"
}}`


{f"Previous Query Execution Error Summary: {previous_error_summary}\n" if previous_error_summary else None}

        """

        llm = ModelProvider().get_model_instance(self.model.name, api_key=self.model.api_key)
        with CallbackManager.get_callback(self.model.provider, self.model.name) as cb:
            response = ModelInvoker(llm=llm).process(prompt=prompt, output_model=QueryPlan)
            if hasattr(cb, 'update'):
                cb.update(response)
            return response

    def _format_schema_info(self, table_schemas: Dict[str, List[ColumnSchema]]) -> str:
        schema_info = ""
        for table, columns in table_schemas.items():
            schema_info += f"Table: {table}\n"
            for column in columns:
                schema_info += f"  - {column.name}: {column.type}\n"
            schema_info += "\n"
        return schema_info
