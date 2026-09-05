from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.providers.evidence import OpenAICompatibleEvidenceProvider
from app.schemas.knowledge import EvidenceAssessment


def build_provider() -> OpenAICompatibleEvidenceProvider:
    return OpenAICompatibleEvidenceProvider(
        api_key="test-key",
        model="test-model",
        base_url="https://example.com/v1",
    )


async def test_evidence_provider_returns_structured_assessment() -> None:
    assessment = EvidenceAssessment(
        sufficient=True,
        supporting_ranks=[1],
        reason="第一条证据明确包含用户的首次操作。",
    )

    with patch("app.providers.evidence.AsyncOpenAI") as client_class:
        client = client_class.return_value
        client.chat.completions.parse = AsyncMock(
            return_value=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(parsed=assessment))]
            )
        )
        provider = build_provider()

        result = await provider.assess(
            query="SEAL-07 后首先应该怎么做？",
            evidence=["用户必须立即停止下潜任务并回收设备。"],
        )

    assert result == assessment
    request = client.chat.completions.parse.await_args.kwargs
    assert request["response_format"] is EvidenceAssessment
    assert "SEAL-07 后首先应该怎么做" in request["messages"][1]["content"]
    assert 'evidence rank="1"' in request["messages"][1]["content"]


async def test_evidence_provider_rejects_out_of_range_supporting_rank() -> None:
    assessment = EvidenceAssessment(
        sufficient=True,
        supporting_ranks=[2],
        reason="错误地引用了不存在的第二条证据。",
    )

    with patch("app.providers.evidence.AsyncOpenAI") as client_class:
        client = client_class.return_value
        client.chat.completions.parse = AsyncMock(
            return_value=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(parsed=assessment))]
            )
        )
        provider = build_provider()

        with pytest.raises(ValueError, match="out-of-range"):
            await provider.assess(query="测试问题", evidence=["唯一的证据"])


@pytest.mark.parametrize(
    ("query", "evidence"),
    [
        ("", ["证据"]),
        ("问题", []),
        ("问题", ["  "]),
    ],
)
async def test_evidence_provider_rejects_blank_input(
    query: str,
    evidence: list[str],
) -> None:
    provider = build_provider()

    with pytest.raises(ValueError):
        await provider.assess(query=query, evidence=evidence)
