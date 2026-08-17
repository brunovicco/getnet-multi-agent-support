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
from getnet_support.application.orchestrator import SupportOrchestrator
from getnet_support.domain.models import AgentName, RouteName


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
