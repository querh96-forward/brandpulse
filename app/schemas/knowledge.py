import uuid
from typing import Self

from pydantic import BaseModel, Field, model_validator


class EvidenceAssessment(BaseModel):
    sufficient: bool
    supporting_ranks: list[int] = Field(default_factory=list)
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_supporting_ranks(self) -> Self:
        if any(rank < 1 for rank in self.supporting_ranks):
            raise ValueError("supporting ranks must start at 1")

        if self.sufficient and not self.supporting_ranks:
            raise ValueError("sufficient evidence must include at least one supporting rank")

        if not self.sufficient and self.supporting_ranks:
            raise ValueError("insufficient evidence must not include supporting ranks")

        return self


class KnowledgeCitation(BaseModel):
    rank: int = Field(ge=1)
    chunk_id: uuid.UUID
    source_name: str = Field(min_length=1, max_length=255)
    section_title: str | None = Field(default=None, max_length=500)
    similarity: float = Field(ge=-1, le=1)
