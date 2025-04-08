from typing import Any

from doorbeen.core.types.ts_model import TSModel


class NodeExecutionOutput(TSModel):
    name: str
    value: Any
