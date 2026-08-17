"""Small dependency-free TF-IDF retriever for the coding challenge."""

import math
import re
import unicodedata
from collections import Counter

from getnet_support.application.text import distinctive_terms
from getnet_support.domain.models import KnowledgeChunk, RetrievalResult, RetrievedChunk


def tokenize(text: str) -> tuple[str, ...]:
    """Create normalized word tokens for Portuguese and English text."""
    normalized = unicodedata.normalize("NFKD", text.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return tuple(re.findall(r"[a-z0-9]+", ascii_text))


class LocalTfidfRetriever:
    """Index a small corpus in memory and rank it with cosine similarity."""

    def __init__(self, chunks: tuple[KnowledgeChunk, ...]) -> None:
        """Build an in-memory index from immutable chunks."""
        if not chunks:
            raise ValueError("at least one knowledge chunk is required")
        self._chunks = chunks
        token_counts = tuple(Counter(tokenize(chunk.text)) for chunk in chunks)
        document_frequency = Counter(token for counts in token_counts for token in counts)
        total_documents = len(chunks)
        self._idf = {
            token: math.log((1 + total_documents) / (1 + frequency)) + 1
            for token, frequency in document_frequency.items()
        }
        self._maximum_idf = max(self._idf.values(), default=1.0)
        self._vectors = tuple(self._vectorize_counts(counts) for counts in token_counts)

    async def search(self, query: str, *, top_k: int = 3) -> RetrievalResult:
        """Return the highest-scoring chunks using local deterministic math."""
        query_tokens = tokenize(query)
        query_vector = self._vectorize_counts(Counter(query_tokens))
        terms = distinctive_terms(query_tokens)
        scored = (
            RetrievedChunk(
                chunk=chunk,
                score=self._cosine(query_vector, vector),
                coverage=self._coverage(terms, chunk),
            )
            for chunk, vector in zip(self._chunks, self._vectors, strict=True)
        )
        ranked = sorted(scored, key=lambda match: match.score, reverse=True)
        return RetrievalResult(matches=tuple(ranked[: max(0, top_k)]))

    def _coverage(self, terms: frozenset[str], chunk: KnowledgeChunk) -> float:
        """Return the share of the question's inverse-document-frequency mass present in a chunk.

        Weighting by IDF is what separates "mentions the same common words" from "is about the
        same thing": an unrelated product page can share "maquininha", but only the right page
        shares "crediario".
        """
        if not terms:
            return 1.0
        chunk_tokens = set(tokenize(chunk.text))
        total = sum(self._term_weight(term) for term in terms)
        if total <= 0:
            return 0.0
        covered = sum(self._term_weight(term) for term in terms if term in chunk_tokens)
        return covered / total

    def _term_weight(self, term: str) -> float:
        # A query term absent from the vocabulary cannot be covered by any chunk, and is weighted
        # as maximally rare so an unanswerable question is not silently treated as covered.
        return self._idf.get(term, self._maximum_idf)

    def _vectorize_counts(self, counts: Counter[str]) -> dict[str, float]:
        total = sum(counts.values())
        if total == 0:
            return {}
        return {
            token: (count / total) * self._idf[token]
            for token, count in counts.items()
            if token in self._idf
        }

    @staticmethod
    def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        shared = left.keys() & right.keys()
        dot_product = sum(left[token] * right[token] for token in shared)
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if not left_norm or not right_norm:
            return 0.0
        return dot_product / (left_norm * right_norm)
