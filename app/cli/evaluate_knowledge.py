import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.brand import Brand
from app.providers.dependencies import get_embedding_provider
from app.services.knowledge import search_knowledge_by_vector


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    case_id: str
    query: str
    answerable: bool
    expected_sections: frozenset[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate pgvector knowledge retrieval")
    parser.add_argument("--brand", required=True, help="Existing BrandPulse brand name")
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("docs/evaluation/pgvector_retrieval_cases.json"),
    )
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--threshold", type=float, default=0.0)
    return parser.parse_args()


def load_cases(path: Path) -> list[EvaluationCase]:
    raw_cases = json.loads(path.read_text(encoding="utf-8"))

    return [
        EvaluationCase(
            case_id=raw_case["id"],
            query=raw_case["query"],
            answerable=raw_case["answerable"],
            expected_sections=frozenset(raw_case["expected_sections"]),
        )
        for raw_case in raw_cases
    ]


async def evaluate(
    brand_name: str,
    cases_path: Path,
    limit: int,
    threshold: float,
) -> None:
    cases = load_cases(cases_path)
    provider = get_embedding_provider()
    query_vectors = await provider.embed_texts([case.query for case in cases])

    top_1_hits = 0
    top_3_hits = 0
    answerable_count = sum(case.answerable for case in cases)
    rejected_count = 0
    out_of_scope_count = len(cases) - answerable_count
    evidence_scores: list[float] = []
    out_of_scope_scores: list[float] = []

    async with async_session_factory() as session:
        brand = await session.scalar(select(Brand).where(Brand.name == brand_name))

        if brand is None:
            raise ValueError(f"brand does not exist: {brand_name}")

        for case, query_vector in zip(cases, query_vectors, strict=True):
            results = await search_knowledge_by_vector(
                session=session,
                brand_id=brand.id,
                query_vector=query_vector,
                limit=limit,
                similarity_threshold=threshold,
            )
            result_sections = [result.section_title or "" for result in results]
            evidence_match = next(
                (
                    (rank, result)
                    for rank, result in enumerate(results, start=1)
                    if (result.section_title or "") in case.expected_sections
                ),
                None,
            )
            evidence_rank = evidence_match[0] if evidence_match else None
            evidence_score = evidence_match[1].similarity if evidence_match else None
            top_1_hit = evidence_rank == 1
            top_3_hit = evidence_rank is not None and evidence_rank <= 3

            if case.answerable:
                top_1_hits += int(top_1_hit)
                top_3_hits += int(top_3_hit)
                if evidence_score is not None:
                    evidence_scores.append(evidence_score)
                status = "TOP1" if top_1_hit else "TOP3" if top_3_hit else "MISS"
            else:
                rejected = not results
                rejected_count += int(rejected)
                if results:
                    out_of_scope_scores.append(results[0].similarity)
                status = "REJECTED" if rejected else "FALSE_RECALL"

            top_score = f"{results[0].similarity:.4f}" if results else "-"
            top_section = result_sections[0] if result_sections else "-"
            formatted_evidence_rank = str(evidence_rank) if evidence_rank is not None else "-"
            formatted_evidence_score = (
                f"{evidence_score:.4f}" if evidence_score is not None else "-"
            )
            print(
                f"{case.case_id} status={status} top_score={top_score} "
                f"evidence_rank={formatted_evidence_rank} "
                f"evidence_score={formatted_evidence_score} top_section={top_section}"
            )

    minimum_evidence_score = min(evidence_scores) if evidence_scores else None
    maximum_out_of_scope_score = max(out_of_scope_scores) if out_of_scope_scores else None
    formatted_minimum_evidence = (
        f"{minimum_evidence_score:.4f}" if minimum_evidence_score is not None else "-"
    )
    formatted_maximum_out_of_scope = (
        f"{maximum_out_of_scope_score:.4f}" if maximum_out_of_scope_score is not None else "-"
    )

    print(
        "\nsummary "
        f"top1={top_1_hits}/{answerable_count} "
        f"top3={top_3_hits}/{answerable_count} "
        f"ood_rejected={rejected_count}/{out_of_scope_count} "
        f"min_evidence={formatted_minimum_evidence} "
        f"max_ood={formatted_maximum_out_of_scope} "
        f"threshold={threshold:.4f}"
    )


async def main() -> None:
    args = parse_args()
    await evaluate(
        brand_name=args.brand,
        cases_path=args.cases,
        limit=args.limit,
        threshold=args.threshold,
    )


if __name__ == "__main__":
    asyncio.run(main())
