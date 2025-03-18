from typing import Optional

from core.types.ts_model import TSModel


class GlossaryTerm(TSModel):
    term: str
    meaning: str
    description: Optional[str] = None
    examples: Optional[list[str]] = None
    related_terms: Optional[list[str]] = None
    synonyms: Optional[list[str]] = None
    antonyms: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None


class Glossary(TSModel):
    terms: Optional[list[GlossaryTerm]] = []
