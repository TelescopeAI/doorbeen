from typing import Optional, List

from doorbeen.core.types.ts_model import TSModel


class FinalPresentation(TSModel):
    ready_to_present: bool
    interpretation_correct: bool
    message: str
    results: Optional[List[dict]] = None
