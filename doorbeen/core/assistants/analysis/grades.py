from doorbeen.core.types.ts_model import TSModel


class CompletenessScore(TSModel):
    score: int
    reason: str


class RelevanceScore(TSModel):
    score: int
    reason: str


class SpecificityScore(TSModel):
    score: int
    reason: str


class OverallGrade(TSModel):
    score: int
    reason: str


class InputGradeResult(TSModel):
    completeness: CompletenessScore
    relevance: RelevanceScore
    specificity: SpecificityScore
    overall: OverallGrade
    should_enrich: bool
