import uuid
from datetime import datetime

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import (
    AnalysisResult,
    RiskLevel,
    Sentiment,
)
from app.models.article import Article
from app.schemas.report import (
    BrandRiskSummary,
    BrandRiskTrendPoint,
    HighRiskArticleRead,
)


async def build_brand_risk_summary(
    session: AsyncSession,
    brand_id: uuid.UUID,
) -> BrandRiskSummary:
    statement = (
        select(
            func.count(Article.id).label("total_articles"),
            func.count(AnalysisResult.id).label(
                "analyzed_articles",
            ),
            func.count(AnalysisResult.id)
            .filter(
                AnalysisResult.risk_level.in_(
                    [
                        RiskLevel.HIGH.value,
                        RiskLevel.CRITICAL.value,
                    ]
                )
            )
            .label("high_risk_articles"),
            func.coalesce(
                func.avg(AnalysisResult.risk_score),
                0.0,
            ).label("average_risk_score"),
            func.count(AnalysisResult.id)
            .filter(AnalysisResult.sentiment == Sentiment.POSITIVE.value)
            .label("positive_articles"),
            func.count(AnalysisResult.id)
            .filter(AnalysisResult.sentiment == Sentiment.NEUTRAL.value)
            .label("neutral_articles"),
            func.count(AnalysisResult.id)
            .filter(AnalysisResult.sentiment == Sentiment.NEGATIVE.value)
            .label("negative_articles"),
        )
        .select_from(Article)
        .outerjoin(
            AnalysisResult,
            AnalysisResult.article_id == Article.id,
        )
        .where(Article.brand_id == brand_id)
    )

    row = (await session.execute(statement)).one()

    return BrandRiskSummary(
        brand_id=brand_id,
        total_articles=int(row.total_articles),
        analyzed_articles=int(row.analyzed_articles),
        high_risk_articles=int(row.high_risk_articles),
        average_risk_score=round(
            float(row.average_risk_score),
            4,
        ),
        positive_articles=int(row.positive_articles),
        neutral_articles=int(row.neutral_articles),
        negative_articles=int(row.negative_articles),
    )


async def list_brand_high_risk_articles(
    session: AsyncSession,
    brand_id: uuid.UUID,
    offset: int = 0,
    limit: int = 20,
) -> list[HighRiskArticleRead]:
    statement = (
        select(
            Article.id.label("article_id"),
            Article.title,
            Article.source_name,
            Article.published_at,
            AnalysisResult.risk_level,
            AnalysisResult.risk_score,
            AnalysisResult.risk_type,
            AnalysisResult.summary,
            AnalysisResult.updated_at.label("analyzed_at"),
        )
        .select_from(Article)
        .join(
            AnalysisResult,
            AnalysisResult.article_id == Article.id,
        )
        .where(
            Article.brand_id == brand_id,
            AnalysisResult.risk_level.in_(
                [
                    RiskLevel.HIGH.value,
                    RiskLevel.CRITICAL.value,
                ]
            ),
        )
        .order_by(
            AnalysisResult.risk_score.desc(),
            AnalysisResult.updated_at.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    rows = (await session.execute(statement)).all()

    return [
        HighRiskArticleRead(
            article_id=row.article_id,
            title=row.title,
            source_name=row.source_name,
            risk_level=row.risk_level,
            risk_score=float(row.risk_score),
            risk_type=row.risk_type,
            summary=row.summary,
            published_at=row.published_at,
            analyzed_at=row.analyzed_at,
        )
        for row in rows
    ]


async def build_brand_risk_trend(
    session: AsyncSession,
    brand_id: uuid.UUID,
    since: datetime | None = None,
) -> list[BrandRiskTrendPoint]:
    analysis_day = cast(
        AnalysisResult.updated_at,
        Date,
    ).label("day")

    statement = (
        select(
            analysis_day,
            func.count(AnalysisResult.id).label(
                "analyzed_articles",
            ),
            func.count(AnalysisResult.id)
            .filter(
                AnalysisResult.risk_level.in_(
                    [
                        RiskLevel.HIGH.value,
                        RiskLevel.CRITICAL.value,
                    ]
                )
            )
            .label("high_risk_articles"),
            func.coalesce(
                func.avg(AnalysisResult.risk_score),
                0.0,
            ).label("average_risk_score"),
        )
        .select_from(Article)
        .join(
            AnalysisResult,
            AnalysisResult.article_id == Article.id,
        )
        .where(Article.brand_id == brand_id)
    )

    if since is not None:
        statement = statement.where(
            AnalysisResult.updated_at >= since,
        )

    statement = statement.group_by(
        analysis_day,
    ).order_by(
        analysis_day,
    )

    rows = (await session.execute(statement)).all()

    return [
        BrandRiskTrendPoint(
            day=row.day,
            analyzed_articles=int(row.analyzed_articles),
            high_risk_articles=int(row.high_risk_articles),
            average_risk_score=round(
                float(row.average_risk_score),
                4,
            ),
        )
        for row in rows
    ]
