from app.schemas.article import ArticleCreate
from app.services.article import calculate_content_hash
from app.services.content_cleaning import clean_html_content, clean_html_inline


def test_clean_html_content_removes_markup_and_unsafe_blocks() -> None:
    raw_html = """
    <html>
      <head><title>页面标题不属于正文</title></head>
      <body>
        <article>
          <h2>设备&nbsp;告警</h2>
          <p>用户反馈 <strong>SEAL-07</strong>，需要立即回收。</p>
          <script>send_private_data()</script>
          <style>.hidden { display: none; }</style>
          <p>品牌方已启动检测&amp;维修流程。</p>
        </article>
      </body>
    </html>
    """

    assert clean_html_content(raw_html) == (
        "设备 告警\n用户反馈 SEAL-07，需要立即回收。\n品牌方已启动检测&维修流程。"
    )


def test_clean_html_inline_collapses_block_boundaries() -> None:
    assert clean_html_inline("<span> 水下设备 </span><br><b>安全通告</b>") == ("水下设备 安全通告")


def test_article_create_cleans_manual_html_before_persistence() -> None:
    article = ArticleCreate(
        source_type="html",
        source_name="Manual HTML",
        title="<b> BC-D200&nbsp;密封告警 </b>",
        content="<p>设备&nbsp;出现进水。</p><script>ignore()</script><p>请立即回收。</p>",
    )

    assert article.title == "BC-D200 密封告警"
    assert article.content == "设备 出现进水。\n请立即回收。"


def test_equivalent_html_and_plain_text_produce_the_same_content_hash() -> None:
    html_article = ArticleCreate(
        source_type="rss",
        source_name="HTML Feed",
        title="HTML article",
        content="<p>设备&nbsp;出现进水。</p><p>请立即回收。</p>",
    )
    plain_article = ArticleCreate(
        source_type="manual",
        source_name="Manual Input",
        title="Plain article",
        content="设备 出现进水。\n请立即回收。",
    )

    assert html_article.content == plain_article.content
    assert calculate_content_hash(html_article.content) == calculate_content_hash(
        plain_article.content
    )
