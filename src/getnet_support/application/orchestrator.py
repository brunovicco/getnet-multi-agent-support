"""Explicit multi-agent orchestration use case."""

from hashlib import sha256
from time import perf_counter
from uuid import uuid4

from getnet_support.application.agents.customer_support import CustomerSupportAgent
from getnet_support.application.agents.escalation import (
    EscalationAgent,
    attach_handoff_reference,
)
from getnet_support.application.agents.knowledge import KnowledgeAgent
from getnet_support.application.agents.router import RouterAgent
from getnet_support.application.ports import EventSink
from getnet_support.domain.models import AgentName, AgentResult, ChatResult, RouteName

ROUTING_CONFIDENCE_THRESHOLD = 0.60
_USER_REFERENCE_NAMESPACE = "getnet-multi-agent-support"


def pseudonymize_user_id(user_id: str) -> str:
    """Return a stable pseudonymous log reference instead of the raw identifier."""
    namespaced_value = f"{_USER_REFERENCE_NAMESPACE}:{user_id}"
    digest = sha256(namespaced_value.encode()).hexdigest()[:16]
    return f"usr_{digest}"


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
        """Route a message to one specialized agent, or to a short agent sequence."""
        request_trace_id = trace_id or uuid4().hex
        user_reference_hash = pseudonymize_user_id(user_id)
        started = perf_counter()
        decision = await self._router.route(message)
        self._events.emit(
            "router_decision",
            {
                "trace_id": request_trace_id,
                "user_reference_hash": user_reference_hash,
                "selected_agent": decision.agent.value,
                "secondary_agent": (
                    decision.secondary_agent.value if decision.secondary_agent else None
                ),
                "confidence": decision.confidence,
                "guardrail": decision.guardrail,
                # Provenance makes the classifier fallback rate a metric instead of a mystery.
                "decision_source": decision.source.value,
                "classifier_latency_ms": decision.classifier_latency_ms,
                "reason": decision.reason,
            },
        )

        if decision.confidence < ROUTING_CONFIDENCE_THRESHOLD:
            result = self._escalation.handle(
                reason="Router confidence below threshold.",
                message=message,
                reference_seed=request_trace_id,
            )
        elif decision.agent is AgentName.ESCALATION:
            result = self._escalation.handle(
                reason=decision.reason,
                message=message,
                reference_seed=request_trace_id,
            )
        else:
            result = await self._run_agent(
                decision.agent,
                message=message,
                user_id=user_id,
                reference_seed=request_trace_id,
            )
            if decision.secondary_agent is not None:
                secondary = await self._run_agent(
                    decision.secondary_agent,
                    message=message,
                    user_id=user_id,
                    reference_seed=request_trace_id,
                )
                result = _merge_sequence(result, secondary)
        result = attach_handoff_reference(
            result,
            message=message,
            reference_seed=request_trace_id,
        )

        latency_ms = round((perf_counter() - started) * 1000, 2)
        self._events.emit(
            "agent_execution",
            {
                "trace_id": request_trace_id,
                "user_reference_hash": user_reference_hash,
                "agent": result.agent.value,
                "route": result.route.value,
                "latency_ms": latency_ms,
                "tool_calls": result.tool_calls,
                "retrieval_result_count": result.retrieval_result_count,
                "handoff_required": result.handoff_required,
                "handoff_reference": result.handoff_reference,
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

    async def _run_agent(
        self,
        agent: AgentName,
        *,
        message: str,
        user_id: str,
        reference_seed: str,
    ) -> AgentResult:
        if agent is AgentName.KNOWLEDGE:
            return await self._knowledge.handle(message)
        if agent is AgentName.SUPPORT:
            return await self._support.handle(message, user_id)
        return self._escalation.handle(
            reason="Unsupported agent selection.",
            message=message,
            reference_seed=reference_seed,
        )


def _merge_sequence(primary: AgentResult, secondary: AgentResult) -> AgentResult:
    """Combine two agent results into one observable sequence outcome.

    Both contributions remain visible. A handoff raised by either agent takes ownership of the
    outcome so a sequence can never hide an escalation behind a successful partial answer.
    """
    handoff_required = primary.handoff_required or secondary.handoff_required
    return AgentResult(
        answer=f"{primary.answer} {secondary.answer}".strip(),
        agent=AgentName.ESCALATION if handoff_required else primary.agent,
        route=RouteName.AGENT_SEQUENCE,
        sources=(*primary.sources, *secondary.sources),
        handoff_required=handoff_required,
        handoff_reference=primary.handoff_reference or secondary.handoff_reference,
        tool_calls=primary.tool_calls + secondary.tool_calls,
        retrieval_result_count=primary.retrieval_result_count + secondary.retrieval_result_count,
    )
