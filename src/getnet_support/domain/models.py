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
    AGENT_SEQUENCE = "agent_sequence"


@dataclass(frozen=True, slots=True)
class RouteDecision:
    """Typed output produced by the router."""

    agent: AgentName
    reason: str
    confidence: float
    secondary_agent: AgentName | None = None
    guardrail: bool = False

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
    """A retrievable piece of untrusted external content.

    ``curated`` marks a chunk that a human reviewed and attributed to an official page. Curated
    chunks answer a question directly, while scraped chunks may be page teasers that merely
    mention the topic; the knowledge agent uses the flag to break near-ties in favour of reviewed
    evidence. It is never a trust signal for prompt content: every chunk stays untrusted data.
    """

    text: str
    source: str
    title: str
    curated: bool = False


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A chunk, its similarity score, and how much of the question it actually covers.

    ``score`` answers "how similar is this text?"; ``coverage`` answers "does it mention what was
    asked?", weighted so a rare term such as "crediario" counts for more than a common one. A high
    score with low coverage is the signature of a confidently wrong, wrongly-cited answer.
    """

    chunk: KnowledgeChunk
    score: float
    coverage: float = 0.0


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
