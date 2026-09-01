import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import AnalysisResult
from app.models.article import Article
from app.models.brand import Brand
from app.services.article import calculate_content_hash
from app.services.report import (
    build_brand_risk_summary,
    build_brand_risk_trend,
    list_brand_high_risk_articles,
)


async def test_build_brand_risk_summary(
    db_session: AsyncSession,
) -> None:
    brand = Brand(
        name="Report Test Brand",
        description="用于测试品牌风险汇总",
    )

    db_session.add(brand)
    await db_session.flush()

    contents = [
        "第一篇品牌测试文章。",
        "第二篇品牌测试文章。",
        "第三篇尚未分析的文章。",
    ]

    articles = [
        Article(
            brand_id=brand.id,
            source_type="manual",
            source_name="Report Test",
            title=f"测试文章 {index}",
            content=content,
            content_hash=calculate_content_hash(content),
        )
        for index, content in enumerate(
            contents,
            start=1,
        )
    ]

    db_session.add_all(articles)
    await db_session.flush()

    high_risk_analysis = AnalysisResult(
        article_id=articles[0].id,
        sentiment="negative",
        sentiment_score=-0.8,
        risk_level="high",
        risk_score=0.9,
        risk_type="product_risk",
        summary="存在较高风险。",
        suggestion="建议立即处理。",
        model_name="test-model",
        prompt_version="v1",
    )

    low_risk_analysis = AnalysisResult(
        article_id=articles[1].id,
        sentiment="positive",
        sentiment_score=0.8,
        risk_level="low",
        risk_score=0.1,
        risk_type="general",
        summary="整体评价良好。",
        suggestion="继续保持。",
        model_name="test-model",
        prompt_version="v1",
    )

    db_session.add_all(
        [
            high_risk_analysis,
            low_risk_analysis,
        ]
    )
    await db_session.flush()

    summary = await build_brand_risk_summary(
        session=db_session,
        brand_id=brand.id,
    )

    assert summary.brand_id == brand.id
    assert summary.total_articles == 3
    assert summary.analyzed_articles == 2
    assert summary.high_risk_articles == 1
    assert summary.average_risk_score == pytest.approx(0.5)
    assert summary.positive_articles == 1
    assert summary.neutral_articles == 0
    assert summary.negative_articles == 1

    high_risk_articles = await list_brand_high_risk_articles(
        session=db_session,
        brand_id=brand.id,
    )

    assert len(high_risk_articles) == 1

    high_risk_article = high_risk_articles[0]

    assert high_risk_article.article_id == articles[0].id
    assert high_risk_article.title == "测试文章 1"
    assert high_risk_article.risk_level == "high"
    assert high_risk_article.risk_score == pytest.approx(0.9)
    assert high_risk_article.risk_type == "product_risk"

    trend = await build_brand_risk_trend(
        session=db_session,
        brand_id=brand.id,
    )

    assert len(trend) == 1

    trend_point = trend[0]

    assert trend_point.day == high_risk_analysis.updated_at.date()
    assert trend_point.analyzed_articles == 2
    assert trend_point.high_risk_articles == 1
    assert trend_point.average_risk_score == pytest.approx(0.5)
