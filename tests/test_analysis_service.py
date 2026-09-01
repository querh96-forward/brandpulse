from app.schemas.analysis import AnalysisOutput
from app.services.analysis import analyze_article_text


class FakeAnalysisProvider:
    model_name = "fake-analysis-model"

    def __init__(self) -> None:
        self.received_prompt = ""

    async def analyze(self, prompt: str) -> AnalysisOutput:
        self.received_prompt = prompt

        return AnalysisOutput(
            sentiment="negative",
            sentiment_score=-0.7,
            risk_level="high",
            risk_score=0.82,
            risk_type="product_safety",
            summary="文章反映水下设备存在密封故障。",
            suggestion="核查产品批次并准备风险回应。",
        )


async def test_analyze_article_text_uses_provider() -> None:
    provider = FakeAnalysisProvider()

    result = await analyze_article_text(
        provider=provider,
        title="水下设备出现故障",
        content="多名用户反馈设备在深水环境中出现进水问题。",
    )

    assert "水下设备出现故障" in provider.received_prompt
    assert "深水环境中出现进水问题" in provider.received_prompt

    assert result.sentiment.value == "negative"
    assert result.risk_level.value == "high"
    assert result.risk_score == 0.82
