import uuid

from httpx import AsyncClient, MockTransport, Request, Response

from app.services.rss import fetch_and_parse_rss_feed, parse_rss_feed


def test_parse_rss_feed() -> None:
    brand_id = uuid.uuid4()

    xml_content = """
    <rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
        <channel>
            <title>Ocean Technology Daily</title>
            <item>
                <title><![CDATA[<b>水下机器人</b>发布新产品]]></title>
                <link>https://example.com/news/1</link>
                <description><![CDATA[<p>短摘要。</p>]]></description>
                <content:encoded><![CDATA[
                    <article>
                        <p>新一代水下机器人&nbsp;正式发布。</p>
                        <script>tracking()</script>
                        <p>设备支持深水巡检&amp;环境监测。</p>
                    </article>
                ]]></content:encoded>
            </item>
            <item>
                <title>缺少正文的文章</title>
                <link>https://example.com/news/2</link>
            </item>
            <item>
                <title>正文清洗后为空的文章</title>
                <description><![CDATA[
                    <script>tracking()</script>
                    <style>body {}</style>
                ]]></description>
            </item>
        </channel>
    </rss>
    """

    articles = parse_rss_feed(
        xml_content=xml_content,
        source_name="Ocean Technology Daily",
        brand_id=brand_id,
    )

    assert len(articles) == 1

    article = articles[0]
    assert article.brand_id == brand_id
    assert article.source_type == "rss"
    assert article.source_name == "Ocean Technology Daily"
    assert article.title == "水下机器人发布新产品"
    assert article.content == "新一代水下机器人 正式发布。\n设备支持深水巡检&环境监测。"
    assert article.url == "https://example.com/news/1"


def test_parse_rss_feed_falls_back_to_description_when_encoded_content_is_blank() -> None:
    xml_content = """
    <rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
        <channel>
            <item>
                <title>RSS 正文回退测试</title>
                <description><![CDATA[<p>description 中的有效正文。</p>]]></description>
                <content:encoded>   </content:encoded>
            </item>
        </channel>
    </rss>
    """

    articles = parse_rss_feed(
        xml_content=xml_content,
        source_name="Fallback Feed",
    )

    assert len(articles) == 1
    assert articles[0].content == "description 中的有效正文。"


async def test_fetch_and_parse_rss_feed() -> None:
    xml_content = """
    <rss version="2.0">
        <channel>
            <title>Test Feed</title>
            <item>
                <title>自动采集文章</title>
                <link>https://example.com/articles/1</link>
                <description>这是一篇通过 RSS 自动采集的文章。</description>
            </item>
        </channel>
    </rss>
    """

    def handle_request(request: Request) -> Response:
        assert str(request.url) == "https://example.com/rss.xml"

        return Response(
            status_code=200,
            text=xml_content,
            headers={"content-type": "application/rss+xml"},
        )

    transport = MockTransport(handle_request)

    async with AsyncClient(transport=transport) as client:
        articles = await fetch_and_parse_rss_feed(
            client=client,
            url="https://example.com/rss.xml",
            source_name="Test Feed",
        )

    assert len(articles) == 1
    assert articles[0].title == "自动采集文章"
    assert articles[0].source_type == "rss"
