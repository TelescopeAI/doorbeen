from typing import Optional, Any

from core.assistants.analysis.sql.query.errors import AttemptErrorDetails
from core.types.ts_model import TSModel


class QueryExecutionAttempt(TSModel):
    number: int
    success: bool = False
    error: Optional[AttemptErrorDetails] = None
    results: Optional[Any] = None
