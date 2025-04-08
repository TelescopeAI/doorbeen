from enum import Enum

from pydantic import Field
from doorbeen.core.types.ts_model import TSModel


class FollowupCertaintyLevel(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    UNSURE = "unsure"


class FollowupAttempts(TSModel):
    answer: str
    is_related: bool
    certainty_level: FollowupCertaintyLevel = Field(default=FollowupCertaintyLevel.PARTIAL)
    modified_question: str
