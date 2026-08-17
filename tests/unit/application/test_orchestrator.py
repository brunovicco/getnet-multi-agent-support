from collections.abc import Mapping

import pytest

from getnet_support.adapters.rag.corpus import DEFAULT_GETNET_CORPUS
from getnet_support.adapters.rag.retriever import LocalTfidfRetriever
from getnet_support.adapters.repositories.fake_customer_repository import FakeCustomerRepository
from getnet_support.adapters.tools.customer import CustomerProfileTool
from getnet_support.adapters.tools.terminal import TerminalStatusTool
from getnet_support.adapters.tools.transactions import RecentTransactionsTool
from getnet_support.adapters.tools.web_search import WebSearchTool
from getnet_support.application.agents.customer_support import CustomerSupportAgent
from getnet_support.application.agents.escalation import EscalationAgent
from getnet_support.application.agents.knowledge import KnowledgeAgent
from getnet_support.application.agents.router import RouterAgent
from getnet_support.application.orchestrator import SupportOrchestrator, _merge_sequence
from getnet_support.domain.models import AgentName, AgentResult, RouteName


class RecordingEvents:
    def __init__(self) -> None:
        self.events: list[tuple[str, Mapping[str, object]]] = []

    def emit(self, event: str, fields: Mapping[str, object]) -> None:
        self.events.append((event, fields))


def build_orchestrator(events: RecordingEvents) -> SupportOrchestrator:
    repository = FakeCustomerRepository()
    return SupportOrchestrator(
        router=RouterAgent(),
        knowledge=KnowledgeAgent(LocalTfidfRetriever(DEFAULT_GETNET_CORPUS), WebSearchTool()),
        support=CustomerSupportAgent(
            CustomerProfileTool(repository),
            RecentTransactionsTool(repository),
            TerminalStatusTool(repository),
        ),
        escalation=EscalationAgent(),
        events=events,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "agent", "route"),
    [
        (
            "How does receivables advance work with Getnet?",
            AgentName.KNOWLEDGE,
            RouteName.GETNET_RAG,
        ),
        (
            "My card machine won't connect to the internet",
            AgentName.SUPPORT,
            RouteName.CUSTOMER_TOOLS,
        ),
        ("What is the capital of Argentina?", AgentName.KNOWLEDGE, RouteName.WEB_SEARCH),
        ("Tell me a secret", AgentName.ESCALATION, RouteName.HUMAN_HANDOFF),
    ],
)
async def test_orchestration_paths(message: str, agent: AgentName, route: RouteName) -> None:
    events = RecordingEvents()

    result = await build_orchestrator(events).chat(
        message=message,
        user_id="cliente1988",
        trace_id="trace-123",
    )

    assert result.agent is agent
    assert result.route is route
    assert result.trace_id == "trace-123"
    assert [event for event, _ in events.events] == ["router_decision", "agent_execution"]
    event_fields = [fields for _, fields in events.events]
    assert all("user_id" not in fields for fields in event_fields)
    references = {fields["user_reference_hash"] for fields in event_fields}
    assert len(references) == 1
    reference = next(iter(references))
    assert isinstance(reference, str)
    assert reference.startswith("usr_")
    assert all("cliente1988" not in str(fields) for fields in event_fields)


@pytest.mark.asyncio
async def test_incident_with_a_product_topic_runs_an_agent_sequence() -> None:
    """REQ-R6: both agents contribute and the route is observable as a sequence."""
    events = RecordingEvents()

    result = await build_orchestrator(events).chat(
        message="Minha maquininha não conecta e como funciona a antecipação?",
        user_id="cliente1988",
    )

    assert result.route is RouteName.AGENT_SEQUENCE
    assert "GET-12345" in result.answer
    assert "antecipa" in result.answer.lower()
    router_event = next(fields for event, fields in events.events if event == "router_decision")
    assert router_event["secondary_agent"] is not None


