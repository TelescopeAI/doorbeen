from typing import List, Optional, Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from pydantic import Field

from core.assistants.analysis.grades import InputGradeResult
from core.assistants.analysis.sql.query.understanding import QueryUnderstanding
from core.glossary.meaning import Glossary
from core.types.enrich import EnrichedOutput
from core.types.execute import ExecutionResults
from core.types.followups import FollowupAttempts
from core.types.generate import GeneratedSQLQuery
from core.types.observe import QueryAnalysisReport
from core.types.sql_schema import DatabaseSchema
from core.types.ts_model import TSModel
from core.types.visualize import QueryVisualizationPlan


def add_execution_operator(a: List[ExecutionResults], b: List[ExecutionResults]) -> List[ExecutionResults]:
    return a + b


class SQLAssistantState(TSModel):
    messages: Annotated[list[AnyMessage], add_messages]
    error: Optional[dict] = None
    input: Optional[str] = Field(default=None, description="The current input question")
    task_type: Optional[str] = Field(default=None, description="Is it a new or followup task")
    should_enrich: Optional[bool] = Field(default=False, description="Whether the input needs to be enriched")
    enrich_output: Optional[EnrichedOutput] = Field(default=None, description="The output of the enrichment process")
    enrich_max_attempts: Optional[int] = Field(default=3, description="Maximum number of attempts to enrich the input")
    is_followup: Optional[bool] = False
    followups: Optional[List[FollowupAttempts]] = Field(default_factory=list, description="Follow-up attempts")
    qa_passed: Optional[bool] = Field(default=False, description="Whether the input has passed QA")
    grade: Optional[InputGradeResult] = Field(default=None, description="The grade of the input")
    output: Optional[str] = Field(default=None, description="The output of the assistant")
    glossary: Optional[Glossary] = Field(default=None, description="Glossary of terms")
    interpretation: Optional[QueryUnderstanding] = Field(default=None, description="Interpretation of the input")
    generated_query: Optional[GeneratedSQLQuery] = Field(default=None, description="The generated SQL query")
    execution_results: Optional[Annotated[list[ExecutionResults], add_execution_operator]] = Field(default=None,
                                                                                                   description="The result of executing the query")
    last_execution_failed: Optional[bool] = Field(default=False, description="Whether the last execution failed")
    query_observation_report: Optional[QueryAnalysisReport] = Field(default=None, description="Report on the query results")
    query_viz: Optional[QueryVisualizationPlan] = Field(default=None, description="Visualization of the query")
    selected_tables: Optional[List[str]] = Field(default_factory=list, description="Tables selected for the current "
                                                                                   "query")
    table_schemas: Optional[DatabaseSchema] = Field(default_factory=dict, description="Schemas of the selected tables")
    current_messages: Optional[List[AnyMessage]] = Field(default_factory=list,
                                                         description="Messages for the current execution")
    summary: Optional[str] = Field(default=None, description="Summary of the existing conversations")
    request_count: Optional[int] = Field(default=0, description="Number of requests made to the assistant")
    # last_query: Optional[str] = Field(default=None, description="The last executed SQL query")
    # conversation_history: List[Dict[str, str]] = Field(default_factory=list, description="History of the conversation")

    # def update_context(self, new_context: str):
    #     self.context += f"\n{new_context}"
    #
    # def add_query_result(self, result: Dict[str, Any]):
    #     self.query_results.append(result)
    #
    # def set_final_answer(self, answer: Dict[str, Any]):
    #     self.final_answer = answer
    #
    # def add_selected_table(self, table: str):
    #     if table not in self.selected_tables:
    #         self.selected_tables.append(table)
    #
    # def add_table_schema(self, table: str, schema: TableSchema):
    #     self.table_schemas[table] = schema
    #
    # def set_last_query(self, query: str):
    #     self.last_query = query
    #
    # def add_to_conversation(self, role: str, content: str):
    #     self.conversation_history.append({"role": role, "content": content})
    #
    # def clear_for_new_question(self):
    #     self.input = ""
    #     self.query_results = []
    #     self.final_answer = {}
    #     self.dag_info = {}
    #     self.last_query = None
    # Note: We're not clearing context, selected_tables, table_schemas, or conversation_history
    # as these might be useful for maintaining continuity across inputs
