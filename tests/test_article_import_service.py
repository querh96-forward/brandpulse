from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.brand import Brand
from app.schemas.article import ArticleCreate
from app.services.article import save_collected_articles


async def test_save_collected_articles_skips_duplicates(
    db_session: AsyncSession,
) -> None:
    brand = Brand(
        name="CollectedArticleBrand",
        description="用于测试采集结果保存",
    )

    db_session.add(brand)
    await db_session.flush()

    articles = [
        ArticleCreate(
            brand_id=brand.id,
            source_type="rss",
            source_name="Test Feed",
            title="第一篇采集文章",
            content="两篇文章使用相同正文，因此只保存一次。",
        ),
        ArticleCreate(
            brand_id=brand.id,
            source_type="rss",
            source_name="Test Feed",
            title="标题不同但正文相同",
            content="两篇文章使用相同正文，因此只保存一次。",
        ),
    ]

    imported_count, skipped_count = await save_collected_articles(
        session=db_session,
        articles=articles,
    )

    assert imported_count == 1
    assert skipped_count == 1

    result = await db_session.scalars(select(Article).where(Article.brand_id == brand.id))
    saved_articles = list(result.all())

    assert len(saved_articles) == 1
    assert saved_articles[0].title == "第一篇采集文章"
    assert saved_articles[0].feed_source_id is None
