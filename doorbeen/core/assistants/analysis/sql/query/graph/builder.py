from typing import Any

from langgraph.constants import START, END
from langgraph.graph import StateGraph

from doorbeen.core.assistants.analysis.sql.nodes.conditionals.determine import InitAssistant, DetermineInputObjectives
from doorbeen.core.assistants.analysis.sql.nodes.conditionals.enrich import EnrichInputNode
from doorbeen.core.assistants.analysis.sql.nodes.conditionals.qn_qa import InputGradingNode
from doorbeen.core.assistants.analysis.sql.nodes.entry import SQLAnalysisEntryNode
from doorbeen.core.assistants.analysis.sql.nodes.execute import ExecuteSQLQueryNode, AnalyseExecutionFailure
from doorbeen.core.assistants.analysis.sql.nodes.finalize import FinalizeAnswerNode
from doorbeen.core.assistants.analysis.sql.nodes.generate import GenerateSQLQueryNode
from doorbeen.core.assistants.analysis.sql.nodes.input_followup import InputFollowupNode
from doorbeen.core.assistants.analysis.sql.nodes.interpretation import InterpretInputNode
from doorbeen.core.assistants.analysis.sql.nodes.observe import ObserveSQLResultsNode
from doorbeen.core.assistants.analysis.sql.nodes.visualize import QueryVisualizationNode
from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.followups import FollowupCertaintyLevel
from doorbeen.core.types.ts_model import TSModel


class SQLAgentGraphBuilder(TSModel):
    handler: ModelHandler
    question: str

    def is_follow_up(self, state: SQLAssistantState):
        if state.is_followup:
            return "followup"
        else:
            return "new"
        
    def followup_answers_fully(self, state: SQLAssistantState):
        if state.followups and len(state.followups) > 0:
            fully_answered = state.followups[-1].certainty_level == FollowupCertaintyLevel.FULL
            if fully_answered:
                return "answer_directly"
            else:
                return "process_further"
        else:
            return "process_further"

    def should_enrich(self, state: SQLAssistantState):
        if state.should_enrich:
            return "enrich"
        else:
            return "no_enrich"

    def query_execution_successful(self, state: SQLAssistantState):
        if state.last_execution_failed:
            return "analyse_failure"
        else:
            return "process_results"

    def all_objectives_fulfilled(self, state: SQLAssistantState):
        if state.query_observation_report.all_objectives_met:
            return "all_objectives_met"
        else:
            return "regen_query"

    def build(self, checkpointer: Any):
        graph_builder = StateGraph(SQLAssistantState)
        # Create nodes
        entry_node = SQLAnalysisEntryNode(handler=self.handler)
        init_assistant = InitAssistant(handler=self.handler, qn=self.question)
        follow_up_node = InputFollowupNode(handler=self.handler)
        qa_grade_node = InputGradingNode(handler=self.handler)
        enrich_input_node = EnrichInputNode(handler=self.handler)
        determine_input_objectives = DetermineInputObjectives(handler=self.handler)
        interpret_input_node = InterpretInputNode(handler=self.handler)
        generate_sql_query_node = GenerateSQLQueryNode(handler=self.handler)
        execute_sql_query_node = ExecuteSQLQueryNode(handler=self.handler)
        process_results_node = ObserveSQLResultsNode(handler=self.handler)
        generate_visualizations_node = QueryVisualizationNode(handler=self.handler)
        handle_execution_failure_node = AnalyseExecutionFailure(handler=self.handler)
        final_answer_node = FinalizeAnswerNode(handler=self.handler)

        # Add nodes and edges
        graph_builder.add_node("init_assistant", init_assistant)
        graph_builder.add_edge(START, "init_assistant")
        graph_builder.add_node("input_followup_node", follow_up_node)

        # Add conditional edges
        graph_builder.add_conditional_edges(
            "init_assistant",
            self.is_follow_up,
            {
                "new": "qa_grade_node",
                "followup": "input_followup_node",
            },
        )
        
        graph_builder.add_conditional_edges(
            "input_followup_node",
            self.followup_answers_fully,
            {
                "answer_directly": END,
                "process_further": "qa_grade_node",
            },
        )

        graph_builder.add_node("qa_grade_node", qa_grade_node)
        graph_builder.add_node("enrich_input_node", enrich_input_node)
        graph_builder.add_node("interpret_input_node", interpret_input_node)
        graph_builder.add_conditional_edges(
            "qa_grade_node",
            self.should_enrich,
            {
                "enrich": "enrich_input_node",
                "no_enrich": "interpret_input_node",
            },
        )
        graph_builder.add_edge("enrich_input_node", "interpret_input_node")
        graph_builder.add_node("generate_sql_query_node", generate_sql_query_node)
        graph_builder.add_edge("interpret_input_node", "generate_sql_query_node")
        graph_builder.add_node("execute_sql_query_node", execute_sql_query_node)
        graph_builder.add_edge("generate_sql_query_node", "execute_sql_query_node")
        graph_builder.add_node("process_results_node", process_results_node)
        graph_builder.add_node("handle_execution_failure_node", handle_execution_failure_node)

        graph_builder.add_conditional_edges(
            "execute_sql_query_node",
            self.query_execution_successful,
            {
                "analyse_failure": "handle_execution_failure_node",
                "process_results": "process_results_node",
            },
        )

        graph_builder.add_edge("handle_execution_failure_node", "execute_sql_query_node")
        graph_builder.add_node("final_answer_node", final_answer_node)
        graph_builder.add_conditional_edges(
            "process_results_node",
            self.all_objectives_fulfilled,
            {
                "regen_query": "generate_sql_query_node",
                "all_objectives_met": "final_answer_node",
            },
        )
        graph_builder.add_edge("final_answer_node", END)
        return graph_builder.compile(checkpointer=checkpointer)
