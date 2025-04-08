from typing import Optional

from doorbeen.core.types.ts_model import TSModel


class DBValidationResult(TSModel):
    can_connect: bool = False
    non_null_tables: bool = False
    error: Optional[str] = None
