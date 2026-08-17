"""Ports used by agents to access data and external capabilities."""

from collections.abc import Mapping
from typing import Protocol

from getnet_support.domain.models import (
    CustomerProfile,
    RetrievalResult,
    RetrievedChunk,
    TerminalStatus,
    Transaction,
    WebSearchResult,
)


class GetnetKnowledgePort(Protocol):
    """Search the indexed Getnet knowledge base."""

    async def search(self, query: str, *, top_k: int = 3) -> RetrievalResult:
        """Return relevant grounded chunks ordered by score."""
        ...


class WebSearchPort(Protocol):
    """Search a provider for current general information."""

    async def search(self, query: str) -> WebSearchResult:
        """Return a grounded answer, or an explicit unavailable result."""
        ...


class AnswerGeneratorPort(Protocol):
    """Generate a response from already-retrieved Getnet evidence."""

    async def generate(self, query: str, evidence: tuple[RetrievedChunk, ...]) -> str | None:
        """Return a grounded answer, or ``None`` so the caller uses its local fallback."""
        ...


class CustomerProfileToolPort(Protocol):
    """Retrieve the authenticated customer's support profile."""

    async def get_customer_profile(self, user_id: str) -> CustomerProfile | None:
        """Return only the profile associated with ``user_id``."""
        ...


class RecentTransactionsToolPort(Protocol):
    """Retrieve recent transactions scoped to one customer."""

    async def get_recent_transactions(self, user_id: str) -> tuple[Transaction, ...]:
        """Return transactions belonging only to ``user_id``."""
        ...


class TerminalStatusToolPort(Protocol):
    """Retrieve a customer's assigned terminal state."""

    async def get_terminal_status(self, user_id: str) -> TerminalStatus | None:
        """Return the terminal assigned to ``user_id`` when it exists."""
        ...


class EventSink(Protocol):
    """Emit metadata-only structured application events."""

    def emit(self, event: str, fields: Mapping[str, object]) -> None:
        """Record a stable event without message or response content."""
        ...
