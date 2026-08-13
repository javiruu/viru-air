from __future__ import annotations

from html.parser import HTMLParser


class _JsonLdScriptCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.documents: list[str] = []
        self._chunks: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        attributes = {key.lower(): value for key, value in attrs}
        content_type = (attributes.get("type") or "").split(";", 1)[0].strip().lower()
        if content_type == "application/ld+json":
            self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._chunks is not None:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._chunks is not None:
            self.documents.append("".join(self._chunks))
            self._chunks = None


def extract_json_ld_documents(html: str) -> list[str]:
    collector = _JsonLdScriptCollector()
    collector.feed(html)
    collector.close()
    return collector.documents
