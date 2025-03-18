from datetime import datetime
from typing import Optional, Union
from uuid import UUID

from core.properties.analysis.aggregates import PropertyAggregates
from core.properties.history import PropertyHistory
from core.types.ts_model import TSModel


class PropertySQL(TSModel):
    statement: str
    params: Optional[dict] = None


class ColumnMap(TSModel):
    key_column: str
    value_column: str
    timestamp_column: Optional[str] = None


class Property(TSModel):
    name: str
    entity_label: Union[str, int, UUID]
    column_map: ColumnMap
    sql: PropertySQL
    value: Optional[Union[int, str]] = None
    history: Optional[PropertyHistory] = None
    aggregates: Optional[PropertyAggregates] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()



