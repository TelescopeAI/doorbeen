"""
Enhanced result processing tools with pandas-based analysis capabilities.
Each tool performs a specific type of analysis on the query results.
"""

import json
from typing import Dict, Any, List, Optional, Union
from typing_extensions import Annotated

from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState
from doorbeen.core.assistants.analysis.sql.tools.pandas_analysis import DataAnalyzer


@tool
async def analyze_dataset_overview(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Get a comprehensive overview of the dataset structure and basic statistics."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": "Analyzing dataset structure and overview...",
                "content": "📊 Getting dataset overview",
                "progress": 10
            }
        }
        
        data = state.get("execution_results", [])
        user_question = state.get("input", "")
        
        if not data:
            error_event = {
                "type": "agent:warning",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": "No data available for analysis",
                    "content": "⚠️ Query returned no results to analyze",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="⚠️ No data available for analysis",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        # Initialize data analyzer
        analyzer = DataAnalyzer(data, max_direct_analysis_rows=100)
        
        # Get basic dataset information
        basic_info = analyzer.get_basic_info()
        
        # Get a sample of the data
        data_sample = analyzer.get_data_sample(n=5, method="head")
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Dataset overview complete - {basic_info.get('total_rows', 0)} rows, {basic_info.get('total_columns', 0)} columns",
                "content": f"✅ Dataset Overview:\n- Rows: {basic_info.get('total_rows', 0)}\n- Columns: {basic_info.get('total_columns', 0)}\n- Requires aggregation: {basic_info.get('requires_aggregation', False)}",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content=f"✅ Dataset overview complete - {basic_info.get('total_rows', 0)} rows analyzed",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, completion_progress_event],
                "dataset_overview": {
                    "basic_info": basic_info,
                    "data_sample": data_sample,
                    "user_question": user_question
                },
                "analysis_strategy": "direct" if len(data) <= 100 else "aggregated"
            }
        )
        
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Dataset overview analysis failed: {str(e)}",
                "content": f"❌ Failed to analyze dataset overview: {str(e)}",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Dataset overview analysis failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "dataset_overview_error", "message": str(e)}
            }
        )


