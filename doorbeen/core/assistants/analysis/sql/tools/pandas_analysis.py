"""
Pandas-based data analysis utilities for SQL result processing.
This module provides a comprehensive set of data analysis functions that can be used
by the ResultProcessor agent to analyze query results efficiently.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
import json
from datetime import datetime, timedelta


class DataAnalyzer:
    """
    Comprehensive data analysis utility class using pandas.
    Provides methods for statistical analysis, trend detection, and insight generation.
    """
    
    def __init__(self, data: List[Dict[str, Any]], max_direct_analysis_rows: int = 100):
        """
        Initialize the DataAnalyzer with query results.
        
        Args:
            data: List of dictionaries representing query results
            max_direct_analysis_rows: Maximum rows to analyze directly without aggregation
        """
        self.data = data
        self.df = pd.DataFrame(data) if data else pd.DataFrame()
        self.max_direct_rows = max_direct_analysis_rows
        self.requires_aggregation = len(data) > max_direct_analysis_rows
        
    def get_basic_info(self) -> Dict[str, Any]:
        """Get basic information about the dataset."""
        if self.df.empty:
            return {"error": "No data available for analysis"}
            
        return {
            "total_rows": len(self.df),
            "total_columns": len(self.df.columns),
            "column_names": list(self.df.columns),
            "column_types": {col: str(dtype) for col, dtype in self.df.dtypes.items()},
            "memory_usage": self.df.memory_usage(deep=True).sum(),
            "requires_aggregation": self.requires_aggregation,
            "null_counts": self.df.isnull().sum().to_dict(),
            "duplicate_rows": self.df.duplicated().sum()
        }
    
    def get_top_values(self, column: str, n: int = 10, sort_by: str = "count") -> Dict[str, Any]:
        """
        Get top N values for a column.
        
        Args:
            column: Column name to analyze
            n: Number of top values to return
            sort_by: 'count' for frequency, 'value' for actual values
        """
        if self.df.empty or column not in self.df.columns:
            return {"error": f"Column '{column}' not found or no data available"}
            
        try:
            if sort_by == "count":
                top_values = self.df[column].value_counts().head(n)
                return {
                    "column": column,
                    "sort_by": sort_by,
                    "results": [{"value": str(val), "count": int(count)} for val, count in top_values.items()]
                }
            else:
                # Sort by actual values
                if pd.api.types.is_numeric_dtype(self.df[column]):
                    top_values = self.df[column].nlargest(n)
                else:
                    top_values = self.df[column].sort_values(ascending=False).head(n)
                
                return {
                    "column": column,
                    "sort_by": sort_by,
                    "results": [{"value": str(val), "index": int(idx)} for idx, val in top_values.items()]
                }
        except Exception as e:
            return {"error": f"Error analyzing column '{column}': {str(e)}"}
    
    def aggregate_data(self, group_by: Union[str, List[str]], agg_column: str, 
                      agg_function: str = "sum") -> Dict[str, Any]:
        """
        Aggregate data by one or more columns.
        
        Args:
            group_by: Column(s) to group by
            agg_column: Column to aggregate
            agg_function: Aggregation function (sum, mean, count, min, max, std)
        """
        if self.df.empty:
            return {"error": "No data available for aggregation"}
            
        if isinstance(group_by, str):
            group_by = [group_by]
            
        # Check if columns exist
        missing_cols = [col for col in group_by + [agg_column] if col not in self.df.columns]
        if missing_cols:
            return {"error": f"Columns not found: {missing_cols}"}
            
        try:
            agg_functions = {
                "sum": "sum",
                "mean": "mean", 
                "average": "mean",
                "count": "count",
                "min": "min",
                "max": "max",
                "std": "std",
                "median": "median"
            }
            
            if agg_function not in agg_functions:
                return {"error": f"Unsupported aggregation function: {agg_function}"}
                
            grouped = self.df.groupby(group_by)[agg_column].agg(agg_functions[agg_function])
            
            # Convert to list of dictionaries for easy consumption
            if isinstance(grouped.index, pd.MultiIndex):
                results = []
                for idx, value in grouped.items():
                    result = dict(zip(group_by, idx))
                    result[f"{agg_column}_{agg_function}"] = value
                    results.append(result)
            else:
                results = [
                    {group_by[0]: idx, f"{agg_column}_{agg_function}": value}
                    for idx, value in grouped.items()
                ]
            
            return {
                "group_by": group_by,
                "agg_column": agg_column,
                "agg_function": agg_function,
                "results": results,
                "total_groups": len(results)
            }
        except Exception as e:
            return {"error": f"Error in aggregation: {str(e)}"}
    
    def get_statistical_summary(self, columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get statistical summary for numeric columns."""
        if self.df.empty:
            return {"error": "No data available for statistical analysis"}
            
        try:
            numeric_df = self.df.select_dtypes(include=[np.number])
            if columns:
                numeric_df = numeric_df[columns] if all(col in numeric_df.columns for col in columns) else numeric_df
                
            if numeric_df.empty:
                return {"error": "No numeric columns found for statistical analysis"}
                
            stats = numeric_df.describe()
            
            return {
                "columns_analyzed": list(numeric_df.columns),
                "statistics": {
                    col: {
                        "count": stats.loc["count", col],
                        "mean": stats.loc["mean", col],
                        "std": stats.loc["std", col],
                        "min": stats.loc["min", col],
                        "25%": stats.loc["25%", col],
                        "50%": stats.loc["50%", col],
                        "75%": stats.loc["75%", col],
                        "max": stats.loc["max", col]
                    }
                    for col in numeric_df.columns
                }
            }
        except Exception as e:
            return {"error": f"Error in statistical analysis: {str(e)}"}
    
    def detect_trends(self, column: str, time_column: Optional[str] = None, 
                     window_size: int = 5) -> Dict[str, Any]:
        """
        Detect trends in a numeric column, optionally over time.
        
        Args:
            column: Column to analyze for trends
            time_column: Optional time column for temporal analysis
            window_size: Window size for moving average calculation
        """
        if self.df.empty or column not in self.df.columns:
            return {"error": f"Column '{column}' not found or no data available"}
            
        try:
            if not pd.api.types.is_numeric_dtype(self.df[column]):
                return {"error": f"Column '{column}' is not numeric"}
                
            series = self.df[column].dropna()
            if len(series) < 2:
                return {"error": "Insufficient data for trend analysis"}
                
            # Basic trend analysis
            correlation_with_index = series.corr(pd.Series(range(len(series))))
            
            # Moving average
            moving_avg = series.rolling(window=min(window_size, len(series))).mean()
            
            # Detect trend direction
            if correlation_with_index > 0.1:
                trend_direction = "increasing"
            elif correlation_with_index < -0.1:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"
                
            result = {
                "column": column,
                "trend_direction": trend_direction,
                "correlation_coefficient": correlation_with_index,
                "data_points": len(series),
                "min_value": series.min(),
                "max_value": series.max(),
                "mean_value": series.mean(),
                "std_deviation": series.std(),
                "moving_average": moving_avg.tolist()[-10:] if len(moving_avg) > 0 else []
            }
            
            # Time-based analysis if time column provided
            if time_column and time_column in self.df.columns:
                try:
                    time_series = pd.to_datetime(self.df[time_column])
                    df_time = pd.DataFrame({
                        'time': time_series,
                        'value': self.df[column]
                    }).dropna().sort_values('time')
                    
                    if len(df_time) > 1:
                        # Calculate time-based statistics
                        time_span = (df_time['time'].max() - df_time['time'].min()).days
                        result.update({
                            "time_column": time_column,
                            "time_span_days": time_span,
                            "start_date": df_time['time'].min().isoformat(),
                            "end_date": df_time['time'].max().isoformat(),
                            "temporal_trend": "increasing" if df_time['value'].iloc[-1] > df_time['value'].iloc[0] else "decreasing"
                        })
                except Exception as e:
                    result["time_analysis_error"] = f"Error in time analysis: {str(e)}"
                    
            return result
            
        except Exception as e:
            return {"error": f"Error in trend analysis: {str(e)}"}
    
    def find_correlations(self, columns: Optional[List[str]] = None, 
                         min_correlation: float = 0.3) -> Dict[str, Any]:
        """Find correlations between numeric columns."""
        if self.df.empty:
            return {"error": "No data available for correlation analysis"}
            
        try:
            numeric_df = self.df.select_dtypes(include=[np.number])
            if columns:
                numeric_df = numeric_df[columns] if all(col in numeric_df.columns for col in columns) else numeric_df
                
            if numeric_df.shape[1] < 2:
                return {"error": "Need at least 2 numeric columns for correlation analysis"}
                
            corr_matrix = numeric_df.corr()
            
            # Find significant correlations
            significant_correlations = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i + 1, len(corr_matrix.columns)):
                    col1, col2 = corr_matrix.columns[i], corr_matrix.columns[j]
                    corr_value = corr_matrix.iloc[i, j]
                    
                    if abs(corr_value) >= min_correlation:
                        significant_correlations.append({
                            "column1": col1,
                            "column2": col2,
                            "correlation": corr_value,
                            "strength": "strong" if abs(corr_value) >= 0.7 else "moderate"
                        })
            
            return {
                "columns_analyzed": list(numeric_df.columns),
                "correlation_matrix": corr_matrix.to_dict(),
                "significant_correlations": significant_correlations,
                "min_correlation_threshold": min_correlation
            }
            
        except Exception as e:
            return {"error": f"Error in correlation analysis: {str(e)}"}
    
    def identify_outliers(self, column: str, method: str = "iqr") -> Dict[str, Any]:
        """
        Identify outliers in a numeric column.
        
        Args:
            column: Column to analyze
            method: Method to use ('iqr', 'zscore', 'modified_zscore')
        """
        if self.df.empty or column not in self.df.columns:
            return {"error": f"Column '{column}' not found or no data available"}
            
        if not pd.api.types.is_numeric_dtype(self.df[column]):
            return {"error": f"Column '{column}' is not numeric"}
            
        try:
            series = self.df[column].dropna()
            outliers = []
            
            if method == "iqr":
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outlier_mask = (series < lower_bound) | (series > upper_bound)
                outliers = series[outlier_mask].tolist()
                
            elif method == "zscore":
                z_scores = np.abs((series - series.mean()) / series.std())
                outlier_mask = z_scores > 3
                outliers = series[outlier_mask].tolist()
                
            elif method == "modified_zscore":
                median = series.median()
                mad = np.median(np.abs(series - median))
                modified_z_scores = 0.6745 * (series - median) / mad
                outlier_mask = np.abs(modified_z_scores) > 3.5
                outliers = series[outlier_mask].tolist()
                
            return {
                "column": column,
                "method": method,
                "outliers": outliers,
                "outlier_count": len(outliers),
                "outlier_percentage": (len(outliers) / len(series)) * 100,
                "total_values": len(series)
            }
            
        except Exception as e:
            return {"error": f"Error in outlier detection: {str(e)}"}
    
    def get_data_sample(self, n: int = 10, method: str = "head") -> Dict[str, Any]:
        """
        Get a sample of the data for inspection.
        
        Args:
            n: Number of rows to return
            method: Sampling method ('head', 'tail', 'random')
        """
        if self.df.empty:
            return {"error": "No data available"}
            
        try:
            if method == "head":
                sample = self.df.head(n)
            elif method == "tail":
                sample = self.df.tail(n)
            elif method == "random":
                sample = self.df.sample(n=min(n, len(self.df)))
            else:
                return {"error": f"Unsupported sampling method: {method}"}
                
            return {
                "method": method,
                "sample_size": len(sample),
                "total_rows": len(self.df),
                "data": sample.to_dict('records')
            }
            
        except Exception as e:
            return {"error": f"Error in data sampling: {str(e)}"}
    
    def analyze_categorical_columns(self, columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze categorical columns for patterns and distributions."""
        if self.df.empty:
            return {"error": "No data available"}
            
        try:
            categorical_df = self.df.select_dtypes(include=['object', 'category'])
            if columns:
                categorical_df = categorical_df[columns] if all(col in categorical_df.columns for col in columns) else categorical_df
                
            if categorical_df.empty:
                return {"error": "No categorical columns found"}
                
            analysis = {}
            for col in categorical_df.columns:
                series = categorical_df[col].dropna()
                unique_values = series.nunique()
                
                analysis[col] = {
                    "unique_values": unique_values,
                    "total_values": len(series),
                    "uniqueness_ratio": unique_values / len(series) if len(series) > 0 else 0,
                    "most_common": series.value_counts().head(5).to_dict(),
                    "null_count": categorical_df[col].isnull().sum()
                }
                
            return {
                "columns_analyzed": list(categorical_df.columns),
                "analysis": analysis
            }
            
        except Exception as e:
            return {"error": f"Error in categorical analysis: {str(e)}"} 