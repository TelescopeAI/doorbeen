from core.types.ts_model import TSModel


class PropertyStats(TSModel):
    sum: float = 0
    avg: float = 0
    min: float = 0
    max: float = 0
    count: int = 0