@tool
async def get_top_values_analysis(
    column: str,
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    n: int = 10,
    sort_by: str = "count"
) -> Command:
    """Get top N values for a specific column, sorted by count or value."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Analyzing top {n} values in column '{column}'...",
                "content": f"🔍 Getting top values for {column}",
                "progress": 20
            }
        }
        
        data = state.get("execution_results", [])
        
        if not data:
            error_event = {
                "type": "agent:warning",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": "No data available for top values analysis",
                    "content": "⚠️ No data to analyze",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="⚠️ No data available for analysis",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        # Initialize data analyzer
        analyzer = DataAnalyzer(data)
        
        # Get top values
        top_values = analyzer.get_top_values(column, n, sort_by)
        
        if "error" in top_values:
            error_event = {
                "type": "agent:error",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": f"Top values analysis failed: {top_values['error']}",
                    "content": f"❌ {top_values['error']}",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content=f"❌ {top_values['error']}",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Top {n} values analysis complete for column '{column}'",
                "content": f"✅ Found {len(top_values.get('results', []))} top values for {column}",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content=f"✅ Top {n} values analysis complete for column '{column}'",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, completion_progress_event],
                "top_values_analysis": top_values
            }
        )
        
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Top values analysis failed: {str(e)}",
                "content": f"❌ Failed to analyze top values: {str(e)}",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Top values analysis failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "top_values_error", "message": str(e)}
            }
        )


@tool
async def aggregate_data_analysis(
    group_by: Union[str, List[str]],
    agg_column: str,
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    agg_function: str = "sum"
) -> Command:
    """Aggregate data by one or more columns using various aggregation functions."""
    
    try:
        # Emit initial progress event
        group_by_str = group_by if isinstance(group_by, str) else ", ".join(group_by)
        start_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Aggregating {agg_column} by {group_by_str} using {agg_function}...",
                "content": f"📊 Grouping data by {group_by_str}",
                "progress": 20
            }
        }
        
        data = state.get("execution_results", [])
        
        if not data:
            error_event = {
                "type": "agent:warning",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": "No data available for aggregation",
                    "content": "⚠️ No data to aggregate",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="⚠️ No data available for aggregation",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        # Initialize data analyzer
        analyzer = DataAnalyzer(data)
        
        # Perform aggregation
        aggregation_result = analyzer.aggregate_data(group_by, agg_column, agg_function)
        
        if "error" in aggregation_result:
            error_event = {
                "type": "agent:error",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": f"Aggregation failed: {aggregation_result['error']}",
                    "content": f"❌ {aggregation_result['error']}",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content=f"❌ {aggregation_result['error']}",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Aggregation complete - {aggregation_result.get('total_groups', 0)} groups created",
                "content": f"✅ Aggregated {agg_column} by {group_by_str} ({aggregation_result.get('total_groups', 0)} groups)",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content=f"✅ Aggregation complete - {aggregation_result.get('total_groups', 0)} groups created",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, completion_progress_event],
                "aggregation_analysis": aggregation_result
            }
        )
        
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Aggregation analysis failed: {str(e)}",
                "content": f"❌ Failed to aggregate data: {str(e)}",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Aggregation analysis failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "aggregation_error", "message": str(e)}
            }
        )


@tool
async def statistical_analysis(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    columns: Optional[List[str]] = None
) -> Command:
    """Perform statistical analysis on numeric columns."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": "Performing statistical analysis on numeric columns...",
                "content": "📊 Computing statistical summaries",
                "progress": 20
            }
        }
        
        data = state.get("execution_results", [])
        
        if not data:
            error_event = {
                "type": "agent:warning",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": "No data available for statistical analysis",
                    "content": "⚠️ No data for statistics",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="⚠️ No data available for statistical analysis",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        # Initialize data analyzer
        analyzer = DataAnalyzer(data)
        
        # Perform statistical analysis
        stats_result = analyzer.get_statistical_summary(columns)
        
        if "error" in stats_result:
            error_event = {
                "type": "agent:error",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": f"Statistical analysis failed: {stats_result['error']}",
                    "content": f"❌ {stats_result['error']}",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content=f"❌ {stats_result['error']}",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Statistical analysis complete for {len(stats_result.get('columns_analyzed', []))} columns",
                "content": f"✅ Statistical analysis complete for: {', '.join(stats_result.get('columns_analyzed', []))}",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content=f"✅ Statistical analysis complete for {len(stats_result.get('columns_analyzed', []))} columns",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, completion_progress_event],
                "statistical_analysis": stats_result
            }
        )
        
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Statistical analysis failed: {str(e)}",
                "content": f"❌ Failed to perform statistical analysis: {str(e)}",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Statistical analysis failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "statistical_analysis_error", "message": str(e)}
            }
        )


