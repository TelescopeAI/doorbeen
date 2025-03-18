from typing import List, Optional

from core.types.ts_model import TSModel
from sqlalchemy.engine.row import Row


class ExecutionResults(TSModel):
    query: str
    result: Optional[List] = None
    error: Optional[str] = None
    is_sql_error: Optional[bool] = None

    model_config = {
        "json_encoders": {
            Row: lambda v: v._asdict(),
        }
    }

    def get_results_json(self):
        results = []
        if self.result is not None:
            for row in self.result:
                results.append(row._asdict())
        return results


class CorrectedSQLQuery(TSModel):
    raw_query: str
    corrected_query: str
    explanation: Optional[str] = None
    modification_plan: Optional[str] = None

