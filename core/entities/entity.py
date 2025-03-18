from datetime import datetime
from typing import Optional, List

from core.properties.property import Property
from core.types.ts_model import TSModel


class Entity(TSModel):
    name: str
    type: str
    properties: Optional[List[Property]] = None
    notes: Optional[List[str]] = None
    insights: Optional[List[str]] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    
