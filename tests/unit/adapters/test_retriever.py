import pytest

from getnet_support.adapters.rag.corpus import DEFAULT_GETNET_CORPUS
from getnet_support.adapters.rag.retriever import LocalTfidfRetriever, tokenize


def test_tokenize_normalizes_accents() -> None:
    assert tokenize("Crédito e antecipação") == ("credito", "e", "antecipacao")


@pytest.mark.asyncio
async def test_retriever_ranks_payment_link_source_first() -> None:
    result = await LocalTfidfRetriever(DEFAULT_GETNET_CORPUS).search(
        "Can I sell through WhatsApp using the Payment Link?"
    )

    assert result.matches
    assert result.matches[0].chunk.title == "Getnet Payment Link"
    assert result.matches[0].score > 0


def test_retriever_requires_a_corpus() -> None:
    with pytest.raises(ValueError, match="at least one"):
        LocalTfidfRetriever(())
