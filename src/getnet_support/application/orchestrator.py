"""Explicit multi-agent orchestration use case."""

from time import perf_counter
from uuid import uuid4

from getnet_support.application.agents.customer_support import CustomerSupportAgent
from getnet_support.application.agents.escalation import EscalationAgent
from getnet_support.application.agents.knowledge import KnowledgeAgent
from getnet_support.application.agents.router import RouterAgent
from getnet_support.application.ports import EventSink
from getnet_support.domain.models import AgentName, ChatResult

ROUTING_CONFIDENCE_THRESHOLD = 0.60


class SupportOrchestrator:
    """Make all routing and agent-to-agent data flow visible in one place."""

    def __init__(
        self,
        router: RouterAgent,
        knowledge: KnowledgeAgent,
        support: CustomerSupportAgent,
        escalation: EscalationAgent,
        events: EventSink,
    ) -> None:
        """Inject agents and the metadata-only event boundary."""
        self._router = router
        self._knowledge = knowledge
        self._support = support
        self._escalation = escalation
        self._events = events

    async def chat(self, *, message: str, user_id: str, trace_id: str | None = None) -> ChatResult:
        """Route and execute a message through exactly one specialized agent."""
        request_trace_id = trace_id or uuid4().hex
        started = perf_counter()
        decision = self._router.route(message)
        self._events.emit(
            "router_decision",
            {
                "trace_id": request_trace_id,
                "user_id": user_id,
                "selected_agent": decision.agent.value,
                "confidence": decision.confidence,
                "reason": decision.reason,
            },
        )

        if decision.confidence < ROUTING_CONFIDENCE_THRESHOLD:
            result = self._escalation.handle(reason="Router confidence below threshold.")
        elif decision.agent is AgentName.KNOWLEDGE:
            result = await self._knowledge.handle(message)
        elif decision.agent is AgentName.SUPPORT:
            result = await self._support.handle(message, user_id)
        else:
            result = self._escalation.handle(reason=decision.reason)

        latency_ms = round((perf_counter() - started) * 1000, 2)
        self._events.emit(
            "agent_execution",
            {
                "trace_id": request_trace_id,
                "user_id": user_id,
                "agent": result.agent.value,
                "route": result.route.value,
                "latency_ms": latency_ms,
                "tool_calls": result.tool_calls,
                "retrieval_result_count": result.retrieval_result_count,
                "handoff_required": result.handoff_required,
            },
        )
        return ChatResult(
            answer=result.answer,
            agent=result.agent,
            route=result.route,
            sources=result.sources,
            trace_id=request_trace_id,
            confidence=decision.confidence,
            handoff_required=result.handoff_required,
        )
