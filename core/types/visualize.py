from enum import Enum
from typing import Optional, List

from pydantic import model_validator

from core.types.ts_model import TSModel


class VisualizationChartType(Enum):
    LINE = "line"
    BAR = "bar"
    PIE = "pie"


class VizDataModel(TSModel):
    name: str
    query: str


class SeriesVisualization(VizDataModel):
    pass


class CategoryVisualization(VizDataModel):
    pass


class BarChartXAxisConfig(TSModel):
    categories: Optional[list[str]] = None


class BarChartConfig(TSModel):
    xaxis: BarChartXAxisConfig


class QueryVisualizationPlan(TSModel):
    needs_visualization: bool = False
    chart_type: Optional[VisualizationChartType] = None
    series: Optional[List[SeriesVisualization]] = None
    categories: Optional[CategoryVisualization] = None

    @model_validator(mode='before')
    @classmethod
    def validate_dimensions(cls, values):
        series = values.get('series')
        categories = values.get('categories')
        if isinstance(series, list) and len(series) == 0:
            values['series'] = None
        if isinstance(categories, dict) and len(categories.keys()) == 0:
            values['categories'] = None
        return values


class VizWithData(TSModel):
    series: Optional[List[SeriesVisualization]] = None
    categories: Optional[CategoryVisualization] = None
