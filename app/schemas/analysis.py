import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.analysis import RiskLevel, Sentiment
from app.models.analysis_job import AnalysisJobStatus


class AnalysisOutput(BaseModel):
    sentiment: Sentiment
    sentiment_score: float = Field(ge=-1, le=1)
    risk_level: RiskLevel
    risk_score: float = Field(ge=0, le=1)
    risk_type: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=2000)
    suggestion: str | None = Field(default=None, max_length=2000)


class AnalysisRead(AnalysisOutput):
    id: uuid.UUID
    article_id: uuid.UUID
    model_name: str
    prompt_version: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisJobRead(BaseModel):
    job_id: uuid.UUID
    article_id: uuid.UUID
    status: AnalysisJobStatus
    queue_length: int | None = None
    reused: bool = False


class AnalysisStatusRead(BaseModel):
    article_id: uuid.UUID
    status: Literal["pending", "completed"]
    result: AnalysisRead | None = None


class AnalysisJobStatusRead(BaseModel):
    job_id: uuid.UUID
    article_id: uuid.UUID
    status: AnalysisJobStatus
    attempts: int
    last_error: str | None
    created_at: datetime
    updated_at: datetime