@tool
async def trend_analysis(
    column: str,
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    time_column: Optional[str] = None,
    window_size: int = 5
) -> Command:
    """Detect trends in a numeric column, optionally over time."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Analyzing trends in column '{column}'...",
                "content": f"📈 Detecting trends in {column}",
                "progress": 20
            }
        }
        
        data = state.get("execution_results", [])
        
        if not data:
            error_event = {
                "type": "agent:warning",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": "No data available for trend analysis",
                    "content": "⚠️ No data for trend analysis",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="⚠️ No data available for trend analysis",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        # Initialize data analyzer
        analyzer = DataAnalyzer(data)
        
        # Perform trend analysis
        trend_result = analyzer.detect_trends(column, time_column, window_size)
        
        if "error" in trend_result:
            error_event = {
                "type": "agent:error",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": f"Trend analysis failed: {trend_result['error']}",
                    "content": f"❌ {trend_result['error']}",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content=f"❌ {trend_result['error']}",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Trend analysis complete - {trend_result.get('trend_direction', 'unknown')} trend detected",
                "content": f"✅ Trend analysis: {column} shows {trend_result.get('trend_direction', 'unknown')} trend",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content=f"✅ Trend analysis complete - {trend_result.get('trend_direction', 'unknown')} trend detected",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, completion_progress_event],
                "trend_analysis": trend_result
            }
        )
        
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Trend analysis failed: {str(e)}",
                "content": f"❌ Failed to analyze trends: {str(e)}",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Trend analysis failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "trend_analysis_error", "message": str(e)}
            }
        )


@tool
async def correlation_analysis(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    columns: Optional[List[str]] = None,
    min_correlation: float = 0.3
) -> Command:
    """Find correlations between numeric columns."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": "Analyzing correlations between numeric columns...",
                "content": "🔗 Finding correlations",
                "progress": 20
            }
        }
        
        data = state.get("execution_results", [])
        
        if not data:
            error_event = {
                "type": "agent:warning",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": "No data available for correlation analysis",
                    "content": "⚠️ No data for correlation analysis",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="⚠️ No data available for correlation analysis",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        # Initialize data analyzer
        analyzer = DataAnalyzer(data)
        
        # Perform correlation analysis
        corr_result = analyzer.find_correlations(columns, min_correlation)
        
        if "error" in corr_result:
            error_event = {
                "type": "agent:error",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": f"Correlation analysis failed: {corr_result['error']}",
                    "content": f"❌ {corr_result['error']}",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content=f"❌ {corr_result['error']}",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Correlation analysis complete - {len(corr_result.get('significant_correlations', []))} significant correlations found",
                "content": f"✅ Found {len(corr_result.get('significant_correlations', []))} significant correlations",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content=f"✅ Correlation analysis complete - {len(corr_result.get('significant_correlations', []))} significant correlations found",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, completion_progress_event],
                "correlation_analysis": corr_result
            }
        )
        
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Correlation analysis failed: {str(e)}",
                "content": f"❌ Failed to analyze correlations: {str(e)}",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Correlation analysis failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "correlation_analysis_error", "message": str(e)}
            }
        )


@tool
async def outlier_detection(
    column: str,
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    method: str = "iqr"
) -> Command:
    """Identify outliers in a numeric column using various methods."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Detecting outliers in column '{column}' using {method} method...",
                "content": f"🎯 Finding outliers in {column}",
                "progress": 20
            }
        }
        
        data = state.get("execution_results", [])
        
        if not data:
            error_event = {
                "type": "agent:warning",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": "No data available for outlier detection",
                    "content": "⚠️ No data for outlier detection",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="⚠️ No data available for outlier detection",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        # Initialize data analyzer
        analyzer = DataAnalyzer(data)
        
        # Perform outlier detection
        outlier_result = analyzer.identify_outliers(column, method)
        
        if "error" in outlier_result:
            error_event = {
                "type": "agent:error",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": f"Outlier detection failed: {outlier_result['error']}",
                    "content": f"❌ {outlier_result['error']}",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content=f"❌ {outlier_result['error']}",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Outlier detection complete - {outlier_result.get('outlier_count', 0)} outliers found",
                "content": f"✅ Found {outlier_result.get('outlier_count', 0)} outliers ({outlier_result.get('outlier_percentage', 0):.1f}%)",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content=f"✅ Outlier detection complete - {outlier_result.get('outlier_count', 0)} outliers found",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, completion_progress_event],
                "outlier_analysis": outlier_result
            }
        )
        
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Outlier detection failed: {str(e)}",
                "content": f"❌ Failed to detect outliers: {str(e)}",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Outlier detection failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "outlier_detection_error", "message": str(e)}
            }
        )


@tool
async def categorical_analysis(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    columns: Optional[List[str]] = None
) -> Command:
    """Analyze categorical columns for patterns and distributions."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": "Analyzing categorical columns for patterns...",
                "content": "📊 Analyzing categorical data",
                "progress": 20
            }
        }
        
        data = state.get("execution_results", [])
        
        if not data:
            error_event = {
                "type": "agent:warning",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": "No data available for categorical analysis",
                    "content": "⚠️ No data for categorical analysis",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="⚠️ No data available for categorical analysis",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        # Initialize data analyzer
        analyzer = DataAnalyzer(data)
        
        # Perform categorical analysis
        categorical_result = analyzer.analyze_categorical_columns(columns)
        
        if "error" in categorical_result:
            error_event = {
                "type": "agent:error",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": f"Categorical analysis failed: {categorical_result['error']}",
                    "content": f"❌ {categorical_result['error']}",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content=f"❌ {categorical_result['error']}",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Categorical analysis complete for {len(categorical_result.get('columns_analyzed', []))} columns",
                "content": f"✅ Analyzed {len(categorical_result.get('columns_analyzed', []))} categorical columns",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content=f"✅ Categorical analysis complete for {len(categorical_result.get('columns_analyzed', []))} columns",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, completion_progress_event],
                "categorical_analysis": categorical_result
            }
        )
        
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Categorical analysis failed: {str(e)}",
                "content": f"❌ Failed to analyze categorical data: {str(e)}",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Categorical analysis failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "categorical_analysis_error", "message": str(e)}
            }
        )


