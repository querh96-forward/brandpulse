import uuid
from xml.etree import ElementTree

from httpx import AsyncClient

from app.schemas.article import ArticleCreate


def parse_rss_feed(
    xml_content: str,
    source_name: str,
    brand_id: uuid.UUID | None = None,
) -> list[ArticleCreate]:
    root = ElementTree.fromstring(xml_content)
    articles: list[ArticleCreate] = []

    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        content = (item.findtext("description") or "").strip()
        url = (item.findtext("link") or "").strip() or None

        if not title or not content:
            continue

        articles.append(
            ArticleCreate(
                brand_id=brand_id,
                source_type="rss",
                source_name=source_name,
                title=title,
                content=content,
                url=url,
            )
        )

    return articles


async def fetch_and_parse_rss_feed(
    client: AsyncClient,
    url: str,
    source_name: str,
    brand_id: uuid.UUID | None = None,
) -> list[ArticleCreate]:
    response = await client.get(url)
    response.raise_for_status()

    return parse_rss_feed(
        xml_content=response.text,
        source_name=source_name,
        brand_id=brand_id,
    )
