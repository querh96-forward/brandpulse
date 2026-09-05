import argparse
import asyncio
from pathlib import Path

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.brand import Brand
from app.providers.dependencies import get_embedding_provider
from app.services.knowledge import replace_markdown_knowledge


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embed and ingest Markdown knowledge documents")
    parser.add_argument("--brand", required=True, help="Existing BrandPulse brand name")
    parser.add_argument("files", nargs="+", type=Path, help="Markdown files to ingest")
    return parser.parse_args()


async def ingest_knowledge(brand_name: str, files: list[Path]) -> None:
    provider = get_embedding_provider()

    async with async_session_factory() as session:
        brand = await session.scalar(select(Brand).where(Brand.name == brand_name))

        if brand is None:
            raise ValueError(f"brand does not exist: {brand_name}")

        total_chunks = 0

        for file_path in files:
            markdown = file_path.read_text(encoding="utf-8")
            chunks = await replace_markdown_knowledge(
                session=session,
                provider=provider,
                brand_id=brand.id,
                source_name=file_path.name,
                markdown=markdown,
            )
            total_chunks += len(chunks)
            print(f"source={file_path.name} chunks={len(chunks)}")

        await session.commit()

    print(
        f"brand={brand_name} total_chunks={total_chunks} "
        f"model={provider.model_name} dimensions={provider.dimensions}"
    )


async def main() -> None:
    args = parse_args()
    await ingest_knowledge(args.brand, args.files)


if __name__ == "__main__":
    asyncio.run(main())