@pytest.mark.asyncio
async def test_agent_sequence_preserves_an_unknown_customer_handoff() -> None:
    """REQ-R6, REQ-S3: a successful product answer must not hide a support handoff."""
    events = RecordingEvents()

    result = await build_orchestrator(events).chat(
        message="Minha maquininha não conecta e como funciona a antecipação?",
        user_id="desconhecido999",
        trace_id="mixed-intent-trace",
    )

    assert result.agent is AgentName.ESCALATION
    assert result.route is RouteName.AGENT_SEQUENCE
    assert result.handoff_required is True
    assert "Nenhum cliente foi encontrado" in result.answer
    assert "HO-" in result.answer
    execution = next(fields for event, fields in events.events if event == "agent_execution")
    assert execution["handoff_required"] is True
    reference = execution["handoff_reference"]
    assert isinstance(reference, str)
    assert reference in result.answer


@pytest.mark.parametrize(
    ("primary_handoff", "secondary_handoff"),
    [(True, False), (False, True), (True, True)],
)
def test_sequence_merge_preserves_every_handoff_combination(
    primary_handoff: bool,
    secondary_handoff: bool,
) -> None:
    primary = AgentResult(
        answer="primary",
        agent=AgentName.ESCALATION if primary_handoff else AgentName.KNOWLEDGE,
        route=RouteName.HUMAN_HANDOFF if primary_handoff else RouteName.GETNET_RAG,
        handoff_required=primary_handoff,
        tool_calls=1,
        retrieval_result_count=1,
    )
    secondary = AgentResult(
        answer="secondary",
        agent=AgentName.ESCALATION if secondary_handoff else AgentName.SUPPORT,
        route=RouteName.HUMAN_HANDOFF if secondary_handoff else RouteName.CUSTOMER_TOOLS,
        handoff_required=secondary_handoff,
        tool_calls=2,
    )

    result = _merge_sequence(primary, secondary)

    assert result.agent is AgentName.ESCALATION
    assert result.route is RouteName.AGENT_SEQUENCE
    assert result.handoff_required is True
    assert result.answer == "primary secondary"
    assert result.tool_calls == 3
    assert result.retrieval_result_count == 1


@pytest.mark.asyncio
async def test_escalation_carries_a_handoff_reference_in_the_user_language() -> None:
    """REQ-E1, REQ-L1: the handoff is correlatable and written in Portuguese."""
    result = await build_orchestrator(RecordingEvents()).chat(
        message="Quero transferir dinheiro da minha conta",
        user_id="cliente1988",
    )

    assert result.handoff_required is True
    assert result.route is RouteName.HUMAN_HANDOFF
    assert "HO-" in result.answer
    assert "especialista humano" in result.answer


@pytest.mark.asyncio
async def test_unknown_customer_is_handed_off_without_disclosure() -> None:
    """REQ-S3: an unknown identifier reveals nothing about any customer."""
    result = await build_orchestrator(RecordingEvents()).chat(
        message="minha maquininha não conecta",
        user_id="desconhecido999",
    )

    assert result.handoff_required is True
    assert "GET-12345" not in result.answer
    assert "HO-" in result.answer


@pytest.mark.asyncio
async def test_handoff_reference_is_stable_per_request_and_unique_between_requests() -> None:
    orchestrator = build_orchestrator(RecordingEvents())

    first = await orchestrator.chat(
        message="Quero transferir dinheiro da minha conta",
        user_id="cliente1988",
        trace_id="request-one",
    )
    repeated = await orchestrator.chat(
        message="Quero transferir dinheiro da minha conta",
        user_id="cliente1988",
        trace_id="request-one",
    )
    second = await orchestrator.chat(
        message="Quero transferir dinheiro da minha conta",
        user_id="cliente1988",
        trace_id="request-two",
    )

    first_reference = first.answer.split("HO-", maxsplit=1)[1][:8]
    repeated_reference = repeated.answer.split("HO-", maxsplit=1)[1][:8]
    second_reference = second.answer.split("HO-", maxsplit=1)[1][:8]
    assert first_reference == repeated_reference
    assert first_reference != second_reference


@pytest.mark.asyncio
async def test_router_event_carries_decision_provenance() -> None:
    """REQ-O1: a disabled classifier and a broken one must not look identical in the logs."""
    events = RecordingEvents()

    await build_orchestrator(events).chat(
        message="minha maquininha não conecta", user_id="cliente1988"
    )

    fields = next(fields for event, fields in events.events if event == "router_decision")
    assert fields["decision_source"] == "rules"
    assert fields["classifier_latency_ms"] is None
