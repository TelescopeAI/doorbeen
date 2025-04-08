from typing import Dict, Any
from doorbeen.core.types.ts_model import TSModel


class QueryResult(TSModel):
    data: Dict[str, Any]
