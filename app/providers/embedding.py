from collections.abc import Sequence

from openai import AsyncOpenAI


class OpenAICompatibleEmbeddingProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        dimensions: int,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.model_name = model
        self.dimensions = dimensions
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=1,
        )

    async def embed_text(self, text: str) -> list[float]:
        vectors = await self.embed_texts([text])
        return vectors[0]

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        normalized_texts = [text.strip() for text in texts]

        if not normalized_texts:
            raise ValueError("at least one text is required")

        if any(not text for text in normalized_texts):
            raise ValueError("embedding input must not be blank")

        response = await self._client.embeddings.create(
            model=self.model_name,
            input=normalized_texts,
            dimensions=self.dimensions,
            encoding_format="float",
        )

        ordered_items = sorted(response.data, key=lambda item: item.index)
        vectors = [list(item.embedding) for item in ordered_items]

        if len(vectors) != len(normalized_texts):
            raise ValueError("embedding provider returned an unexpected number of vectors")

        for vector in vectors:
            if len(vector) != self.dimensions:
                raise ValueError(
                    "embedding provider returned an unexpected vector dimension: "
                    f"expected {self.dimensions}, received {len(vector)}"
                )

        return vectors
