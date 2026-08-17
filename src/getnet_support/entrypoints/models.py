"""FastAPI request and response boundary models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from getnet_support.domain.models import ChatResult, Source


class ChatRequest(BaseModel):
    """Validated input accepted by ``POST /chat``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=4_000)
    user_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")


class SourceResponse(BaseModel):
    """Public citation metadata."""

    title: str
    url: str

    @classmethod
    def from_domain(cls, source: Source) -> "SourceResponse":
        """Translate a domain citation to the transport schema."""
        return cls(title=source.title, url=source.url)


class ChatResponse(BaseModel):
    """Observable multi-agent response."""

    answer: str
    agent: Literal["knowledge", "support", "escalation"]
    route: Literal["getnet_rag", "web_search", "customer_tools", "human_handoff"]
    sources: list[SourceResponse]
    trace_id: str
    confidence: float
    handoff_required: bool

    @classmethod
    def from_domain(cls, result: ChatResult) -> "ChatResponse":
        """Translate the use-case output without exposing internal models."""
        return cls(
            answer=result.answer,
            agent=result.agent.value,
            route=result.route.value,
            sources=[SourceResponse.from_domain(source) for source in result.sources],
            trace_id=result.trace_id,
            confidence=result.confidence,
            handoff_required=result.handoff_required,
        )


class HealthResponse(BaseModel):
    """Liveness and local capability summary."""

    status: Literal["ok"] = "ok"
    service: str
    rag: Literal["ready"] = "ready"
    web_search: Literal["unavailable"] = "unavailable"
