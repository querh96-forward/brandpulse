from unittest.mock import patch

from app.providers.openai_compatible import OpenAICompatibleAnalysisProvider


def test_provider_configures_timeout_and_retries() -> None:
    with patch("app.providers.openai_compatible.AsyncOpenAI") as client_class:
        provider = OpenAICompatibleAnalysisProvider(
            api_key="test-key",
            model="test-model",
            base_url="https://example.com/v1",
            timeout_seconds=90.0,
            max_retries=3,
        )

    assert provider.model_name == "test-model"
    client_class.assert_called_once_with(
        api_key="test-key",
        base_url="https://example.com/v1",
        timeout=90.0,
        max_retries=3,
    )
