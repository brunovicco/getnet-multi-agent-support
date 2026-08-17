"""Offline HTTP ingestion for small, explicitly selected Getnet pages."""

import argparse
import json
from pathlib import Path
from typing import TypedDict

import httpx
from bs4 import BeautifulSoup

from getnet_support.domain.models import KnowledgeChunk

DEFAULT_URLS = (
    "https://www.getnet.net/",
    "https://www.getnet.net/en",
    "https://site.getnet.com.br/produtos-fisicos/",
    "https://site.getnet.com.br/link-de-pagamento/",
    "https://site.getnet.com.br/pix/",
)


class SerializedChunk(TypedDict):
    """JSON representation written by the ingestion command."""

    text: str
    source: str
    title: str


class GetnetHttpIngestor:
    """Fetch selected pages with bounded I/O and convert them into text chunks."""

    def __init__(self, *, timeout_seconds: float = 10.0, chunk_size: int = 900) -> None:
        """Configure bounded HTTP and chunk sizes."""
        self._timeout_seconds = timeout_seconds
        self._chunk_size = chunk_size

    async def ingest(self, urls: tuple[str, ...]) -> tuple[KnowledgeChunk, ...]:
        """Fetch pages sequentially; skip failures so one page cannot break the corpus."""
        chunks: list[KnowledgeChunk] = []
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "getnet-support-challenge/0.1"},
        ) as client:
            for url in urls:
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                except httpx.HTTPError:
                    continue
                chunks.extend(self._parse(response.text, source=str(response.url)))
        return tuple(chunks)

    def _parse(self, html: str, *, source: str) -> tuple[KnowledgeChunk, ...]:
        soup = BeautifulSoup(html, "html.parser")
        for element in soup(["script", "style", "noscript", "svg"]):
            element.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else source
        text = " ".join(soup.get_text(" ", strip=True).split())
        segments = tuple(
            text[index : index + self._chunk_size].strip()
            for index in range(0, len(text), self._chunk_size)
        )
        return tuple(
            KnowledgeChunk(text=segment, source=source, title=title)
            for segment in segments
            if len(segment) >= 80
        )


async def _run(output: Path, urls: tuple[str, ...]) -> None:
    chunks = await GetnetHttpIngestor().ingest(urls)
    serialized: list[SerializedChunk] = [
        {"text": chunk.text, "source": chunk.source, "title": chunk.title} for chunk in chunks
    ]
    output.write_text(json.dumps(serialized, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    """Run ingestion outside the API request path."""
    import asyncio

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("urls", nargs="*", default=DEFAULT_URLS)
    arguments = parser.parse_args()
    asyncio.run(_run(arguments.output, tuple(arguments.urls)))


if __name__ == "__main__":
    main()
