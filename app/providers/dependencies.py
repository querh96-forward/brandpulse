from functools import lru_cache

from app.core.config import get_settings
from app.providers.base import AnalysisProvider, EmbeddingProvider, EvidenceProvider
from app.providers.embedding import OpenAICompatibleEmbeddingProvider
from app.providers.evidence import OpenAICompatibleEvidenceProvider
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


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()

    if not settings.embedding_api_key or not settings.embedding_base_url:
        raise RuntimeError("embedding provider is not configured")

    return OpenAICompatibleEmbeddingProvider(
        api_key=settings.embedding_api_key,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        base_url=settings.embedding_base_url,
        timeout_seconds=settings.embedding_timeout_seconds,
    )


@lru_cache
def get_evidence_provider() -> EvidenceProvider:
    settings = get_settings()

    if not settings.llm_api_key or not settings.llm_model:
        raise RuntimeError("evidence provider is not configured")

    return OpenAICompatibleEvidenceProvider(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url or None,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )


@lru_cache
def get_optional_embedding_provider() -> EmbeddingProvider | None:
    settings = get_settings()

    if not settings.embedding_api_key or not settings.embedding_base_url:
        return None

    return get_embedding_provider()


@lru_cache
def get_optional_evidence_provider() -> EvidenceProvider | None:
    settings = get_settings()

    if not settings.llm_api_key or not settings.llm_model:
        return None

    return get_evidence_provider()
