from typing import Any, List, Dict
from pydantic import ConfigDict, Field

from doorbeen.core.types.ts_model import TSModel
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState
from langgraph.prebuilt import create_react_agent

from doorbeen.core.assistants.analysis.sql.tools.result_processing import (
    analyze_dataset_overview,
    get_top_values_analysis,
    aggregate_data_analysis,
    statistical_analysis,
    trend_analysis,
    correlation_analysis,
    outlier_detection,
    categorical_analysis,
    generate_insights_summary,
    result_processing_pre_hook,
    result_processing_post_hook,
    notify_outputs
)
from doorbeen.core.models.provider import ModelHandler


class ResultProcessingResponse(TSModel):
    """Structured response schema for the Result Processing Agent."""
    data_summary: str = Field(description="A comprehensive summary of the dataset and key findings.")
    key_insights: List[str] = Field(description="A list of key, actionable insights extracted from the comprehensive analysis.", default_factory=list)
    trends_and_patterns: List[str] = Field(description="A list of key trends and patterns identified in the data.", default_factory=list)
    recommendations: List[str] = Field(description="A list of actionable recommendations based on the analysis findings.", default_factory=list)
    analysis_components_used: List[str] = Field(description="List of analysis components that were used (e.g., statistical_analysis, trend_analysis, etc.).", default_factory=list)

    model_config = ConfigDict(extra="forbid")


def create_result_processing_agent(
    name: str,
    handler: ModelHandler,
):
    """Creates a result processing agent with comprehensive pandas-based analysis capabilities."""
    system_message = """
You are an expert data analyst specialized in extracting actionable insights from SQL query results.

Your role is to analyze the execution results and generate comprehensive insights that directly answer the user's question.

## ANALYSIS APPROACH:

**IMPORTANT**: You should ONLY use the `generate_insights_summary` tool. This tool has been enhanced to work directly with the execution results and will provide comprehensive analysis.

## YOUR TASK:

1. **Use only `generate_insights_summary`** - This tool will:
   - Analyze the actual query execution results
   - Generate a comprehensive data summary
   - Extract key insights and trends
   - Provide actionable recommendations

2. **Focus on the user's question** - Ensure all insights directly address what the user asked

3. **Be specific and data-driven** - Use actual numbers, percentages, and specific findings from the results

4. **MANDATORY FINAL STEP** - Always call `notify_outputs` after completing analysis to provide important context about accomplishments

## IMPORTANT GUIDELINES:

- **DO NOT use other analysis tools** - The `generate_insights_summary` tool is sufficient and will handle all analysis internally
- **Reference actual data** - Make sure insights are based on the specific execution results, not generic analysis
- **Connect to business value** - Provide insights that have clear business implications
- **Be comprehensive** - The single tool call should provide complete analysis
- **ALWAYS call `notify_outputs` at the end** - This is mandatory for proper workflow tracking

Your goal is to transform raw query results into actionable business insights that directly answer the user's question.
"""
    
    tools = [
        analyze_dataset_overview,
        get_top_values_analysis,
        aggregate_data_analysis,
        statistical_analysis,
        trend_analysis,
        correlation_analysis,
        outlier_detection,
        categorical_analysis,
        generate_insights_summary,
        notify_outputs,
    ]
    
    return create_react_agent(
        name=name,
        model=handler.model,
        tools=tools,
        prompt=system_message,
        state_schema=SQLSupervisorState,
        pre_model_hook=result_processing_pre_hook,
        post_model_hook=result_processing_post_hook,
        response_format=ResultProcessingResponse
    ) 