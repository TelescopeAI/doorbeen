from typing import Literal

from langchain_community.utilities import SQLDatabase
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from pydantic import Field

from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.models.provider import ModelProvider
from doorbeen.core.models.model import ModelInstance
from doorbeen.core.types.ts_model import TSModel

query_check_system = """You are a SQL expert with a strong attention to detail.
Double check the SQLite query for common mistakes, including:
- Using NOT IN with NULL values
- Using UNION when UNION ALL should have been used
- Using BETWEEN for exclusive ranges
- Data type mismatch in predicates
- Properly quoting identifiers
- Using the correct number of arguments for functions
- Casting to the correct data type
- Using the proper columns for joins

If there are any of the above mistakes, rewrite the query. If there are no mistakes, just reproduce the original query.

You will call the appropriate tool to execute the query after running this check."""


# Describe a tool to represent the end state
class SubmitFinalAnswer(TSModel):
    """Submit the final answer to the user based on the query results."""

    final_answer: str = Field(..., description="The final answer to the user")


class SQLDBWorkflow(TSModel):
    workflow: StateGraph = None
    db: SQLDatabase = Field(exclude=True)

    class Config:
        arbitrary_types_allowed = True

    def query_check(self, model: ModelInstance):
        model = ModelProvider().get_model_instance(model.name,
                                                   api_key=model.api_key)
        query_check_prompt = ChatPromptTemplate.from_messages(
            [("system", query_check_system), ("placeholder", "{messages}")]
        )
        # query_check = query_check_prompt | model.bind_tools([QuerySQLDataBaseTool], tool_choice="required")
        query_check = query_check_prompt
        return query_check

    # Add a node for the first tool call
    def first_tool_call(state: SQLAssistantState) -> dict[str, list[AIMessage]]:
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "sql_db_list_tables",
                            "args": {},
                            "id": "tool_abcd123",
                        }
                    ],
                )
            ]
        }

    def model_check_query(self, state: SQLAssistantState) -> dict[str, list[AIMessage]]:
        """
        Use this tool to double-check if your query is correct before executing it.
        """
        return {"messages": [self.query_check.invoke({"messages": [state["messages"][-1]]})]}

    def query_gen_node(self, state: SQLAssistantState, model: ModelInstance):
        llm = ModelProvider().get_model_instance(model.name, api_key=model.api_key)
        # Add a node for a model to generate a query based on the question and schema
        query_gen_system = """You are a SQL expert with a strong attention to detail.

        Given an input question, output a syntactically correct SQLite query to run, then look at the results of the query and return the answer.

        DO NOT call any tool besides SubmitFinalAnswer to submit the final answer.

        When generating the query:

        Output the SQL query that answers the input question without a tool call.

        Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 5 results.
        You can order the results by a relevant column to return the most interesting examples in the database.
        Never query for all the columns from a specific table, only ask for the relevant columns given the question.

        If you get an error while executing a query, rewrite the query and try again.

        If you get an empty result set, you should try to rewrite the query to get a non-empty result set. 
        NEVER make stuff up if you don't have enough information to answer the query... just say you don't have enough information.

        If you have enough information to answer the input question, simply invoke the appropriate tool to submit the final answer to the user.

        DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database."""
        query_gen_prompt = ChatPromptTemplate.from_messages(
            [("system", query_gen_system), ("placeholder", "{messages}")]
        )
        query_gen = query_gen_prompt | llm.bind_tools(
            [SubmitFinalAnswer]
        )
        message = query_gen.invoke(state)

        # Sometimes, the LLM will hallucinate and call the wrong tool. We need to catch this and return an error message.
        tool_messages = []
        if message.tool_calls:
            for tc in message.tool_calls:
                if tc["name"] != "SubmitFinalAnswer":
                    tool_messages.append(
                        ToolMessage(
                            content=f"Error: The wrong tool was called: {tc['name']}. Please fix your mistakes. Remember to only call SubmitFinalAnswer to submit the final answer. Generated queries should be outputted WITHOUT a tool call.",
                            tool_call_id=tc["id"],
                        )
                    )
        else:
            tool_messages = []
        return {"messages": [message] + tool_messages}

    def build(self, model: ModelInstance):
        self.workflow = StateGraph(SQLAssistantState)
        llm = ModelProvider().get_model_instance(model.name, api_key=model.api_key)
        self.workflow.add_node("first_tool_call", self.first_tool_call)

        # Add nodes for the first two tools
        # self.workflow.add_node(
        #     "list_tables_tool", ListSQLDatabaseTool
        # )
        # self.workflow.add_node("get_schema_tool", InfoSQLDatabaseTool)

        # Add a node for a model to choose the relevant tables based on the question and available tables
        # model_get_schema = llm.bind_tools(
        #     [InfoSQLDatabaseTool]
        # )
        model_get_schema = llm.bind_tools()
        self.workflow.add_node(
            "model_get_schema",
            lambda state: {
                "messages": [model_get_schema.invoke(state["messages"])],
            },
        )

        self.workflow.add_node("query_gen", self.query_gen_node(model=model))

        # Add a node for the model to check the query before executing it
        self.workflow.add_node("correct_query", self.model_check_query)

        # Add node for executing the query
        # self.workflow.add_node("execute_query", QuerySQLDataBaseTool)

        # Define a conditional edge to decide whether to continue or end the workflow
        def should_continue(state: SQLAssistantState) -> Literal[END, "correct_query", "query_gen"]:
            messages = state["messages"]
            last_message = messages[-1]
            # If there is a tool call, then we finish
            if getattr(last_message, "tool_calls", None):
                return END
            if last_message.content.startswith("Error:"):
                return "query_gen"
            else:
                return "correct_query"

        # Specify the edges between the nodes
        self.workflow.add_edge(START, "first_tool_call")
        self.workflow.add_edge("first_tool_call", "list_tables_tool")
        self.workflow.add_edge("list_tables_tool", "model_get_schema")
        self.workflow.add_edge("model_get_schema", "get_schema_tool")
        self.workflow.add_edge("get_schema_tool", "query_gen")
        self.workflow.add_conditional_edges(
            "query_gen",
            should_continue,
        )
        self.workflow.add_edge("correct_query", "execute_query")
        self.workflow.add_edge("execute_query", "query_gen")

        # Compile the workflow into a runnable
        app = self.workflow.compile()
        return app
