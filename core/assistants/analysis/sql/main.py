import json
from typing import Dict, Any, List, Optional

import pandas as pd
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, END
from pydantic import Field

from core.assistants.analysis.sql.state import SQLAssistantState
from core.assistants.analysis.sql.workflow import SQLAssistantWorkflow, MaxRetriesExceededError
from core.assistants.hooks.callback import CallbackManager
from core.assistants.prompts.sql import db_assistant_summarizer
from core.assistants.usage.tracker import ModelUsageTracker
from core.models.model import ModelInstance
from core.models.provider import ModelSelectionMode
from core.types.sql_schema import ColumnSchema
from core.types.ts_model import TSModel


class AssistantResponse(TSModel):
    query: str = Field(description="The generated SQL query")
    result: Dict[str, Any] = Field(description="The query result")
    selected_tables: List[str] = Field(description="List of selected tables")
    table_schemas: Dict[str, List[ColumnSchema]] = Field(description="Schemas of the selected tables")
    usage_stats: ModelUsageTracker = Field(description="Usage statistics for the operation")
    error_count: int = Field(description="Number of errors encountered")
    errors: List[str] = Field(description="List of errors encountered")


class SQLAssistant(TSModel):
    client: Any = Field(description="Database client")
    db_type: str = Field(description="Type of the database")
    model: ModelInstance = Field(description="Default model instance")
    workflow: Optional[SQLAssistantWorkflow] = Field(default=None, description="SQL Assistant Workflow")
    state: SQLAssistantState = Field(default_factory=SQLAssistantState)
    usage_tracker: ModelUsageTracker = Field(default_factory=ModelUsageTracker)

    class Config:
        arbitrary_types_allowed = True

    # @root_validator
    # def initialize_workflow(cls, values) -> 'SQLAssistant':
    #     if self.workflow is None:
    #         table_analyzer = TableAnalyzer(client=self.client, model=self.model)
    #
    #         understanding_engine = QueryUnderstandingEngine(model=self.model)
    #         planning_engine = QueryPlanningEngine(model=self.model)
    #         validation_engine = QueryValidationEngine(model=self.model)
    #         query_executor = QueryExecutor(client=self.client)
    #
    #         query_execution_manager = QueryExecutionManager(
    #             model=self.model,
    #             understanding_engine=understanding_engine,
    #             planning_engine=planning_engine,
    #             validation_engine=validation_engine,
    #             query_executor=query_executor,
    #             client=self.client
    #         )
    #
    #         self.workflow = SQLAssistantWorkflow(
    #             client=self.client,
    #             table_analyzer=table_analyzer,
    #             query_execution_manager=query_execution_manager
    #         )
    #     return self

    def ask_assistant(
            self,
            question: str,
            schema: Optional[str] = None
    ) -> AssistantResponse:
        self.state.clear_for_new_question()
        self.state.input = question
        self.state.add_to_conversation("user", question)

        try:
            result = self.workflow.run_workflow(self.state, schema)
        except MaxRetriesExceededError as e:
            # Handle the case where max retries were exceeded
            return AssistantResponse(
                query=self.state.input,
                result={},
                selected_tables=[],
                table_schemas={},
                usage_stats=self.usage_tracker,
                error_count=self.workflow.max_retries,
                errors=[str(e)],
                execution_result=None
            )
        self.state.set_last_query(result.query)
        self.state.add_query_result(result.result)
        self.state.set_final_answer(result.result)

        self.state.add_to_conversation("assistant", str(result.result))

        # Update usage stats
        for operation, stats in result.usage_stats.items():
            self.usage_tracker.add_usage(
                model_name=self.model.name,
                input=question,
                output=str(result.result),
                stats=stats
            )

        return AssistantResponse(
            query=result.query,
            result=result.result,
            selected_tables=result.selected_tables,
            table_schemas=result.table_schemas,
            usage_stats=self.usage_tracker,
            error_count=result.error_count,
            errors=result.errors,
            execution_result=result.execution_result
        )

    def execute_sql_query(self, query: str) -> pd.DataFrame:
        """Execute a SQL query and return the results as a pandas DataFrame."""
        print("Executing SQL query:", query)
        result = self.client.query(query)
        return pd.DataFrame(result)

    def get_llm(self, task: str, model: ModelInstance):
        self.model_provider.config.selection_mode[task] = ModelSelectionMode.STATIC
        self.model_provider.set_static_model(task, model.name)
        return self.model_provider.get_model_instance(model_name=model.name, api_key=model.api_key)

    def create_sql_assistant_graph(self):
        sql_tool = StructuredTool.from_function(
            name="SQL_Query_Executor",
            func=self.execute_sql_query,
            description="Executes a SQL query and returns the result as a pandas DataFrame."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             f"You are a SQL expert for {self.db_type} databases. Your task is to analyze data by writing and executing SQL queries, then interpreting the results. You can run multiple queries if needed to gather all necessary information. Use the context of previous query results when formulating new queries."),
            ("human", "Context from previous queries:\n{context}\n\nQuestion: {input}"),
            ("human", "Current conversation:\n{agent_scratchpad}"),
        ])

        def assistant_node(state: SQLAssistantState) -> Dict[str, Any]:
            llm = self.get_llm("sql", state.model)
            agent = create_openai_functions_agent(llm, [sql_tool], prompt)
            agent_executor = AgentExecutor(agent=agent, tools=[sql_tool])

            with CallbackManager.get_callback(state.model.provider, state.model.name) as cb:
                result = agent_executor.invoke({
                    "input": state.input,
                    "context": state.context
                })

                if hasattr(cb, 'update'):
                    cb.update(result)

                state.usage_tracker.add_usage(
                    model_name=state.model.name,
                    input=state.input,
                    output=str(result),
                    stats=CallbackManager.get_usage_from_callback(cb, state.model.provider, state.model.name)
                )

            state.dag_info["assistant"] = {"type": "process", "next": "sql_execution"}
            state.model_info["assistant"] = self.model_provider.get_model_info(llm.model_name).model_dump()

            # Determine the next step based on the output
            if "query" in result["output"]:
                return {"messages": result["messages"], "model_info": state.model_info, "next": "sql_execution"}
            else:
                return {"messages": result["messages"], "model_info": state.model_info, "next": "analysis"}

        def sql_node(state: SQLAssistantState) -> Dict[str, Any]:
            last_message = state.messages[-1].content
            if isinstance(last_message, str) and "query" in last_message:
                query = json.loads(last_message)["query"]
                result_df = self.execute_sql_query(query)
                result_dict = result_df.to_dict(orient="records")
                state.query_results.append(result_dict)

                new_result_str = json.dumps(result_dict, indent=2)
                summarized_new_result = self.chunk_and_summarize(new_result_str, state)
                state.context += f"\nResults of latest query:\n{summarized_new_result}\n"

                state.dag_info["sql_execution"] = {"type": "data", "next": "assistant"}
                return {"query_results": state.query_results, "context": state.context, "next": "assistant"}
            return {"next": "analysis"}

        def analysis_node(state: SQLAssistantState) -> Dict[str, Any]:
            all_results_str = json.dumps(state.query_results, indent=2)
            summarized_results = self.chunk_and_summarize(all_results_str, state)

            analysis_prompt = db_assistant_summarizer(summarized_results=summarized_results)

            llm = self.get_llm("analysis", state.model)

            with CallbackManager.get_callback(state.model.provider, state.model.name) as cb:
                analysis_response = llm.invoke(analysis_prompt)

                if hasattr(cb, 'update'):
                    cb.update(analysis_response)

                state.usage_tracker.add_usage(
                    model_name=state.model.name,
                    input=analysis_prompt,
                    output=analysis_response.content,
                    stats=CallbackManager.get_usage_from_callback(cb, state.model.provider, state.model.name)
                )

            analysis_result = json.loads(analysis_response.content)

            final_answer = {
                "text_content": analysis_result.get("text_content", ""),
                "table_data": self.prepare_table_data(
                    state.query_results[-1]) if "table_description" in analysis_result else None,
                "chart_data": self.prepare_chart_data(state.query_results[-1], analysis_result.get(
                    "chart_description")) if "chart_description" in analysis_result else None
            }

            state.dag_info["analysis"] = {"type": "process", "next": "end"}
            state.model_info["analysis"] = self.model_provider.get_model_info(llm.model_name).model_dump()
            return {"final_answer": final_answer, "next": END, "dag_info": state.dag_info,
                    "model_info": state.model_info}

        workflow = StateGraph(SQLAssistantState)

        workflow.add_node("assistant", assistant_node)
        workflow.add_node("sql_execution", sql_node)
        workflow.add_node("analysis", analysis_node)

        workflow.set_entry_point("assistant")

        workflow.add_conditional_edges(
            "assistant",
            lambda x: x["next"]
        )
        workflow.add_conditional_edges(
            "sql_execution",
            lambda x: x["next"]
        )
        workflow.add_edge("analysis", END)

        return workflow.compile()

    def chunk_and_summarize(self, data: str, state: SQLAssistantState, max_tokens: int = 4000) -> str:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_tokens,
            chunk_overlap=200,
            length_function=len,
        )
        chunks = text_splitter.split_text(data)

        if len(chunks) == 1:
            return chunks[0]

        summaries = [self.summarize_data(chunk, state) for chunk in chunks]
        return "\n".join(summaries)

    def summarize_data(self, data: str, state: SQLAssistantState) -> str:
        llm = self.get_llm("analysis", state.model)
        summarize_prompt = ChatPromptTemplate.from_messages([
            ("system", "Summarize the following data concisely, focusing on key information:"),
            ("human", "{data}")
        ])

        with CallbackManager.get_callback(state.model.provider, state.model.name) as cb:
            summary = llm(summarize_prompt.format_messages(data=data))

            if hasattr(cb, 'update'):
                cb.update(summary)

            state.usage_tracker.add_usage(
                model_name=state.model.name,
                input=data,
                output=summary.content,
                stats=CallbackManager.get_usage_from_callback(cb, state.model.provider, state.model.name)
            )

        return summary.content

    def prepare_table_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        df = pd.DataFrame(data)
        return {
            "columns": df.columns.tolist(),
            "data": df.to_dict(orient='records')
        }

    def prepare_chart_data(self, data: List[Dict[str, Any]], chart_description: str) -> Dict[str, Any]:
        df = pd.DataFrame(data)
        chart_type = "bar"  # Default to bar chart
        if "line" in chart_description.lower():
            chart_type = "line"
        elif "scatter" in chart_description.lower():
            chart_type = "scatter"

        return {
            "type": chart_type,
            "data": {
                "labels": df.index.tolist(),
                "datasets": [{
                    "label": column,
                    "data": df[column].tolist()
                } for column in df.columns]
            }
        }