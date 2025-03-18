import logging
from typing import List, Dict, Any, Union, Optional, Tuple

from pydantic import Field

from core.assistants.hooks.callback import CallbackManager
from core.models.provider import ModelProvider
from core.connections.clients.NoSQL.mongo import MongoDBClient
from core.connections.clients.SQL.bigquery import BigQueryClient
from core.connections.clients.SQL.common import CommonSQLClient
from core.models.model import ModelInstance
from core.types.ts_model import TSModel


class TableSchema(TSModel):
    columns: Dict[str, str] = Field(description="Dictionary of column names and their data types")
    examples: List


class TableAnalyzer(TSModel):
    client: Union[CommonSQLClient, BigQueryClient, MongoDBClient] = Field(description="Database client", default=None)
    model: ModelInstance = Field(description="The language model instance")

    def get_available_tables(self, schema: Optional[str] = None) -> List[str]:
        return self.client.get_table_names(schema_name=schema)

    def select_relevant_tables(self, available_tables: List[str], user_question: str) -> Tuple[List[str], Dict[str, Any]]:
        prompt = f"""Given the following list of available tables and a user question, 
        select the most relevant tables for answering the question.

        Available tables: {', '.join(available_tables)}

        User question: {user_question}

        Return only the names of the relevant tables, separated by commas."""

        llm = ModelProvider().get_model_instance(model_name=self.model.name, api_key=self.model.api_key, plaintext=True)

        with CallbackManager.get_callback(self.model.provider, self.model.name) as cb:
            response = llm.invoke(prompt)
            selected_tables = [table.strip() for table in response.content.split(',')]

            if hasattr(cb, 'update'):
                cb.update(response)

        usage_stats = CallbackManager.get_usage_from_callback(cb, self.model.provider, self.model.name)

        return selected_tables, usage_stats

    def get_table_schema(self, table_name: str, schema: str) -> TableSchema:
        # Implement this method based on your client's capabilities
        # It should return a TableSchema object
        columns = {}  # Populate this dictionary based on your client's method
        column_schema = self.client.get_column_info(table_name, schema_name=schema)
        return column_schema

    def get_table_examples(self, table_name: str, schema: Optional[str]) -> List:
        # Implement this method based on your client's capabilities
        # It should return a list of example records from the table
        sql = f"SELECT * FROM {table_name} LIMIT 3"
        logging.log(f"Fetching example records from table {table_name}")
        results = self.client.query(sql, schema_name=schema)
        return results
