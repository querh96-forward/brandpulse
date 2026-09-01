from app.schemas.analysis import AnalysisOutput


class RuleBasedAnalysisProvider:
    model_name = "rule-based-v1"

    async def analyze(self, prompt: str) -> AnalysisOutput:
        risk_keywords = (
            "故障",
            "进水",
            "事故",
            "召回",
            "爆炸",
            "投诉",
        )

        has_risk = any(keyword in prompt for keyword in risk_keywords)

        if has_risk:
            return AnalysisOutput(
                sentiment="negative",
                sentiment_score=-0.8,
                risk_level="high",
                risk_score=0.85,
                risk_type="product_risk",
                summary="文章中检测到潜在的产品或舆情风险。",
                suggestion="建议核查相关情况并准备风险回应。",
            )

        return AnalysisOutput(
            sentiment="neutral",
            sentiment_score=0,
            risk_level="low",
            risk_score=0.1,
            risk_type="general",
            summary="文章中暂未检测到明显风险。",
            suggestion="建议继续监测后续舆情变化。",
        )
