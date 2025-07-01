import json
import logging
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
from doorbeen.core.assistants.analysis.sql.nodes.process_results import ProcessResultsNode
from doorbeen.core.assistants.analysis.sql.nodes.tools.kit import DataExplorationNode
from doorbeen.core.assistants.analysis.sql.nodes.visualize import QueryVisualizationNode
from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.ts_model import TSModel


class LinearGraphBuilder(TSModel):
    """
    Builder for traditional linear node-based SQL analysis graph.
    
    This graph uses sequential nodes with conditional routing logic for
    processing SQL analysis requests in a traditional pipeline fashion.
    """
    
    handler: ModelHandler
    question: str

    def should_enrich(self, state: SQLAssistantState):
        logging.info("🔍 [LINEAR_BUILDER] Evaluating should_enrich routing decision")
        logging.info(f"🔍 [LINEAR_BUILDER] Question: {state.input}")
        
        # CRITICAL: Check for irrelevant questions first (circuit breaker condition)
        if hasattr(state, 'grade') and state.grade:
            logging.info("🔍 [LINEAR_BUILDER] Grade data found, checking relevance")
            
            # Check relevance score - if relevance score > 6, question is not relevant to dataset
            # Handle both dict and object access patterns
            relevance_score = None
            
            if isinstance(state.grade, dict):
                logging.info("🔍 [LINEAR_BUILDER] Using dictionary access for grade")
                # Dictionary access pattern
                relevance_data = state.grade.get('relevance', {})
                if isinstance(relevance_data, dict):
                    relevance_score = relevance_data.get('score')
            else:
                logging.info("🔍 [LINEAR_BUILDER] Using object access for grade")
                # Object access pattern
                if hasattr(state.grade, 'relevance') and hasattr(state.grade.relevance, 'score'):
                    relevance_score = state.grade.relevance.score
            
            logging.info(f"🔍 [LINEAR_BUILDER] Relevance score: {relevance_score}")
            
            if relevance_score is not None and relevance_score > 6:
                # Mark circuit breaker for irrelevant questions
                logging.warning(f"⚠️ [LINEAR_BUILDER] CIRCUIT BREAKER TRIGGERED - Irrelevant question (score: {relevance_score})")
                state.circuit_breaker_triggered = True
                state.relevance_assessment = f"Question not relevant to dataset (relevance score: {relevance_score})"
                return "circuit_breaker"
        
        logging.info(f"🔍 [LINEAR_BUILDER] Question is relevant, checking enrichment need")
        logging.info(f"🔍 [LINEAR_BUILDER] context.should_enrich: {getattr(state, 'should_enrich', 'not set')}")
        
        # For relevant questions, check if enrichment is needed
        if state.should_enrich:
            logging.info("✅ [LINEAR_BUILDER] ROUTING TO ENRICHMENT")
            return "enrich"
        else:
            logging.info("✅ [LINEAR_BUILDER] ROUTING TO INTERPRETATION (no enrichment needed)")
            return "no_enrich"

    def query_execution_successful(self, state: SQLAssistantState):
        logging.info("🔍 [LINEAR_BUILDER] Evaluating query execution success")
        
        # CRITICAL: Check circuit breaker FIRST - both from context and recent messages
        if getattr(state, 'circuit_breaker_triggered', False):
            logging.warning("⚠️ [LINEAR_BUILDER] Circuit breaker already triggered in context")
            return "circuit_breaker_end"
        
        # Also check the most recent message for circuit breaker information
        if state.messages:
            latest_message = state.messages[-1]
            if hasattr(latest_message, 'content'):
                try:
                    content = json.loads(latest_message.content) if isinstance(latest_message.content, str) else latest_message.content
                    if isinstance(content, dict) and content.get('circuit_breaker_triggered'):
                        logging.warning("⚠️ [LINEAR_BUILDER] Circuit breaker found in latest message")
                        return "circuit_breaker_end"
                except:
                    pass
        
        # Check if we've exceeded retry limits (fallback detection)
        retry_count = getattr(state, 'retry_count', 0)
        max_retries = getattr(state, 'max_retries', 3)
        logging.info(f"🔍 [LINEAR_BUILDER] Retry status: {retry_count}/{max_retries}")
        
        if retry_count >= max_retries:
            logging.warning(f"⚠️ [LINEAR_BUILDER] Retry limit exceeded ({retry_count}/{max_retries})")
            return "circuit_breaker_end"
        
        # Check execution status
        last_execution_failed = getattr(state, 'last_execution_failed', False)
        logging.info(f"🔍 [LINEAR_BUILDER] Last execution failed: {last_execution_failed}")
        
        if last_execution_failed:
            logging.info("🔄 [LINEAR_BUILDER] ROUTING TO FAILURE ANALYSIS")
            return "analyse_failure"
        else:
            logging.info("✅ [LINEAR_BUILDER] ROUTING TO RESULTS PROCESSING")
            return "process_results"

    def all_objectives_fulfilled(self, state: SQLAssistantState):
        """
        Intelligent "good enough" detection that determines when the system has provided
        sufficient value to the user, preventing infinite loops while ensuring useful responses.
        Enhanced with configurable retry strategies for unmet objectives.
        """
        logging.info("🔍 [LINEAR_BUILDER] Evaluating if all objectives are fulfilled")
        
        # CRITICAL: Circuit breaker check first
        if getattr(state, 'circuit_breaker_triggered', False):
            logging.warning("⚠️ [LINEAR_BUILDER] Circuit breaker triggered - ending workflow")
            return "all_objectives_met"
        
        # Count iterations to prevent infinite loops
        query_generation_count = len([msg for msg in state.messages if "generate_sql_query_node" in str(msg)])
        process_results_count = len([msg for msg in state.messages if "process_results_node" in str(msg)])
        
        logging.info(f"🔍 [LINEAR_BUILDER] Iteration counts:")
        logging.info(f"   - Query generations: {query_generation_count}")
        logging.info(f"   - Results processing: {process_results_count}")
        logging.info(f"   - Objective retries: {state.objective_retry_count}/{state.max_objective_retries}")
        
        # Absolute safety valve: Stop after 4 query generations or 4 result processings
        if query_generation_count >= 4 or process_results_count >= 4:
            logging.warning(f"⚠️ [LINEAR_BUILDER] Safety valve triggered - too many iterations")
            return "all_objectives_met"
        
        # Check for explicit "all objectives met" - always honor this
        if (hasattr(state, 'objectives_met') and state.objectives_met == "all_objectives_met") or \
           (hasattr(state, 'query_observation_report') and state.query_observation_report and 
            getattr(state.query_observation_report, 'all_objectives_met', False)):
            logging.info("✅ [LINEAR_BUILDER] Explicit objectives met signal found")
            return "all_objectives_met"
        
        # "Good Enough" Value Detection - check if we've provided sufficient value
        has_meaningful_results = self._has_sufficient_value(state)
        logging.info(f"🔍 [LINEAR_BUILDER] Has meaningful results: {has_meaningful_results}")
        
        if has_meaningful_results:
            # If we have meaningful results and have tried at least once, that's often enough
            if query_generation_count >= 1:
                logging.info("✅ [LINEAR_BUILDER] Sufficient value achieved - ending workflow")
                return "all_objectives_met"
        
        # Check if we should try objective-based retries for unmet objectives
        if (hasattr(state, 'objectives_met') and state.objectives_met in [None, "some_objectives_met"]) or \
           (hasattr(state, 'query_observation_report') and state.query_observation_report and 
            not getattr(state.query_observation_report, 'all_objectives_met', False)):
            
            # Check if we can retry with different strategies
            if state.can_retry_objectives:
                next_strategy = state.get_next_retry_strategy()
                if next_strategy:
                    logging.info(f"🔄 [LINEAR_BUILDER] Attempting objective retry with strategy: {next_strategy}")
                    state.mark_retry_strategy_used(next_strategy)
                    
                    # Store the strategy for the next interpretation/generation cycle
                    state.summary = (state.summary or "") + f"\n\n[RETRY STRATEGY]: {next_strategy}"
                    
                    return "regen_query"
            else:
                logging.info("⚠️ [LINEAR_BUILDER] Objective retry limit reached, ending workflow")
                return "all_objectives_met"
        
        # If we have some objectives met and meaningful insights, stop after 2 attempts
        if (hasattr(state, 'objectives_met') and state.objectives_met == "some_objectives_met") or \
           (hasattr(state, 'query_observation_report') and state.query_observation_report and 
            getattr(state.query_observation_report, 'some_objectives_met', False)):
            
            if query_generation_count >= 2 and has_meaningful_results:
                logging.info("✅ [LINEAR_BUILDER] Some objectives met with meaningful results - ending workflow")
                return "all_objectives_met"
        
        # If we have alternative suggestions for no-data scenarios, that's complete
        if getattr(state, 'alternative_suggestions_provided', False):
            logging.info("✅ [LINEAR_BUILDER] Alternative suggestions provided - ending workflow")
            return "all_objectives_met"
        
        # If we have comprehensive exploration findings but no data, that's complete
        if (state.exploration_findings and 
            len(state.exploration_findings) > 200 and 
            state.execution_results and 
            len(state.execution_results) > 0 and
            (not state.execution_results[-1].result or len(state.execution_results[-1].result) == 0)):
            logging.info("✅ [LINEAR_BUILDER] Comprehensive exploration completed - ending workflow")
            return "all_objectives_met"
        
        # Default: continue trying (but limited by safety valves above)
        logging.info("🔄 [LINEAR_BUILDER] Continuing workflow - regenerating query")
        return "regen_query"
    
    def _has_sufficient_value(self, state: SQLAssistantState) -> bool:
        """
        Determine if the current context provides sufficient value to the user.
        This is the key "good enough" detection logic.
        """
        logging.info("🔍 [LINEAR_BUILDER] Evaluating sufficient value")
        
        # Check if we have a query observation report with insights
        if hasattr(state, 'query_observation_report') and state.query_observation_report:
            report = state.query_observation_report
            
            # Count meaningful insights (non-empty, substantial content)
            insights = getattr(report, 'insights', [])
            meaningful_insights = [
                insight for insight in insights 
                if isinstance(insight, str) and len(insight) > 50
            ] if insights else []
            
            logging.info(f"🔍 [LINEAR_BUILDER] Meaningful insights: {len(meaningful_insights)}")
            
            # If we have 3+ substantial insights, that's valuable
            if len(meaningful_insights) >= 3:
                logging.info("✅ [LINEAR_BUILDER] Sufficient insights found")
                return True
            
            # If we have data results AND some insights, that's valuable
            if (state.execution_results and 
                len(state.execution_results) > 0 and 
                state.execution_results[-1].result and 
                len(state.execution_results[-1].result) > 0 and
                len(meaningful_insights) >= 1):
                logging.info("✅ [LINEAR_BUILDER] Data results with insights found")
                return True
            
            # If we have a detailed next_step, that shows thoughtful analysis
            next_step = getattr(report, 'next_step', '')
            if next_step and len(next_step) > 100:
                logging.info("✅ [LINEAR_BUILDER] Detailed next step found")
                return True
        
        # Check if we have actionable results
        if getattr(state, 'has_actionable_results', False):
            logging.info("✅ [LINEAR_BUILDER] Actionable results found")
            return True
        
        # Check if we have substantial exploration findings
        if (state.exploration_findings and 
            len(state.exploration_findings) > 300):  # Comprehensive exploration
            logging.info("✅ [LINEAR_BUILDER] Substantial exploration findings found")
            return True
        
        logging.info("❌ [LINEAR_BUILDER] Insufficient value - need more work")
        return False

    def build(self, checkpointer: Any):
        """Build the traditional linear node graph"""
        logging.info("📝 [LINEAR_BUILDER] Building linear node graph")
        
        graph_builder = StateGraph(SQLAssistantState)
        
        # Create all linear nodes
        entry_node = SQLAnalysisEntryNode(handler=self.handler)
        init_assistant = InitAssistant(handler=self.handler, qn=self.question)
        follow_up_node = InputFollowupNode(handler=self.handler)
        qa_grade_node = InputGradingNode(handler=self.handler)
        enrich_input_node = EnrichInputNode(handler=self.handler)
        determine_input_objectives = DetermineInputObjectives(handler=self.handler)
        interpret_input_node = InterpretInputNode(handler=self.handler)
        data_exploration_node = DataExplorationNode(handler=self.handler)
        generate_sql_query_node = GenerateSQLQueryNode(handler=self.handler)
        execute_sql_query_node = ExecuteSQLQueryNode(handler=self.handler)
        process_results_node = ProcessResultsNode(handler=self.handler)
        generate_visualizations_node = QueryVisualizationNode(handler=self.handler)
        handle_execution_failure_node = AnalyseExecutionFailure(handler=self.handler)
        final_answer_node = FinalizeAnswerNode(handler=self.handler)

        logging.info("📝 [LINEAR_BUILDER] Adding linear nodes and edges to graph")
        
        # Add nodes and edges
        graph_builder.add_node("init_assistant", init_assistant)
        graph_builder.add_edge(START, "init_assistant")

        # Direct linear flow - no followup branching
        graph_builder.add_edge("init_assistant", "qa_grade_node")

        graph_builder.add_node("qa_grade_node", qa_grade_node)
        graph_builder.add_node("enrich_input_node", enrich_input_node)
        graph_builder.add_node("interpret_input_node", interpret_input_node)
        graph_builder.add_node("data_exploration_node", data_exploration_node)
        graph_builder.add_conditional_edges(
            "qa_grade_node",
            self.should_enrich,
            {
                "enrich": "enrich_input_node",
                "no_enrich": "interpret_input_node",
                "circuit_breaker": "final_answer_node",  # Route irrelevant questions to final answer
            },
        )
        graph_builder.add_edge("enrich_input_node", "interpret_input_node")
        graph_builder.add_edge("interpret_input_node", "data_exploration_node")
        graph_builder.add_node("generate_sql_query_node", generate_sql_query_node)
        graph_builder.add_edge("data_exploration_node", "generate_sql_query_node")
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
                "circuit_breaker_end": "final_answer_node"  # Route through final answer node
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
        
        logging.info("✅ [LINEAR_BUILDER] Linear graph construction completed")
        return graph_builder.compile(checkpointer=checkpointer) 