import uuid
from unittest.mock import AsyncMock, patch

from app.models.article import Article
from app.schemas.knowledge import EvidenceAssessment
from app.services.analysis import prepare_article_knowledge
from app.services.knowledge import AssessedKnowledge, KnowledgeSearchResult


class FakeEmbeddingProvider:
    model_name = "fake-embedding-model"
    dimensions = 1024

    async def embed_text(self, text: str) -> list[float]:
        return [0.0] * self.dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.dimensions for _ in texts]


class FakeEvidenceProvider:
    model_name = "fake-evidence-model"

    async def assess(self, query: str, evidence: list[str]) -> EvidenceAssessment:
        return EvidenceAssessment(
            sufficient=True,
            supporting_ranks=[1],
            reason="第一条证据支持本次分析。",
        )


def build_article() -> Article:
    return Article(
        brand_id=uuid.uuid4(),
        source_type="manual",
        source_name="RAG Test",
        title="BC-D200 出现 SEAL-07",
        content="用户反馈设备在下潜时出现密封异常。",
        content_hash="a" * 64,
    )


async def test_prepare_article_knowledge_keeps_only_supporting_evidence() -> None:
    first_result = KnowledgeSearchResult(
        chunk_id=uuid.uuid4(),
        source_name="emergency.md",
        section_title="SEAL-07 用户首次操作",
        content="必须立即停止下潜任务并回收设备。",
        similarity=0.81,
    )
    second_result = KnowledgeSearchResult(
        chunk_id=uuid.uuid4(),
        source_name="policy.md",
        section_title="其他规则",
        content="与本次分析无关的候选文本。",
        similarity=0.70,
    )
    assessed = AssessedKnowledge(
        results=[first_result, second_result],
        assessment=EvidenceAssessment(
            sufficient=True,
            supporting_ranks=[1],
            reason="只有第一条证据提供明确依据。",
        ),
    )

    with patch(
        "app.services.analysis.retrieve_and_assess_knowledge",
        new=AsyncMock(return_value=assessed),
    ):
        knowledge = await prepare_article_knowledge(
            session=AsyncMock(),
            article=build_article(),
            embedding_provider=FakeEmbeddingProvider(),
            evidence_provider=FakeEvidenceProvider(),
        )

    assert knowledge.used is True
    assert knowledge.context_blocks == [first_result.content]
    assert len(knowledge.citations) == 1
    assert knowledge.citations[0].chunk_id == first_result.chunk_id
    assert knowledge.citations[0].rank == 1
    assert knowledge.retrieval_model_name == "fake-embedding-model"
    assert knowledge.evidence_model_name == "fake-evidence-model"


async def test_prepare_article_knowledge_rejects_insufficient_evidence() -> None:
    assessed = AssessedKnowledge(
        results=[
            KnowledgeSearchResult(
                chunk_id=uuid.uuid4(),
                source_name="policy.md",
                section_title="品牌信息",
                content="只包含无关的品牌信息。",
                similarity=0.64,
            )
        ],
        assessment=EvidenceAssessment(
            sufficient=False,
            supporting_ranks=[],
            reason="候选证据没有提供事件所需的内部政策。",
        ),
    )

    with patch(
        "app.services.analysis.retrieve_and_assess_knowledge",
        new=AsyncMock(return_value=assessed),
    ):
        knowledge = await prepare_article_knowledge(
            session=AsyncMock(),
            article=build_article(),
            embedding_provider=FakeEmbeddingProvider(),
            evidence_provider=FakeEvidenceProvider(),
        )

    assert knowledge.used is False
    assert knowledge.context_blocks == []
    assert knowledge.citations == []
    assert knowledge.reason == "候选证据没有提供事件所需的内部政策。"
