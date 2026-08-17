import json
from pathlib import Path

import pytest

from getnet_support.adapters.rag.corpus_store import (
    CorpusFormatError,
    load_corpus,
    load_corpus_or_fallback,
    save_corpus,
)
from getnet_support.domain.models import KnowledgeChunk


def test_corpus_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "corpus.json"
    chunks = (
        KnowledgeChunk(
            text="Grounded Getnet evidence",
            source="https://getnet.test",
            title="Getnet",
        ),
    )

    save_corpus(path, chunks)

    assert load_corpus(path) == chunks


def test_invalid_corpus_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps([{"text": "missing metadata"}]), encoding="utf-8")

    with pytest.raises(CorpusFormatError, match="invalid"):
        load_corpus(path)


def test_invalid_corpus_uses_explicit_fallback(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("not-json", encoding="utf-8")
    fallback = (
        KnowledgeChunk(text="Fallback evidence", source="https://getnet.test", title="Fallback"),
    )

    assert load_corpus_or_fallback(path, fallback) == fallback
