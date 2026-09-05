import argparse
import asyncio

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.brand import Brand
from app.providers.dependencies import get_embedding_provider
from app.services.knowledge import search_knowledge


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search BrandPulse's pgvector knowledge base")
    parser.add_argument("query", help="Natural-language knowledge query")
    parser.add_argument("--brand", required=True, help="Existing BrandPulse brand name")
    parser.add_argument("--limit", type=int, default=3, help="Maximum results to return")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Minimum cosine similarity between 0 and 1",
    )
    return parser.parse_args()


async def run_search(
    brand_name: str,
    query: str,
    limit: int,
    threshold: float,
) -> None:
    provider = get_embedding_provider()

    async with async_session_factory() as session:
        brand = await session.scalar(select(Brand).where(Brand.name == brand_name))

        if brand is None:
            raise ValueError(f"brand does not exist: {brand_name}")

        results = await search_knowledge(
            session=session,
            provider=provider,
            brand_id=brand.id,
            query=query,
            limit=limit,
            similarity_threshold=threshold,
        )

    print(
        f"brand={brand_name} results={len(results)} model={provider.model_name} "
        f"dimensions={provider.dimensions}"
    )

    for rank, result in enumerate(results, start=1):
        preview = " ".join(result.content.split())[:240]
        print(
            f"\nrank={rank} similarity={result.similarity:.4f} "
            f"source={result.source_name} section={result.section_title}\n{preview}"
        )


async def main() -> None:
    args = parse_args()
    await run_search(
        brand_name=args.brand,
        query=args.query,
        limit=args.limit,
        threshold=args.threshold,
    )


if __name__ == "__main__":
    asyncio.run(main())
