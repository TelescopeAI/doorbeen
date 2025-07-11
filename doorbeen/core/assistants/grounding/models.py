"""
Grounding models for analysis examples and context.
"""

from typing import List, Optional, Dict, Any
from pydantic import Field

from doorbeen.core.types.ts_model import TSModel


class AnalysisExample(TSModel):
    """Example of expected analysis output for grounding."""
    
    question: str = Field(description="The user question that was asked")
    instructions: str = Field(description="Specific instructions for how to handle this type of question")
    expected_output: str = Field(description="Example of the expected output format and content")
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing the example")
    priority: int = Field(default=1, description="Priority level for this example (higher = more important)")


class GroundingContext(TSModel):
    """Context containing examples and grounding information."""
    
    examples: List[AnalysisExample] = Field(default_factory=list, description="List of analysis examples")
    similar_examples: List[AnalysisExample] = Field(default_factory=list, description="Examples similar to current question")
    guidance_applied: bool = Field(default=False, description="Whether example guidance has been applied")
    similarity_threshold: float = Field(default=0.7, description="Threshold for considering examples similar")
    
    def add_example(self, example: AnalysisExample) -> None:
        """Add an example to the context."""
        self.examples.append(example)
    
    def get_examples_by_tag(self, tag: str) -> List[AnalysisExample]:
        """Get examples filtered by tag."""
        return [ex for ex in self.examples if tag in ex.tags]
    
    def get_high_priority_examples(self) -> List[AnalysisExample]:
        """Get high priority examples (priority >= 3)."""
        return [ex for ex in self.examples if ex.priority >= 3] 