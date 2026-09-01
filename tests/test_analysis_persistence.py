from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import AnalysisResult
from app.models.article import Article
from app.schemas.analysis import AnalysisOutput
from app.services.analysis import analyze_and_save_article
from app.services.article import calculate_content_hash


class FakeAnalysisProvider:
    model_name = "fake-analysis-model"

    def __init__(self, result: AnalysisOutput) -> None:
        self.result = result

    async def analyze(self, prompt: str) -> AnalysisOutput:
        return self.result


async def test_analyze_and_save_article_updates_existing_result(
    db_session: AsyncSession,
) -> None:
    content = "用户反馈水下设备出现进水问题。"

    article = Article(
        source_type="manual",
        source_name="Test Source",
        title="水下设备故障",
        content=content,
        content_hash=calculate_content_hash(content),
    )

    db_session.add(article)
    await db_session.flush()

    provider = FakeAnalysisProvider(
        AnalysisOutput(
            sentiment="negative",
            sentiment_score=-0.8,
            risk_level="high",
            risk_score=0.85,
            risk_type="product_safety",
            summary="设备可能存在密封问题。",
            suggestion="立即核查相关产品批次。",
        )
    )

    first_analysis = await analyze_and_save_article(
        session=db_session,
        provider=provider,
        article=article,
    )
    first_analysis_id = first_analysis.id

    provider.result = AnalysisOutput(
        sentiment="neutral",
        sentiment_score=0,
        risk_level="low",
        risk_score=0.2,
        risk_type="general_feedback",
        summary="重新分析后风险较低。",
        suggestion="继续观察后续反馈。",
    )

    second_analysis = await analyze_and_save_article(
        session=db_session,
        provider=provider,
        article=article,
    )

    assert second_analysis.id == first_analysis_id
    assert second_analysis.sentiment == "neutral"
    assert second_analysis.risk_level == "low"
    assert second_analysis.risk_score == 0.2

    result = await db_session.scalars(
        select(AnalysisResult).where(
            AnalysisResult.article_id == article.id,
        )
    )
    saved_analyses = list(result.all())

    assert len(saved_analyses) == 1