@tool
async def generate_insights_summary(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Generate a comprehensive insights summary from execution results and any available analysis results."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": "Generating comprehensive insights summary...",
                "content": "🧠 Analyzing execution results and generating insights",
                "progress": 10
            }
        }
    
        configuration = config.get("configurable", {})
        handler: ModelHandler = configuration.get("handler")
        
        if not handler:
            error_event = {
                "type": "agent:error",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": "Model handler not available",
                    "content": "❌ No model handler for insight generation",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="❌ Model handler not available",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event],
                    "error": {"type": "handler_error", "message": "Model handler not set"}
                }
            )
        
        # Gather all data from state
        user_question = state.get("input", "")
        sql_query = state.get("sql_query", "")
        execution_results = state.get("execution_results", [])
        
        # Check if we have execution results
        if not execution_results:
            error_event = {
                "type": "agent:warning",
                "name": "ResultProcessing",
                "data": {
                    "scope": "ResultProcessing",
                    "description": "No execution results available for analysis",
                    "content": "⚠️ No query results to analyze",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="⚠️ No execution results available for analysis",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        # Get optional analysis results from other tools (if available)
        dataset_overview = state.get("dataset_overview", {})
        top_values_analysis = state.get("top_values_analysis", {})
        aggregation_analysis = state.get("aggregation_analysis", {})
        statistical_analysis = state.get("statistical_analysis", {})
        trend_analysis = state.get("trend_analysis", {})
        correlation_analysis = state.get("correlation_analysis", {})
        outlier_analysis = state.get("outlier_analysis", {})
        categorical_analysis = state.get("categorical_analysis", {})
        analysis_strategy = state.get("analysis_strategy", "direct")
        
        # Emit data analysis progress
        analysis_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Analyzing {len(execution_results)} execution results...",
                "content": f"📊 Processing {len(execution_results)} rows of data",
                "progress": 30
            }
        }
        
        # Prepare execution results for analysis (limit to first 100 rows for prompt)
        sample_results = execution_results[:100] if len(execution_results) > 100 else execution_results
        
        # Create comprehensive insights prompt that works with actual execution results
        insights_prompt = f"""
You are a senior data analyst creating comprehensive insights from SQL query execution results.

USER QUESTION: {user_question}

SQL QUERY EXECUTED:
{sql_query}

EXECUTION RESULTS ({len(execution_results)} total rows, showing first {len(sample_results)} rows):
{json.dumps(sample_results, indent=2)}

DATASET SUMMARY:
- Total rows: {len(execution_results)}
- Sample size analyzed: {len(sample_results)}
- Analysis strategy: {analysis_strategy}

ADDITIONAL ANALYSIS RESULTS (if available):
{json.dumps({
    "dataset_overview": dataset_overview,
    "top_values_analysis": top_values_analysis,
    "aggregation_analysis": aggregation_analysis,
    "statistical_analysis": statistical_analysis,
    "trend_analysis": trend_analysis,
    "correlation_analysis": correlation_analysis,
    "outlier_analysis": outlier_analysis,
    "categorical_analysis": categorical_analysis
}, indent=2)}

TASK: Create a comprehensive analysis that includes:

1. **DATA SUMMARY**: A clear, comprehensive summary of what the data shows in relation to the user's question. Reference specific values, trends, and patterns found in the execution results.

2. **KEY INSIGHTS**: Extract 3-5 key actionable insights that directly answer the user's question. Each insight should:
   - Be specific to the data (include actual numbers, percentages, or values)
   - Address the user's question directly
   - Have clear business implications
   - Be supported by the execution results

3. **TRENDS AND PATTERNS**: Identify 3-5 significant trends or patterns in the data that are relevant to the user's question. Each should:
   - Be specific and measurable
   - Reference actual data points from the results
   - Explain what the trend means for the user's question

4. **RECOMMENDATIONS**: Provide 2-3 actionable recommendations based on the analysis.

IMPORTANT:
- Focus on the ACTUAL execution results, not generic analysis
- Reference specific data points, values, and findings from the results
- Connect every insight directly to the user's question
- Be specific rather than generic
- Use the actual data to support every statement

Return your analysis in the following JSON format:
{{
    "data_summary": "Comprehensive summary of the data and key findings...",
    "key_insights": ["Specific insight 1 with data", "Specific insight 2 with data", ...],
    "trends_and_patterns": ["Specific trend 1 with data", "Specific trend 2 with data", ...],
    "recommendations": ["Actionable recommendation 1", "Actionable recommendation 2", ...]
}}
"""
        
        # Generate comprehensive insights
        insights_response = await handler.model.ainvoke(insights_prompt)
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": "Comprehensive insights summary generated",
                "content": "✅ Generated comprehensive insights from execution results",
                "progress": 100
            }
        }
        
        # Parse the JSON response
        try:
            insights_data = json.loads(insights_response.content)
            
            data_summary = insights_data.get("data_summary", "")
            key_insights = insights_data.get("key_insights", [])
            trends_and_patterns = insights_data.get("trends_and_patterns", [])
            recommendations = insights_data.get("recommendations", [])
            
            # Ensure all fields are lists where expected
            if not isinstance(key_insights, list):
                key_insights = [key_insights] if key_insights else []
            if not isinstance(trends_and_patterns, list):
                trends_and_patterns = [trends_and_patterns] if trends_and_patterns else []
            if not isinstance(recommendations, list):
                recommendations = [recommendations] if recommendations else []
                
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            data_summary = insights_response.content
            key_insights = ["Analysis completed - see data summary for details"]
            trends_and_patterns = ["Trends identified - see data summary for details"]
            recommendations = ["Recommendations provided - see data summary for details"]
        
        # Track which analysis components were used
        analysis_components_used = [
            key for key in [
                "dataset_overview", "top_values_analysis", "aggregation_analysis",
                "statistical_analysis", "trend_analysis", "correlation_analysis",
                "outlier_analysis", "categorical_analysis"
            ] if state.get(key)
        ]
        
        # Add execution_results as a component since we always use it
        analysis_components_used.append("execution_results")
        
        tool_message = ToolMessage(
            content=f"✅ Comprehensive insights generated from {len(execution_results)} execution results - {len(key_insights)} insights, {len(trends_and_patterns)} trends, {len(recommendations)} recommendations",
            tool_call_id=tool_call_id
        )
        
        # Update state with the fields that the finalizer expects
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, analysis_progress_event, completion_progress_event],
                # Core fields expected by finalizer
                "data_summary": data_summary,
                "key_insights": key_insights,
                "trends_and_patterns": trends_and_patterns,
                "recommendations": recommendations,
                # Additional tracking fields
                "analysis_components_used": analysis_components_used,
                "analysis_strategy": analysis_strategy
            }
        )
        
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Insights generation failed: {str(e)}",
                "content": f"❌ Failed to generate insights: {str(e)}",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Insights generation failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "insights_generation_error", "message": str(e)}
            }
        )


