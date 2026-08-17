"""Corpus hygiene applied between ingestion and indexing.

Marketing sites repeat navigation, contact blocks, and footers on every page. Indexed verbatim,
those fragments dominate a small lexical index and become the top match for unrelated questions,
which produces confidently wrong, source-attributed answers. The filters below are deliberately
structural rather than a hardcoded blocklist, so they keep working when the site is redesigned.
"""

import re
import unicodedata
from collections import defaultdict

from getnet_support.domain.models import KnowledgeChunk

MINIMUM_DISTINCT_WORDS = 12
MAXIMUM_NON_ALPHABETIC_RATIO = 0.35
_PHONE_PATTERN = re.compile(r"\b\d{3,4}[-\s]?\d{4}\b")
# A support phone number inside a chunk is a reliable marker of contact chrome (hero banners,
# "fale conosco" blocks) rather than of an answer to a product question.
_MAXIMUM_PHONE_MENTIONS = 0


def canonical_source(source: str) -> str:
    """Treat ``/en`` and ``/en/`` as one page, so duplicates are not mistaken for chrome."""
    return source.rstrip("/")


def normalized_text(text: str) -> str:
    """Return an accent-free, punctuation-free key used for duplicate detection."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    ascii_text = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def is_low_information(chunk: KnowledgeChunk) -> bool:
    """Return whether a chunk is a menu, contact block, or otherwise carries no answer."""
    words = normalized_text(chunk.text).split()
    if len(set(words)) < MINIMUM_DISTINCT_WORDS:
        return True
    if len(_PHONE_PATTERN.findall(chunk.text)) > _MAXIMUM_PHONE_MENTIONS:
        return True
    alphabetic = sum(1 for character in chunk.text if character.isalpha() or character.isspace())
    return (1 - (alphabetic / len(chunk.text))) > MAXIMUM_NON_ALPHABETIC_RATIO


def clean_corpus(chunks: tuple[KnowledgeChunk, ...]) -> tuple[KnowledgeChunk, ...]:
    """Drop cross-page boilerplate, duplicates, and low-information chunks, preserving order."""
    sources_by_text: defaultdict[str, set[str]] = defaultdict(set)
    for chunk in chunks:
        sources_by_text[normalized_text(chunk.text)].add(canonical_source(chunk.source))

    cleaned: list[KnowledgeChunk] = []
    seen: set[str] = set()
    for chunk in chunks:
        key = normalized_text(chunk.text)
        if not key or key in seen:
            continue
        # Identical text served from two different pages is site chrome, not page content.
        if len(sources_by_text[key]) > 1:
            continue
        if is_low_information(chunk):
            continue
        seen.add(key)
        cleaned.append(chunk)
    return tuple(cleaned)
