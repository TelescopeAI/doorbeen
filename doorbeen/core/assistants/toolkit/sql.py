from typing import Union

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_core.tools import BaseTool

from doorbeen.core.connections.clients.NoSQL.mongo import MongoDBClient
from doorbeen.core.connections.clients.SQL.bigquery import BigQueryClient
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.ts_model import TSModel


class TSSQLToolkit(TSModel):
    client: Union[CommonSQLClient, BigQueryClient, MongoDBClient]
    handler: ModelHandler

    def get_sql_toolkit(self) -> SQLDatabaseToolkit:
        db, tools = self.get_lc_tools_from_uri()
        toolkit = SQLDatabaseToolkit(db=db, llm=self.handler.model)
        return toolkit

    def get_tools(self):
        db, tools = self.get_lc_tools_from_uri()
        toolkit = SQLDatabaseToolkit(db=db, llm=self.handler.model)
        collection = [self.get_list_table_tool(), self.get_schema_tool(), self.execute_query()]
        return toolkit.get_tools()

    def get_lc_tools_from_uri(self) -> tuple[SQLDatabase, list[BaseTool]]:
        db_uri = self.client.get_uri()
        db = SQLDatabase.from_uri(db_uri)
        toolkit = SQLDatabaseToolkit(db=db, llm=self.handler.model)
        tools = toolkit.get_tools()
        return db, tools

    def get_list_table_tool(self) -> BaseTool:
        db, tools = self.get_lc_tools_from_uri()
        tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")
        return tool

    def get_schema_tool(self) -> BaseTool:
        db, tools = self.get_lc_tools_from_uri()
        tool = next(tool for tool in tools if tool.name == "sql_db_schema")
        return tool

    def execute_query(self) -> BaseTool:
        """
            Execute a SQL query against the database and get back the result.
            If the query is not correct, an error message will be returned.
            If an error is returned, rewrite the query, check the query, and try again.
            """
        db, tools = self.get_lc_tools_from_uri()
        tool = next(tool for tool in tools if tool.name == "sql_db_query")
        return tool
