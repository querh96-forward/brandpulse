import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.analysis import RiskLevel


class BrandRiskSummary(BaseModel):
    brand_id: uuid.UUID
    total_articles: int
    analyzed_articles: int
    high_risk_articles: int
    average_risk_score: float
    positive_articles: int
    neutral_articles: int
    negative_articles: int


class HighRiskArticleRead(BaseModel):
    article_id: uuid.UUID
    title: str
    source_name: str
    risk_level: RiskLevel
    risk_score: float
    risk_type: str
    summary: str
    published_at: datetime | None
    analyzed_at: datetime


class BrandRiskTrendPoint(BaseModel):
    day: date
    analyzed_articles: int
    high_risk_articles: int
    average_risk_score: float
