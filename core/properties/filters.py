from enum import Enum
from typing import List, Union, Optional

from pydantic import model_validator
from pydantic import Field

from core.types.ts_model import TSModel


class Comparator(Enum):
    EQ = 'eq'
    NE = 'ne'
    GT = 'gt'
    LT = 'lt'
    GTE = 'gte'
    LTE = 'lte'
    IN = 'in'
    NOT_IN = 'not_in'
    CONTAINS = 'contains'
    NOT_CONTAINS = 'not_contains'
    STARTS_WITH = 'starts_with'
    ENDS_WITH = 'ends_with'


class LogicalOperator(Enum):
    AND = 'and'
    OR = 'or'
    NOT = 'not'


class ColumnThreshold(TSModel):
    column_name: str = Field(...)
    comparator: Comparator = Field(...)
    value: Union[int, str, List[Union[int, str]]] = Field(...)

    @model_validator(mode='after')
    def validate_value(cls, values):
        comparator = values.get('comparator')
        value = values.get('value')
        if comparator in [Comparator.IN, Comparator.NOT_IN] and not isinstance(value, list):
            raise ValueError(f"{comparator} requires a list of values.")
        elif comparator not in [Comparator.IN, Comparator.NOT_IN] and isinstance(value, list):
            raise ValueError(f"{comparator} cannot be used with a list of values.")
        return values


class FilterCondition(TSModel):
    logical_operator: LogicalOperator = Field(default=None)
    condition: Union['Filter', ColumnThreshold]  # This supports nested structures

    @model_validator(mode='after')
    def validate_logical_operator(cls, values):
        condition = values.get('condition')
        logical_operator = values.get('logical_operator')
        if isinstance(condition, Filter) and not logical_operator:
            raise ValueError("logical_operator is required for nested Filter conditions.")
        return values


class FilterUnit(TSModel):
    conditions: List[ColumnThreshold]
    logical_operator: Optional[LogicalOperator]


class Filter(TSModel):
    filter_units: List[FilterUnit]
    logical_operator: Optional[LogicalOperator]
