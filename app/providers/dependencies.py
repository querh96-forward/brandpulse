from functools import lru_cache

from app.core.config import get_settings
from app.providers.base import AnalysisProvider
from app.providers.openai_compatible import OpenAICompatibleAnalysisProvider
from app.providers.rule_based import RuleBasedAnalysisProvider


@lru_cache
def get_analysis_provider() -> AnalysisProvider:
    settings = get_settings()

    if settings.llm_api_key and settings.llm_model:
        return OpenAICompatibleAnalysisProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url or None,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    return RuleBasedAnalysisProvider()
