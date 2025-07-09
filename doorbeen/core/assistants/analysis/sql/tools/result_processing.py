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
    """Generate a comprehensive insights summary from all analysis results and update state for finalizer."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": "Generating comprehensive insights summary...",
                "content": "🧠 Synthesizing all analysis results",
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
        
        # Gather all analysis results from state
        user_question = state.get("input", "")
        sql_query = state.get("sql_query", "")
        execution_results = state.get("execution_results", [])
        dataset_overview = state.get("dataset_overview", {})
        top_values_analysis = state.get("top_values_analysis", {})
        aggregation_analysis = state.get("aggregation_analysis", {})
        statistical_analysis = state.get("statistical_analysis", {})
        trend_analysis = state.get("trend_analysis", {})
        correlation_analysis = state.get("correlation_analysis", {})
        outlier_analysis = state.get("outlier_analysis", {})
        categorical_analysis = state.get("categorical_analysis", {})
        analysis_strategy = state.get("analysis_strategy", "direct")
        
        # Emit synthesis progress
        synthesis_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": "Synthesizing insights from all analysis components...",
                "content": "🎯 Connecting analysis results to user question",
                "progress": 30
            }
        }
        
        # Create comprehensive insights prompt for data summary
        data_summary_prompt = f"""
You are a senior data analyst creating a comprehensive data summary that directly addresses the user's question.

USER QUESTION: {user_question}

SQL QUERY EXECUTED:
{sql_query}

DATASET INFORMATION:
- Total rows: {len(execution_results)}
- Analysis strategy: {analysis_strategy}

ANALYSIS RESULTS:

Dataset Overview:
{json.dumps(dataset_overview, indent=2) if dataset_overview else "No dataset overview available"}

Top Values Analysis:
{json.dumps(top_values_analysis, indent=2) if top_values_analysis else "No top values analysis available"}

Aggregation Analysis:
{json.dumps(aggregation_analysis, indent=2) if aggregation_analysis else "No aggregation analysis available"}

Statistical Analysis:
{json.dumps(statistical_analysis, indent=2) if statistical_analysis else "No statistical analysis available"}

Trend Analysis:
{json.dumps(trend_analysis, indent=2) if trend_analysis else "No trend analysis available"}

Correlation Analysis:
{json.dumps(correlation_analysis, indent=2) if correlation_analysis else "No correlation analysis available"}

Outlier Analysis:
{json.dumps(outlier_analysis, indent=2) if outlier_analysis else "No outlier analysis available"}

Categorical Analysis:
{json.dumps(categorical_analysis, indent=2) if categorical_analysis else "No categorical analysis available"}

Create a comprehensive data summary that:
1. Directly answers the user's question using the analysis results
2. Highlights the most significant findings
3. Includes specific numbers and statistics
4. Explains what the data reveals about the user's question
5. Is clear and actionable

Focus on being specific to the user's question rather than generic.
"""
        
        # Generate data summary
        data_summary_response = await handler.model.ainvoke(data_summary_prompt)
        
        # Emit trends analysis progress
        trends_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": "Extracting trends and patterns...",
                "content": "📈 Identifying key trends and patterns",
                "progress": 60
            }
        }
        
        # Create trends and patterns prompt
        trends_prompt = f"""
Based on the analysis results, identify the key trends and patterns that are relevant to the user's question.

USER QUESTION: {user_question}

ANALYSIS RESULTS:
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

Return a JSON list of strings, each describing a specific trend or pattern found in the data.
Focus on trends that help answer the user's question.
Each trend should be a concise, specific statement with supporting data.

Example format:
["Transaction volume increased by 25% in Q3 compared to Q2", "Customer retention rate is highest in the premium segment at 85%"]
"""
        
        trends_response = await handler.model.ainvoke(trends_prompt)
        
        # Emit insights progress
        insights_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": "Extracting key insights...",
                "content": "💡 Generating actionable insights",
                "progress": 80
            }
        }
        
        # Create key insights prompt
        insights_prompt = f"""
Based on the analysis results, generate key actionable insights that directly address the user's question.

USER QUESTION: {user_question}

ANALYSIS RESULTS:
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

Return a JSON list of strings, each containing a key insight that helps answer the user's question.
Focus on actionable insights with business value.
Each insight should be specific and supported by the data.

Example format:
["The top 3 product categories account for 60% of total revenue, suggesting opportunity for focused marketing", "Customer churn is 3x higher in the first month, indicating need for improved onboarding"]
"""
        
        insights_response = await handler.model.ainvoke(insights_prompt)
        
        # Parse JSON responses
        try:
            trends_list = json.loads(trends_response.content)
            if not isinstance(trends_list, list):
                trends_list = [trends_response.content]
        except:
            trends_list = [trends_response.content]
        
        try:
            insights_list = json.loads(insights_response.content)
            if not isinstance(insights_list, list):
                insights_list = [insights_response.content]
        except:
            insights_list = [insights_response.content]
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "ResultProcessing",
            "data": {
                "scope": "ResultProcessing",
                "description": "Comprehensive insights summary generated",
                "content": f"✅ Generated {len(insights_list)} insights and {len(trends_list)} trends",
                "progress": 100
            }
        }
        
        # Track which analysis components were used
        analysis_components_used = [
            key for key in [
                "dataset_overview", "top_values_analysis", "aggregation_analysis",
                "statistical_analysis", "trend_analysis", "correlation_analysis",
                "outlier_analysis", "categorical_analysis"
            ] if state.get(key)
        ]
        
        tool_message = ToolMessage(
            content=f"✅ Comprehensive insights summary generated - {len(insights_list)} insights, {len(trends_list)} trends",
            tool_call_id=tool_call_id
        )
        
        # Update state with the fields that the finalizer expects
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, synthesis_progress_event, trends_progress_event, insights_progress_event, completion_progress_event],
                # Core fields expected by finalizer
                "data_summary": data_summary_response.content,
                "trends_and_patterns": trends_list,
                "key_insights": insights_list,
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
    """Post-model hook for result processing agent - emits agent end event"""
    data_summary = state.get("data_summary", "")
    key_insights = state.get("key_insights", [])
    trends_and_patterns = state.get("trends_and_patterns", [])
    analysis_components = state.get("analysis_components_used", [])
    analysis_strategy = state.get("analysis_strategy", "direct")
    
    event = {
        "type": "agent:end",
        "name": "ResultProcessing",
        "data": {
            "scope": "ResultProcessing",
            "description": f"Completed {analysis_strategy} analysis with {len(key_insights)} insights and {len(trends_and_patterns)} trends",
            "content": f"✅ Generated {len(key_insights)} insights and {len(trends_and_patterns)} trends using {len(analysis_components)} analysis components"
        }
    }
    return {"agent_lifecycle_events": [event]} 