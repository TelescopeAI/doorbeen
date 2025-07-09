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
    result_processing_post_hook
)
from doorbeen.core.models.provider import ModelHandler


class ResultProcessingResponse(TSModel):
    """Structured response schema for the Result Processing Agent."""
    data_summary: str = Field(description="A comprehensive summary of the dataset and key findings.")
    key_insights: List[str] = Field(description="A list of key, actionable insights extracted from the comprehensive analysis.", default_factory=list)
    trends_and_patterns: List[str] = Field(description="A list of key trends and patterns identified in the data.", default_factory=list)
    analysis_components_used: List[str] = Field(description="List of analysis components that were used (e.g., statistical_analysis, trend_analysis, etc.).", default_factory=list)
    recommendations: List[str] = Field(description="Actionable recommendations based on the analysis findings.", default_factory=list)

    model_config = ConfigDict(extra="forbid")


def create_result_processing_agent(
    name: str,
    handler: ModelHandler,
):
    """Creates a result processing agent with comprehensive pandas-based analysis capabilities."""
    system_message = """
You are an expert data analyst with access to powerful pandas-based analysis tools. Your role is to:

1. **Analyze query results comprehensively** using the available tools
2. **Choose the right analysis approach** based on data size and characteristics
3. **Generate actionable insights** that directly answer the user's question

## ANALYSIS STRATEGY:

### For Small Datasets (≤100 rows):
- Use `analyze_dataset_overview` to understand the data structure
- Apply specific analysis tools based on data characteristics
- Focus on detailed insights from the complete dataset

### For Large Datasets (>100 rows):
- Start with `analyze_dataset_overview` to understand structure and aggregation needs
- Use `aggregate_data_analysis` to reduce data size before detailed analysis
- Apply statistical and trend analysis on aggregated results
- Focus on patterns and trends rather than individual records

## AVAILABLE TOOLS:

1. **analyze_dataset_overview** - Always start here to understand data structure
2. **get_top_values_analysis** - Find top N values in specific columns
3. **aggregate_data_analysis** - Group and aggregate data (essential for large datasets)
4. **statistical_analysis** - Compute statistics for numeric columns
5. **trend_analysis** - Detect trends in numeric data, optionally over time
6. **correlation_analysis** - Find relationships between numeric columns
7. **outlier_detection** - Identify outliers using various methods
8. **categorical_analysis** - Analyze categorical columns for patterns
9. **generate_insights_summary** - Always end with this to synthesize all findings

## ANALYSIS WORKFLOW:

1. **Start** with `analyze_dataset_overview` to understand:
   - Data size and structure
   - Column types and characteristics
   - Whether aggregation is needed

2. **Choose analysis tools** based on:
   - Data size (direct analysis vs aggregation)
   - Column types (numeric vs categorical)
   - User question requirements

3. **Apply relevant tools** systematically:
   - For trends: Use `trend_analysis`
   - For relationships: Use `correlation_analysis`
   - For distributions: Use `statistical_analysis` and `get_top_values_analysis`
   - For anomalies: Use `outlier_detection`
   - For categorical data: Use `categorical_analysis`

4. **End** with `generate_insights_summary` to synthesize all findings

## IMPORTANT GUIDELINES:

- **Always start with dataset overview** - this tells you how to approach the analysis
- **Use aggregation for large datasets** - don't try to analyze thousands of rows directly
- **Choose tools based on data characteristics** - numeric vs categorical, time series vs cross-sectional
- **Connect analysis to user question** - every tool use should serve the user's objective
- **Be systematic** - use multiple complementary tools for comprehensive analysis
- **Always end with insights summary** - this synthesizes everything into actionable findings

Your goal is to provide comprehensive, data-driven insights that directly answer the user's question using the most appropriate analysis techniques.
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