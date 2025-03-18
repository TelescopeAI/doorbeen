from typing import Optional

from core.types.ts_model import TSModel


class EnrichAssumptions(TSModel):
    completeness: Optional[list[str]] = None
    relevance: Optional[list[str]] = None
    specificity: Optional[list[str]] = None


class EnrichedOutput(TSModel):
    improved_input: Optional[str] = None
    assumptions: Optional[EnrichAssumptions] = None
    variations: Optional[list[str]] = None