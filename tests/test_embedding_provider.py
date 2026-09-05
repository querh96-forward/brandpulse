from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.providers.embedding import OpenAICompatibleEmbeddingProvider


def build_provider() -> OpenAICompatibleEmbeddingProvider:
    return OpenAICompatibleEmbeddingProvider(
        api_key="test-key",
        model="text-embedding-v4",
        dimensions=3,
        base_url="https://example.com/compatible-mode/v1",
        timeout_seconds=15.0,
    )


async def test_embedding_provider_preserves_input_order_and_dimensions() -> None:
    with patch("app.providers.embedding.AsyncOpenAI") as client_class:
        client = client_class.return_value
        client.embeddings.create = AsyncMock(
            return_value=SimpleNamespace(
                data=[
                    SimpleNamespace(index=1, embedding=[0.4, 0.5, 0.6]),
                    SimpleNamespace(index=0, embedding=[0.1, 0.2, 0.3]),
                ]
            )
        )
        provider = build_provider()

        vectors = await provider.embed_texts(["first", "second"])

    assert vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    client.embeddings.create.assert_awaited_once_with(
        model="text-embedding-v4",
        input=["first", "second"],
        dimensions=3,
        encoding_format="float",
    )


async def test_embedding_provider_rejects_unexpected_dimensions() -> None:
    with patch("app.providers.embedding.AsyncOpenAI") as client_class:
        client = client_class.return_value
        client.embeddings.create = AsyncMock(
            return_value=SimpleNamespace(data=[SimpleNamespace(index=0, embedding=[0.1, 0.2])])
        )
        provider = build_provider()

        with pytest.raises(ValueError, match="expected 3, received 2"):
            await provider.embed_text("test")


@pytest.mark.parametrize("texts", [[], [""], ["   "]])
async def test_embedding_provider_rejects_missing_text(texts: list[str]) -> None:
    provider = build_provider()

    with pytest.raises(ValueError):
        await provider.embed_texts(texts)
