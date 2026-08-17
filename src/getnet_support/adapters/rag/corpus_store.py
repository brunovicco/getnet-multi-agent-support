"""Persist and load validated local knowledge artifacts."""

import json
from pathlib import Path

from getnet_support.domain.models import KnowledgeChunk


class CorpusFormatError(ValueError):
    """Raised when a persisted corpus does not match the expected boundary schema."""


def save_corpus(path: Path, chunks: tuple[KnowledgeChunk, ...]) -> None:
    """Write a portable JSON corpus artifact using only public chunk metadata."""
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = [
        {
            "text": chunk.text,
            "source": chunk.source,
            "title": chunk.title,
            "curated": chunk.curated,
        }
        for chunk in chunks
    ]
    path.write_text(json.dumps(serialized, ensure_ascii=False, indent=2), encoding="utf-8")


def load_corpus(path: Path) -> tuple[KnowledgeChunk, ...]:
    """Load and validate a corpus artifact at the untrusted filesystem boundary."""
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CorpusFormatError(f"cannot read corpus artifact: {path}") from exc
    if not isinstance(raw, list) or not raw:
        raise CorpusFormatError("corpus artifact must be a non-empty JSON list")

    chunks: list[KnowledgeChunk] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise CorpusFormatError(f"corpus item {index} must be an object")
        text = item.get("text")
        source = item.get("source")
        title = item.get("title")
        if (
            not isinstance(text, str)
            or not text.strip()
            or not isinstance(source, str)
            or not source.strip()
            or not isinstance(title, str)
            or not title.strip()
        ):
            raise CorpusFormatError(f"corpus item {index} has invalid text, source, or title")
        curated = item.get("curated", False)
        if not isinstance(curated, bool):
            raise CorpusFormatError(f"corpus item {index} has an invalid curated flag")
        chunks.append(
            KnowledgeChunk(
                text=text.strip(),
                source=source.strip(),
                title=title.strip(),
                curated=curated,
            )
        )
    return tuple(chunks)


def load_corpus_or_fallback(
    path: Path, fallback: tuple[KnowledgeChunk, ...]
) -> tuple[KnowledgeChunk, ...]:
    """Load the ingested artifact, retaining a deterministic startup fallback."""
    if not path.is_file():
        return fallback
    try:
        return load_corpus(path)
    except CorpusFormatError:
        return fallback
