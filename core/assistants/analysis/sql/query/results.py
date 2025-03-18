from typing import Dict, Any
from core.types.ts_model import TSModel


class QueryResult(TSModel):
    data: Dict[str, Any]
