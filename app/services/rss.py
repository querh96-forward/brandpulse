import uuid
from xml.etree import ElementTree

from httpx import AsyncClient

from app.schemas.article import ArticleCreate
from app.services.content_cleaning import clean_html_content, clean_html_inline


def _find_item_text(item: ElementTree.Element, *local_names: str) -> str:
    expected_names = set(local_names)

    for child in item:
        local_name = child.tag.rsplit("}", maxsplit=1)[-1]

        if local_name in expected_names and child.text:
            return child.text

    return ""


def parse_rss_feed(
    xml_content: str,
    source_name: str,
    brand_id: uuid.UUID | None = None,
) -> list[ArticleCreate]:
    root = ElementTree.fromstring(xml_content)
    articles: list[ArticleCreate] = []

    for item in root.findall("./channel/item"):
        title = clean_html_inline(_find_item_text(item, "title"))
        raw_content = _find_item_text(item, "encoded")

        if not raw_content.strip():
            raw_content = _find_item_text(item, "description")

        content = clean_html_content(raw_content)
        url = _find_item_text(item, "link").strip() or None

        if not title or not content:
            continue

        article = ArticleCreate(
            brand_id=brand_id,
            source_type="rss",
            source_name=source_name,
            title=title,
            content=content,
            url=url,
        )
        articles.append(article)

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
