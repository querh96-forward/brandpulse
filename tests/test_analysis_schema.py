from pydantic import ValidationError
from pytest import raises

from app.models.analysis import RiskLevel, Sentiment
from app.schemas.analysis import AnalysisOutput


def test_analysis_output_accepts_valid_result() -> None:
    result = AnalysisOutput(
        sentiment="negative",
        sentiment_score=-0.8,
        risk_level="high",
        risk_score=0.85,
        risk_type="product_safety",
        summary="用户反馈水下设备出现密封故障。",
        suggestion="立即核查相关批次，并准备对外回应。",
    )

    assert result.sentiment == Sentiment.NEGATIVE
    assert result.risk_level == RiskLevel.HIGH
    assert result.risk_score == 0.85


def test_analysis_output_rejects_invalid_risk_score() -> None:
    with raises(ValidationError):
        AnalysisOutput(
            sentiment="negative",
            sentiment_score=-0.8,
            risk_level="high",
            risk_score=1.5,
            risk_type="product_safety",
            summary="风险分数超出了允许范围。",
            suggestion=None,
        )
