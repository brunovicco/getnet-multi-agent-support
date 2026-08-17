"""Shared lexical helpers for retrieval gating.

The distinctive terms of a question are the words a grounded answer is expected to actually
mention. They are shared between the retrieval adapter, which measures evidence coverage, and the
knowledge agent, which owns the policy threshold applied to that measurement.
"""

_MINIMUM_DISTINCTIVE_LENGTH = 4
_ALWAYS_DISTINCTIVE = frozenset({"pix", "tef", "pos", "qr"})
STOPWORDS = frozenset(
    {
        "a",
        "about",
        "ainda",
        "and",
        "ao",
        "aos",
        "are",
        "as",
        "available",
        "can",
        "com",
        "como",
        "da",
        "das",
        "de",
        "difference",
        "do",
        "does",
        "dos",
        "e",
        "em",
        "explain",
        "for",
        "from",
        "have",
        "how",
        "i",
        "is",
        "it",
        "many",
        "me",
        "meu",
        "meus",
        "minha",
        "minhas",
        "much",
        "my",
        "na",
        "nao",
        "no",
        "nos",
        "of",
        "on",
        "os",
        "ou",
        "para",
        "pela",
        "pelo",
        "por",
        "posso",
        "precisa",
        "preciso",
        "qual",
        "quais",
        "quando",
        "quanto",
        "quantos",
        "quantas",
        "que",
        "sao",
        "se",
        "sem",
        "ser",
        "sobre",
        "tell",
        "that",
        "the",
        "their",
        "there",
        "this",
        "to",
        "um",
        "uma",
        "used",
        "using",
        "vou",
        "was",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "you",
        "your",
    }
)


def distinctive_terms(tokens: tuple[str, ...]) -> frozenset[str]:
    """Return the content terms a grounded answer is expected to address."""
    return frozenset(
        token
        for token in tokens
        if token not in STOPWORDS
        and (len(token) >= _MINIMUM_DISTINCTIVE_LENGTH or token in _ALWAYS_DISTINCTIVE)
        and not token.isdigit()
    )
