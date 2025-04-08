from doorbeen.core.types.ts_model import TSModel


class AttemptErrorDetails(TSModel):
    query: str
    logic: str
    message: str
