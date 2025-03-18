from datetime import datetime
from typing import Optional, Union

from core.types.ts_model import TSModel


class PropertyValue(TSModel):
    timestamp: Optional[datetime] = None
    value: Union[int, str]

