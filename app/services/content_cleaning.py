from html import unescape
from html.parser import HTMLParser

BLOCK_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "dd",
        "div",
        "dl",
        "dt",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    }
)
IGNORED_TAGS = frozenset(
    {
        "canvas",
        "head",
        "iframe",
        "noscript",
        "object",
        "script",
        "style",
        "svg",
        "template",
    }
)


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        normalized_tag = tag.lower()

        if normalized_tag in IGNORED_TAGS:
            self.ignored_depth += 1
            return

        if self.ignored_depth == 0 and normalized_tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if self.ignored_depth == 0 and tag.lower() in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()

        if normalized_tag in IGNORED_TAGS:
            self.ignored_depth = max(0, self.ignored_depth - 1)
            return

        if self.ignored_depth == 0 and normalized_tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.ignored_depth == 0:
            self.parts.append(data)


def normalize_plain_text(value: str) -> str:
    decoded = unescape(value).replace("\u00a0", " ")
    lines = [" ".join(line.split()) for line in decoded.splitlines()]
    return "\n".join(line for line in lines if line)


def clean_html_content(value: str) -> str:
    extractor = _HTMLTextExtractor()
    extractor.feed(value)
    extractor.close()
    return normalize_plain_text("".join(extractor.parts))


def clean_html_inline(value: str) -> str:
    return " ".join(clean_html_content(value).split())
