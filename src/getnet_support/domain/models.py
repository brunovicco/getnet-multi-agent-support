"""Framework-free contracts shared by the support system."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class AgentName(StrEnum):
    """Agents available to the orchestrator."""

    KNOWLEDGE = "knowledge"
    SUPPORT = "support"
    ESCALATION = "escalation"


class RouteName(StrEnum):
    """Observable execution routes."""

    GETNET_RAG = "getnet_rag"
    WEB_SEARCH = "web_search"
    CUSTOMER_TOOLS = "customer_tools"
    HUMAN_HANDOFF = "human_handoff"


@dataclass(frozen=True, slots=True)
class RouteDecision:
    """Typed output produced by the router."""

    agent: AgentName
    reason: str
    confidence: float

    def __post_init__(self) -> None:
        """Reject invalid confidence values at the domain boundary."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between zero and one")


@dataclass(frozen=True, slots=True)
class Source:
    """Public citation attached to grounded evidence."""

    title: str
    url: str


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    """A retrievable piece of untrusted external content."""

    text: str
    source: str
    title: str


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A chunk and its local retrieval relevance score."""

    chunk: KnowledgeChunk
    score: float


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Evidence returned by a knowledge adapter."""

    matches: tuple[RetrievedChunk, ...]


@dataclass(frozen=True, slots=True)
class WebSearchResult:
    """Grounded result returned by an optional web search provider."""

    answer: str
    sources: tuple[Source, ...]
    available: bool


@dataclass(frozen=True, slots=True)
class AgentResult:
    """Normalized result returned by every specialized agent."""

    answer: str
    agent: AgentName
    route: RouteName
    sources: tuple[Source, ...] = ()
    handoff_required: bool = False
    tool_calls: int = 0
    retrieval_result_count: int = 0


@dataclass(frozen=True, slots=True)
class ChatResult:
    """End-to-end output returned by the application use case."""

    answer: str
    agent: AgentName
    route: RouteName
    sources: tuple[Source, ...]
    trace_id: str
    confidence: float
    handoff_required: bool


@dataclass(frozen=True, slots=True)
class CustomerProfile:
    """Minimum customer data required by support flows."""

    user_id: str
    name: str
    status: str
    terminal_id: str


@dataclass(frozen=True, slots=True)
class Transaction:
    """A customer-scoped payment transaction."""

    transaction_id: str
    user_id: str
    amount: Decimal
    occurred_at: datetime
    payment_method: str
    status: str
    settlement_status: str
    expected_settlement_at: datetime | None


@dataclass(frozen=True, slots=True)
class TerminalStatus:
    """Current state of a terminal assigned to one customer."""

    terminal_id: str
    connectivity: str
    operational_status: str
    last_seen_at: datetime
    diagnostic: str
