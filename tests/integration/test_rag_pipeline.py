from pathlib import Path

import pytest

from getnet_support.adapters.rag.corpus_store import load_corpus, save_corpus
from getnet_support.adapters.rag.ingest import GetnetHttpIngestor
from getnet_support.adapters.rag.retriever import LocalTfidfRetriever
from getnet_support.adapters.tools.web_search import WebSearchTool
from getnet_support.application.agents.knowledge import KnowledgeAgent
from getnet_support.domain.models import AgentName, RouteName


@pytest.mark.asyncio
async def test_html_to_persisted_index_to_grounded_response(tmp_path: Path) -> None:
    html = """
    <html>
      <head><title>Getnet Payment Link</title></head>
      <body>
        <nav>Ignore navigation</nav>
        <main>
          <h1>Payment Link</h1>
          <p>
            Getnet Payment Link lets merchants create a secure online checkout and share it
            through WhatsApp, email, or social networks without requiring a physical terminal.
          </p>
        </main>
      </body>
    </html>
    """
    source = "https://www.getnet.net/en/payment-link"
    ingested = GetnetHttpIngestor().parse_html(html, source=source)
    artifact = tmp_path / "getnet.json"
    save_corpus(artifact, ingested)
    loaded = load_corpus(artifact)
    agent = KnowledgeAgent(LocalTfidfRetriever(loaded), WebSearchTool())

    result = await agent.handle("Can I share a Getnet Payment Link through WhatsApp?")

    assert result.agent is AgentName.KNOWLEDGE
    assert result.route is RouteName.GETNET_RAG
    assert "WhatsApp" in result.answer
    assert result.sources[0].url == source
