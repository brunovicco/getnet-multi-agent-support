import pytest

from getnet_support.adapters.rag.corpus import DEFAULT_GETNET_CORPUS
from getnet_support.adapters.rag.retriever import LocalTfidfRetriever
from getnet_support.adapters.repositories.fake_customer_repository import FakeCustomerRepository
from getnet_support.adapters.tools.customer import CustomerProfileTool
from getnet_support.adapters.tools.terminal import TerminalStatusTool
from getnet_support.adapters.tools.transactions import RecentTransactionsTool
from getnet_support.adapters.tools.web_search import WebSearchTool
from getnet_support.application.agents.customer_support import CustomerSupportAgent
from getnet_support.application.agents.knowledge import KnowledgeAgent
from getnet_support.domain.models import AgentName, RouteName


def build_support_agent() -> CustomerSupportAgent:
    repository = FakeCustomerRepository()
    return CustomerSupportAgent(
        CustomerProfileTool(repository),
        RecentTransactionsTool(repository),
        TerminalStatusTool(repository),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "source_title"),
    [
        (
            "What's the difference between the Get Clássica and the Get Smart?",
            "Getnet physical products",
        ),
        ("Do I need a bank account to receive my sales via Pix?", "Pix with Getnet"),
        ("How does receivables advance work with Getnet?", "Getnet receivables advance"),
        ("How many installments are available with crediário?", "Crediário Getnet manual"),
        ("Can I sell through WhatsApp using the Payment Link?", "Getnet Payment Link"),
    ],
)
async def test_knowledge_agent_uses_getnet_rag_with_sources(
    message: str, source_title: str
) -> None:
    agent = KnowledgeAgent(LocalTfidfRetriever(DEFAULT_GETNET_CORPUS), WebSearchTool())

    result = await agent.handle(message)

    assert result.agent is AgentName.KNOWLEDGE
    assert result.route is RouteName.GETNET_RAG
    assert len(result.sources) == 1
    assert result.sources[0].title == source_title


@pytest.mark.asyncio
async def test_knowledge_agent_degrades_without_web_provider() -> None:
    agent = KnowledgeAgent(LocalTfidfRetriever(DEFAULT_GETNET_CORPUS), WebSearchTool())

    result = await agent.handle("What's the euro exchange rate today?")

    assert result.route is RouteName.WEB_SEARCH
    assert result.sources == ()
    assert "requires a configured" in result.answer


@pytest.mark.asyncio
async def test_support_agent_combines_transaction_tools() -> None:
    result = await build_support_agent().handle(
        "When will yesterday's sales be deposited?", "cliente1988"
    )

    assert result.agent is AgentName.SUPPORT
    assert result.route is RouteName.CUSTOMER_TOOLS
    assert "2026-08-18" in result.answer
    assert result.tool_calls == 2


@pytest.mark.asyncio
async def test_support_agent_combines_terminal_tools() -> None:
    result = await build_support_agent().handle(
        "My card machine won't connect to the internet", "cliente1988"
    )

    assert result.agent is AgentName.SUPPORT
    assert "GET-12345" in result.answer
    assert "disconnected" in result.answer


@pytest.mark.asyncio
async def test_support_agent_escalates_unknown_customer() -> None:
    result = await build_support_agent().handle("My card machine is offline", "missing")

    assert result.agent is AgentName.ESCALATION
    assert result.handoff_required is True
