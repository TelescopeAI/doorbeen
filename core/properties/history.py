from typing import Optional, List

from core.commons.frequency import Frequency
from core.properties.values import PropertyValue
from core.types.ts_model import TSModel


class PropertyHistory(TSModel):
    frequency: Optional[Frequency] = None
    values: Optional[List[PropertyValue]] = None

    class Config:
        use_enum_values = True
