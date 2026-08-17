"""Offline HTTP ingestion for small, explicitly selected Getnet pages."""

import argparse
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from getnet_support.adapters.rag.corpus import DEFAULT_GETNET_CORPUS
from getnet_support.adapters.rag.corpus_store import save_corpus
from getnet_support.domain.models import KnowledgeChunk

DEFAULT_URLS = (
    "https://www.getnet.net/",
    "https://www.getnet.net/en",
    "https://site.getnet.com.br/produtos-fisicos/",
    "https://site.getnet.com.br/link-de-pagamento/",
    "https://site.getnet.com.br/pix/",
    "https://site.getnet.com.br/quando-vale-a-pena-antecipar-as-suas-vendas-no-cartao/",
)


class GetnetHttpIngestor:
    """Fetch selected pages with bounded I/O and convert them into text chunks."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        chunk_size: int = 900,
        max_chunks_per_page: int = 20,
    ) -> None:
        """Configure bounded HTTP and chunk sizes."""
        self._timeout_seconds = timeout_seconds
        self._chunk_size = chunk_size
        self._max_chunks_per_page = max_chunks_per_page

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
                chunks.extend(self.parse_html(response.text, source=str(response.url)))
        return tuple(chunks)

    def parse_html(self, html: str, *, source: str) -> tuple[KnowledgeChunk, ...]:
        """Convert one HTML document into bounded, paragraph-aware chunks."""
        soup = BeautifulSoup(html, "html.parser")
        for element in soup(["script", "style", "noscript", "svg"]):
            element.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else source
        content = soup.find("main") or soup.body or soup
        blocks = tuple(
            normalized
            for element in content.find_all(["h1", "h2", "h3", "p", "li"])
            if (normalized := " ".join(element.get_text(" ", strip=True).split()))
        )
        if not blocks:
            fallback_text = " ".join(content.get_text(" ", strip=True).split())
            blocks = (fallback_text,) if fallback_text else ()
        segments = self._chunk_blocks(blocks)
        return tuple(
            KnowledgeChunk(text=segment, source=source, title=title)
            for segment in segments[: self._max_chunks_per_page]
            if len(segment) >= 80
        )

    def _chunk_blocks(self, blocks: tuple[str, ...]) -> tuple[str, ...]:
        chunks: list[str] = []
        current = ""
        for block in blocks:
            remaining = block
            while remaining:
                capacity = self._chunk_size - len(current) - (1 if current else 0)
                if capacity <= 0:
                    chunks.append(current)
                    current = ""
                    continue
                if len(remaining) <= capacity:
                    current = f"{current} {remaining}".strip()
                    remaining = ""
                    continue
                split_at = remaining.rfind(" ", 0, capacity + 1)
                if split_at <= 0:
                    split_at = capacity
                current = f"{current} {remaining[:split_at]}".strip()
                chunks.append(current)
                current = ""
                remaining = remaining[split_at:].strip()
        if current:
            chunks.append(current)
        return tuple(chunks)


async def _run(output: Path, urls: tuple[str, ...]) -> None:
    ingested_chunks = await GetnetHttpIngestor().ingest(urls)
    if not ingested_chunks:
        raise RuntimeError("ingestion produced no chunks")
    # Reviewed seeds keep the challenge scenarios deterministic while the fetched chunks extend
    # coverage with the latest content from the selected official pages.
    save_corpus(output, (*DEFAULT_GETNET_CORPUS, *ingested_chunks))


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
