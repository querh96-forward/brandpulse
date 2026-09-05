import argparse
import asyncio

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.brand import Brand
from app.providers.dependencies import get_embedding_provider, get_evidence_provider
from app.services.knowledge import retrieve_and_assess_knowledge


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retrieve and assess BrandPulse knowledge evidence"
    )
    parser.add_argument("query", help="Natural-language knowledge query")
    parser.add_argument("--brand", required=True, help="Existing BrandPulse brand name")
    parser.add_argument("--limit", type=int, default=3, help="Maximum candidates to assess")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Minimum cosine similarity between 0 and 1",
    )
    return parser.parse_args()


async def run_assessment(
    brand_name: str,
    query: str,
    limit: int,
    threshold: float,
) -> None:
    embedding_provider = get_embedding_provider()
    evidence_provider = get_evidence_provider()

    async with async_session_factory() as session:
        brand = await session.scalar(select(Brand).where(Brand.name == brand_name))

        if brand is None:
            raise ValueError(f"brand does not exist: {brand_name}")

        assessed = await retrieve_and_assess_knowledge(
            session=session,
            embedding_provider=embedding_provider,
            evidence_provider=evidence_provider,
            brand_id=brand.id,
            query=query,
            limit=limit,
            similarity_threshold=threshold,
        )

    print(
        f"brand={brand_name} candidates={len(assessed.results)} "
        f"embedding_model={embedding_provider.model_name} "
        f"judge_model={evidence_provider.model_name}"
    )

    for rank, result in enumerate(assessed.results, start=1):
        print(
            f"rank={rank} similarity={result.similarity:.4f} "
            f"source={result.source_name} section={result.section_title}"
        )

    supporting_ranks = ",".join(map(str, assessed.assessment.supporting_ranks)) or "-"
    print(
        "\nassessment "
        f"sufficient={str(assessed.assessment.sufficient).lower()} "
        f"supporting_ranks={supporting_ranks}"
    )
    print(f"reason={assessed.assessment.reason}")


async def main() -> None:
    args = parse_args()
    await run_assessment(
        brand_name=args.brand,
        query=args.query,
        limit=args.limit,
        threshold=args.threshold,
    )


if __name__ == "__main__":
    asyncio.run(main())