@tool
async def notify_outputs(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Notify about the outputs and accomplishments of the result processing agent."""
    
    try:
        # Extract relevant information from state
        data_summary = state.get("data_summary", "")
        key_insights = state.get("key_insights", [])
        trends_and_patterns = state.get("trends_and_patterns", [])
        recommendations = state.get("recommendations", [])
        analysis_components = state.get("analysis_components_used", [])
        analysis_strategy = state.get("analysis_strategy", "direct")
        execution_results = state.get("execution_results", [])
        
        # Build contextual content
        content_parts = ["📊 Result Analysis Complete"]
        
        # Add data processing summary
        if execution_results:
            content_parts.append(f"\n**Data Processed:** {len(execution_results)} rows analyzed")
        
        # Add analysis strategy
        content_parts.append(f"**Analysis Method:** {analysis_strategy}")
        
        # Add key findings summary
        findings_summary = []
        if key_insights:
            findings_summary.append(f"{len(key_insights)} insights")
        if trends_and_patterns:
            findings_summary.append(f"{len(trends_and_patterns)} trends")
        if recommendations:
            findings_summary.append(f"{len(recommendations)} recommendations")
        
        if findings_summary:
            content_parts.append(f"**Generated:** {', '.join(findings_summary)}")
        
        # Add sample insight if available
        if key_insights and len(key_insights) > 0:
            first_insight = key_insights[0]
            if len(first_insight) > 100:
                first_insight = first_insight[:100] + "..."
            content_parts.append(f"\n**Key Finding:** {first_insight}")
        
        # Add analysis components used
        if analysis_components:
            # Filter out 'execution_results' since it's always present
            components = [comp for comp in analysis_components if comp != "execution_results"]
            if components:
                content_parts.append(f"**Analysis Tools:** {', '.join(components[:3])}")
        
        # Create the notification event
        notification_event = {
            "type": "agent:end",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Completed {analysis_strategy} analysis with {len(key_insights)} insights and {len(trends_and_patterns)} trends",
                "content": "\n".join(content_parts)
            }
        }
        
        tool_message = ToolMessage(
            content="✅ Result processing outputs notified",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [notification_event]
            }
        )
        
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": f"Output notification failed: {str(e)}",
                "content": f"❌ Failed to notify outputs: {str(e)}",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Output notification failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event]
            }
        )


def result_processing_pre_hook(state: Annotated[dict, InjectedState]) -> dict:
    """Pre-model hook for result processing agent - emits agent start event"""
    data = state.get("execution_results", [])
    row_count = len(data)
    
    event = {
        "type": "agent:start",
        "name": "ResultProcessing",
        "data": {
            "scope": "ResultProcessing",
            "description": f"Processing {row_count} query results with pandas-based analysis",
            "content": f"📊 Starting advanced result processing for {row_count} rows"
        }
    }
    return {"agent_lifecycle_events": [event]}


def result_processing_post_hook(state: Annotated[dict, InjectedState]) -> dict:
    """Post-model hook for result processing agent - emits agent end event with contextual information"""
    # Extract relevant information from state
    data_summary = state.get("data_summary", "")
    key_insights = state.get("key_insights", [])
    trends_and_patterns = state.get("trends_and_patterns", [])
    recommendations = state.get("recommendations", [])
    analysis_components = state.get("analysis_components_used", [])
    analysis_strategy = state.get("analysis_strategy", "direct")
    execution_results = state.get("execution_results", [])
    
    # Build contextual content
    content_parts = ["📊 Result Analysis Complete"]
    
    # Add data processing summary
    if execution_results:
        content_parts.append(f"\n**Data Processed:** {len(execution_results)} rows analyzed")
    
    # Add analysis strategy
    content_parts.append(f"**Analysis Method:** {analysis_strategy}")
    
    # Add key findings summary
    findings_summary = []
    if key_insights:
        findings_summary.append(f"{len(key_insights)} insights")
    if trends_and_patterns:
        findings_summary.append(f"{len(trends_and_patterns)} trends")
    if recommendations:
        findings_summary.append(f"{len(recommendations)} recommendations")
    
    if findings_summary:
        content_parts.append(f"**Generated:** {', '.join(findings_summary)}")
    
    # Add sample insight if available
    if key_insights and len(key_insights) > 0:
        first_insight = key_insights[0]
        if len(first_insight) > 100:
            first_insight = first_insight[:100] + "..."
        content_parts.append(f"\n**Key Finding:** {first_insight}")
    
    # Add analysis components used
    if analysis_components:
        # Filter out 'execution_results' since it's always present
        components = [comp for comp in analysis_components if comp != "execution_results"]
        if components:
            content_parts.append(f"**Analysis Tools:** {', '.join(components[:3])}")
    
    event = {
        "type": "agent:end",
        "name": "ResultProcessing",
        "data": {
            "scope": "ResultProcessing",
            "description": f"Completed {analysis_strategy} analysis with {len(key_insights)} insights and {len(trends_and_patterns)} trends",
            "content": "\n".join(content_parts)
        }
    }
    return {"agent_lifecycle_events": [event]} 