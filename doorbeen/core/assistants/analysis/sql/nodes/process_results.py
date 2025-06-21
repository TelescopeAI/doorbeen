import json

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.assistants.utils.sql import convert_sqlalchemy_rows_to_dict
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.observe import QueryAnalysisReport
from doorbeen.core.types.ts_model import TSModel


class ProcessResultsNode(TSModel):
    handler: ModelHandler

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        assert state.interpretation is not None, "Interpretation should be present in the state"

        # Check if we have actual results to process
        execution_results = state.execution_results[-1] if state.execution_results else None
        has_data = execution_results and execution_results.result and len(execution_results.result) > 0
        
        # Dataset-agnostic result processing
        if has_data:
            # Process actual results
            system_prompt = self._get_data_processing_prompt()
            input_prompt = f"""
Objective: {state.interpretation.objective}

Query Executed: {execution_results.query}

Results Found: {len(execution_results.result)} records

Sample Results (first 5 records):
{json.dumps(convert_sqlalchemy_rows_to_dict(execution_results.result[:5]), indent=2)}

Based on these results, analyze what insights can be drawn and whether the user's objective has been met.
"""
        else:
            # Handle no data scenario with intelligent alternatives
            system_prompt = self._get_no_data_processing_prompt()
            input_prompt = f"""
Objective: {state.interpretation.objective}

Query Executed: {execution_results.query if execution_results else "No query executed"}

Data Exploration Findings: {state.exploration_findings or "No exploration performed"}

The query returned no results. Analyze this situation and provide:
1. Why no data was found (based on exploration findings)
2. Alternative approaches or related analyses that could be helpful
3. Suggestions for what data might need to be collected
4. Whether the user's question can be answered with available data in a different way

Consider this a complete analysis - don't just say "no data found".
"""

        summarized_content = state.summary
        summarized_context = AIMessage(content=f"Here is a summary of all of the previous "
                                               f"conversations\n\n {summarized_content}\n\n")
        request_messages = [
            summarized_context,
            SystemMessage(content=system_prompt),
            AIMessage(content=input_prompt)
        ]

        json_llm = self.handler.model.bind(response_format={"type": "json_object"})
        response = json_llm.invoke(request_messages)
        response_data = json.loads(response.content)
        
        # Enhanced observation report that handles no-data scenarios
        query_observation_report = QueryAnalysisReport(**response_data)
        result_message = AIMessage(content=query_observation_report.model_dump_json())

        summary = state.summary
        summary += "\n\n[CURRENT OPERATION: Processing Query Results]\n"
        
        if has_data:
            summary += f"Successfully found {len(execution_results.result)} records. Analyzing results for insights.\n"
        else:
            summary += "No data found matching the query criteria. Providing alternative analysis suggestions.\n"
            
        summary += f"Analysis insights: {', '.join(query_observation_report.insights) if query_observation_report.insights else 'No specific insights generated'}\n"
        if query_observation_report.next_step:
            summary += f"Next steps: {query_observation_report.next_step}\n"
        
        # Enhanced logic for determining if objectives are met
        objectives_met = self._determine_objectives_status(query_observation_report, has_data, state)

        return {
            "messages": [result_message],
            "query_observation_report": query_observation_report,
            "summary": summary,
            "objectives_met": objectives_met,
            "has_actionable_results": has_data,
            "alternative_suggestions_provided": not has_data and bool(query_observation_report.insights)
        }

    def _get_data_processing_prompt(self) -> str:
        """Prompt for processing when data is found"""
        return """
You are analyzing query results to determine if the user's objective has been met and what insights can be drawn.

Instructions:
1. Analyze the data returned and extract meaningful insights
2. Determine if the user's objective has been fully, partially, or not met
3. Suggest any additional analysis that might be valuable
4. Provide a clear summary of findings

JSON Format:
{
    "query": {
        "query_effective": true/false,
        "met_reasons": ["Reason 1 why objective was met", "Reason 2"],
        "unmet_reasons": ["Reason 1 why objective was not met", "Reason 2"]
    },
    "all_objectives_met": true/false,
    "some_objectives_met": true/false,
    "insights": ["Insight 1", "Insight 2"],
    "unmet_objectives": ["Objective 1", "Objective 2"],
    "next_step": "What additional queries or analysis might be helpful"
}
"""

    def _get_no_data_processing_prompt(self) -> str:
        """Prompt for processing when no data is found"""
        return """
You are analyzing a scenario where a query returned no results. Your goal is to provide intelligent analysis and alternatives.

Instructions:
1. Analyze WHY no data was found based on the exploration findings
2. Suggest alternative approaches or related analyses
3. Determine if the user's question can be answered differently with available data
4. Provide constructive suggestions rather than just "no data found"

JSON Format:
{
    "query": {
        "query_effective": false,
        "met_reasons": [],
        "unmet_reasons": ["Query returned no results", "Available data may not contain the requested information"]
    },
    "all_objectives_met": false,
    "some_objectives_met": false,
    "insights": ["Analysis of why no data was found", "What this means for the user's question"],
    "unmet_objectives": ["Objective that couldn't be met"],
    "next_step": "Specific suggestions for alternative analyses or data collection"
}
"""

    def _determine_objectives_status(self, report: QueryAnalysisReport, has_data: bool, state: SQLAssistantState) -> str:
        """
        Intelligently determine if we should continue trying or consider objectives met.
        This prevents infinite loops while providing useful responses.
        Enhanced to be more generous about considering objectives "met" when value is provided.
        """
        # If we have data and objectives are explicitly met, we're done
        if has_data and getattr(report, 'all_objectives_met', False):
            return "all_objectives_met"
        
        # If we have meaningful insights (even without perfect objective completion), consider value provided
        insights = getattr(report, 'insights', [])
        meaningful_insights = [
            insight for insight in insights 
            if isinstance(insight, str) and len(insight) > 30
        ] if insights else []
        
        # If we have data and meaningful insights, that's often sufficient value
        if has_data and len(meaningful_insights) >= 2:
            return "all_objectives_met"
        
        # If we have some objectives met and meaningful content, that's often enough
        if getattr(report, 'some_objectives_met', False) and len(meaningful_insights) >= 1:
            return "some_objectives_met"
        
        # If no data found but we have good exploration and comprehensive analysis, consider it complete
        if not has_data and state.exploration_findings and len(state.exploration_findings) > 100:
            # We've done thorough exploration and analysis - this is a complete answer
            return "all_objectives_met"
        
        # If we've tried multiple queries and still no data, but have good analysis, stop trying
        if len(state.execution_results) >= 2 and not has_data and len(meaningful_insights) >= 1:
            return "all_objectives_met"
        
        # Default: might need more analysis
        return "some_objectives_met" 