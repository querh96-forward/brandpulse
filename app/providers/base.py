from collections.abc import Sequence
from typing import Protocol

from app.schemas.analysis import AnalysisOutput
from app.schemas.knowledge import EvidenceAssessment


class AnalysisProvider(Protocol):
    model_name: str

    async def analyze(self, prompt: str) -> AnalysisOutput: ...


class EmbeddingProvider(Protocol):
    model_name: str
    dimensions: int

    async def embed_text(self, text: str) -> list[float]: ...

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]: ...


class EvidenceProvider(Protocol):
    model_name: str

    async def assess(
        self,
        query: str,
        evidence: Sequence[str],
    ) -> EvidenceAssessment: ...
