import uuid
from unittest.mock import AsyncMock, patch

from app.schemas.knowledge import EvidenceAssessment
from app.services.knowledge import (
    KnowledgeSearchResult,
    retrieve_and_assess_knowledge,
)


class FakeEmbeddingProvider:
    model_name = "fake-embedding-model"
    dimensions = 1024

    async def embed_text(self, text: str) -> list[float]:
        return [0.0] * self.dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.dimensions for _ in texts]


class FakeEvidenceProvider:
    model_name = "fake-evidence-model"

    def __init__(self, assessment: EvidenceAssessment) -> None:
        self.assessment = assessment
        self.received_query: str | None = None
        self.received_evidence: list[str] | None = None

    async def assess(self, query: str, evidence: list[str]) -> EvidenceAssessment:
        self.received_query = query
        self.received_evidence = evidence
        return self.assessment


async def test_retrieve_and_assess_passes_ranked_content_to_evidence_provider() -> None:
    results = [
        KnowledgeSearchResult(
            chunk_id=uuid.uuid4(),
            source_name="emergency.md",
            section_title="SEAL-07 用户首次操作",
            content="必须立即停止下潜任务并回收设备。",
            similarity=0.81,
        )
    ]
    evidence_provider = FakeEvidenceProvider(
        EvidenceAssessment(
            sufficient=True,
            supporting_ranks=[1],
            reason="第一条证据明确回答了问题。",
        )
    )

    with patch(
        "app.services.knowledge.search_knowledge",
        new=AsyncMock(return_value=results),
    ):
        assessed = await retrieve_and_assess_knowledge(
            session=AsyncMock(),
            embedding_provider=FakeEmbeddingProvider(),
            evidence_provider=evidence_provider,
            brand_id=uuid.uuid4(),
            query="SEAL-07 后首先应该怎么做？",
        )

    assert assessed.results == results
    assert assessed.assessment.sufficient is True
    assert evidence_provider.received_query == "SEAL-07 后首先应该怎么做？"
    assert evidence_provider.received_evidence == [results[0].content]


async def test_retrieve_and_assess_rejects_without_calling_model_when_no_results() -> None:
    evidence_provider = FakeEvidenceProvider(
        EvidenceAssessment(
            sufficient=True,
            supporting_ranks=[1],
            reason="This response must not be used.",
        )
    )

    with patch(
        "app.services.knowledge.search_knowledge",
        new=AsyncMock(return_value=[]),
    ):
        assessed = await retrieve_and_assess_knowledge(
            session=AsyncMock(),
            embedding_provider=FakeEmbeddingProvider(),
            evidence_provider=evidence_provider,
            brand_id=uuid.uuid4(),
            query="没有候选证据的问题",
        )

    assert assessed.results == []
    assert assessed.assessment.sufficient is False
    assert assessed.assessment.supporting_ranks == []
    assert evidence_provider.received_query is None
