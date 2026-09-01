import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BrandCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("brand name cannot be empty")

        return normalized


class BrandRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
