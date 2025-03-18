from typing import Optional, List

from core.types.ts_model import TSModel


class QueryEvaluationReport(TSModel):
    query_effective: bool = False
    met_reasons: Optional[list[str]] = None
    unmet_reasons: Optional[list[str]] = None


class QueryAnalysisReport(TSModel):
    query: QueryEvaluationReport | None = None
    all_objectives_met: bool = False
    some_objectives_met: bool = False
    results_trimmed: Optional[bool] = False
    insights: List[str | dict] = []
    limitations: List[str | dict] = []
    unmet_objectives: List[str] = []
    next_step: str
