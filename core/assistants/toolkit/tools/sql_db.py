# # flake8: noqa
# """Tools for interacting with a SQL database."""
#
# from typing import Any, Dict, Optional, Sequence, Type, Union
#
# from langchain_community.tools.sql_database.prompt import QUERY_CHECKER
# from langchain_community.utilities.sql_database import SQLDatabase
# from langchain_core.callbacks import (
#     AsyncCallbackManagerForToolRun,
#     CallbackManagerForToolRun,
# )
# from langchain_core.language_models import BaseLanguageModel
# from langchain_core.prompts import PromptTemplate
# from langchain_core.tools import BaseTool
# from pydantic import model_validator
# from pydantic import Field
# from sqlalchemy.engine import Result
#
# from core.types.ts_model import TSModel
#
#
# class BaseSQLDatabaseTool(TSModel):
#     """Base tool for interacting with a SQL database."""
#
#     db: SQLDatabase = Field(exclude=True)
#
#     class Config(BaseTool.Config):
#         arbitrary_types_allowed = True
#
#
# class _QuerySQLDataBaseToolInput(TSModel):
#     query: str = Field(..., description="A detailed and correct SQL query.")
#
#
# class QuerySQLDataBaseTool(BaseSQLDatabaseTool, BaseTool):
#     """Tool for querying a SQL database."""
#
#     name: str = "sql_db_query"
#     description: str = """
#     Execute a SQL query against the database and get back the result..
#     If the query is not correct, an error message will be returned.
#     If an error is returned, rewrite the query, check the query, and try again.
#     """
#     args_schema: Type[TSModel] = _QuerySQLDataBaseToolInput
#
#     def _run(
#             self,
#             query: str,
#             run_manager: Optional[CallbackManagerForToolRun] = None,
#     ) -> Union[str, Sequence[Dict[str, Any]], Result]:
#         """Execute the query, return the results or an error message."""
#         return self.db.run_no_throw(query)
#
#
# QuerySQLDataBaseTool.model_rebuild()
#
#
# class _InfoSQLDatabaseToolInput(TSModel):
#     table_names: str = Field(
#         ...,
#         description=(
#             "A comma-separated list of the table names for which to return the schema. "
#             "Example input: 'table1, table2, table3'"
#         ),
#     )
#
#
# class InfoSQLDatabaseTool(BaseSQLDatabaseTool, BaseTool):
#     """Tool for getting metadata about a SQL database."""
#
#     name: str = "sql_db_schema"
#     description: str = "Get the schema and sample rows for the specified SQL tables."
#     args_schema: Type[TSModel] = _InfoSQLDatabaseToolInput
#
#     def _run(
#             self,
#             table_names: str,
#             run_manager: Optional[CallbackManagerForToolRun] = None,
#     ) -> str:
#         """Get the schema for tables in a comma-separated list."""
#         return self.db.get_table_info_no_throw(
#             [t.strip() for t in table_names.split(",")]
#         )
#
#
# InfoSQLDatabaseTool.model_rebuild()
#
#
# class _ListSQLDataBaseToolInput(TSModel):
#     tool_input: str = Field("", description="An empty string")
#
#
# class ListSQLDatabaseTool(BaseSQLDatabaseTool, BaseTool):
#     """Tool for getting tables names."""
#
#     name: str = "sql_db_list_tables"
#     description: str = "Input is an empty string, output is a comma-separated list of tables in the database."
#     args_schema: Type[TSModel] = _ListSQLDataBaseToolInput
#
#     def _run(
#             self,
#             tool_input: str = "",
#             run_manager: Optional[CallbackManagerForToolRun] = None,
#     ) -> str:
#         """Get a comma-separated list of table names."""
#         return ", ".join(self.db.get_usable_table_names())
#
#
# ListSQLDatabaseTool.model_rebuild()
#
#
# class _QuerySQLCheckerToolInput(TSModel):
#     query: str = Field(..., description="A detailed and SQL query to be checked.")
#
#
# class QuerySQLCheckerTool(BaseSQLDatabaseTool, BaseTool):
#     """Use an LLM to check if a query is correct.
#     Adapted from https://www.patterns.app/blog/2023/01/18/crunchbot-sql-analyst-gpt/"""
#
#     template: str = QUERY_CHECKER
#     llm: BaseLanguageModel
#     llm_chain: Any = Field(init=False)
#     name: str = "sql_db_query_checker"
#     description: str = """
#     Use this tool to double check if your query is correct before executing it.
#     Always use this tool before executing a query with sql_db_query!
#     """
#     args_schema: Type[TSModel] = _QuerySQLCheckerToolInput
#
#     @model_validator(mode='before')
#     @classmethod
#     def initialize_llm_chain(cls, values: Dict[str, Any]) -> Dict[str, Any]:
#         if "llm_chain" not in values:
#             from langchain.chains.llm import LLMChain
#
#             values["llm_chain"] = LLMChain(
#                 llm=values.get("llm"),  # type: ignore[arg-type]
#                 prompt=PromptTemplate(
#                     template=QUERY_CHECKER, input_variables=["dialect", "query"]
#                 ),
#             )
#
#         if values["llm_chain"].prompt.input_variables != ["dialect", "query"]:
#             raise ValueError(
#                 "LLM chain for QueryCheckerTool must have input variables ['query', 'dialect']"
#             )
#
#         return values
#
#     def _run(
#             self,
#             query: str,
#             run_manager: Optional[CallbackManagerForToolRun] = None,
#     ) -> str:
#         """Use the LLM to check the query."""
#         return self.llm_chain.predict(
#             query=query,
#             dialect=self.db.dialect,
#             callbacks=run_manager.get_child() if run_manager else None,
#         )
#
#     async def _arun(
#             self,
#             query: str,
#             run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
#     ) -> str:
#         return await self.llm_chain.apredict(
#             query=query,
#             dialect=self.db.dialect,
#             callbacks=run_manager.get_child() if run_manager else None,
#         )
#
#
# QuerySQLDataBaseTool.model_rebuild()
