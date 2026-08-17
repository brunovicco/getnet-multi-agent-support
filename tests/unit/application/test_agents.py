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
from getnet_support.domain.models import (
    AgentName,
    RetrievedChunk,
    RouteName,
    Source,
    WebSearchResult,
)


class StubAnswerGenerator:
    def __init__(self, answer: str | None) -> None:
        self._answer = answer

    async def generate(self, query: str, evidence: tuple[RetrievedChunk, ...]) -> str | None:
        assert query
        assert evidence
        return self._answer


class StubWebSearch:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(self, query: str) -> WebSearchResult:
        self.queries.append(query)
        return WebSearchResult(
            answer="Grounded web answer.",
            sources=(Source(title="Reference", url="https://example.test/argentina"),),
            available=True,
        )


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
    # The merchant sees a plain unavailable notice, never provider configuration details.
    assert "not available" in result.answer
    assert "WEB_SEARCH_API_KEY" not in result.answer


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message",
    [
        "What is the capital of Argentina?",
        "Qual é a capital da Argentina?",
        "What is Getnet's stock price today?",
    ],
)
async def test_knowledge_agent_uses_web_for_general_or_current_questions(
    message: str,
) -> None:
    web_search = StubWebSearch()
    agent = KnowledgeAgent(LocalTfidfRetriever(DEFAULT_GETNET_CORPUS), web_search)

    result = await agent.handle(message)

    assert result.agent is AgentName.KNOWLEDGE
    assert result.route is RouteName.WEB_SEARCH
    assert result.answer == "Grounded web answer."
    assert result.sources[0].url == "https://example.test/argentina"
    assert web_search.queries == [message]


@pytest.mark.asyncio
async def test_knowledge_agent_uses_optional_grounded_generator() -> None:
    agent = KnowledgeAgent(
        LocalTfidfRetriever(DEFAULT_GETNET_CORPUS),
        WebSearchTool(),
        StubAnswerGenerator("A generated answer based only on the retrieved evidence."),
    )

    result = await agent.handle("Can I share a Getnet Payment Link through WhatsApp?")

    assert result.answer == "A generated answer based only on the retrieved evidence."
    assert result.sources[0].title == "Getnet Payment Link"
    assert result.tool_calls == 2


@pytest.mark.asyncio
async def test_knowledge_agent_keeps_extractive_fallback_when_generation_fails() -> None:
    agent = KnowledgeAgent(
        LocalTfidfRetriever(DEFAULT_GETNET_CORPUS),
        WebSearchTool(),
        StubAnswerGenerator(None),
    )

    result = await agent.handle("Can I share a Getnet Payment Link through WhatsApp?")

    assert result.answer.startswith("Based on the indexed Getnet sources:")
    assert result.sources[0].title == "Getnet Payment Link"
    assert result.tool_calls == 2


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
async def test_support_agent_localizes_transaction_states_in_portuguese() -> None:
    result = await build_support_agent().handle(
        "Qual o status da minha última venda e da liquidação?", "cliente1988"
    )

    assert "cadastro do cliente: ativo" in result.answer
    assert "venda mais recente está aprovada" in result.answer
    assert "liquidação está agendada" in result.answer
    assert all(value not in result.answer for value in ("active", "approved", "scheduled"))


@pytest.mark.asyncio
async def test_support_agent_combines_terminal_tools() -> None:
    result = await build_support_agent().handle(
        "My card machine won't connect to the internet", "cliente1988"
    )

    assert result.agent is AgentName.SUPPORT
    assert "GET-12345" in result.answer
    assert "disconnected" in result.answer


@pytest.mark.asyncio
async def test_support_agent_localizes_terminal_states_in_portuguese() -> None:
    result = await build_support_agent().handle(
        "Minha maquininha não conecta na internet", "cliente1988"
    )

    assert "conectividade do terminal GET-12345 está desconectada" in result.answer
    assert "sessão de dados móveis está sem conexão" in result.answer
    assert "disconnected" not in result.answer
    assert "mobile data session" not in result.answer


@pytest.mark.asyncio
async def test_support_agent_escalates_unknown_customer() -> None:
    result = await build_support_agent().handle("My card machine is offline", "missing")

    assert result.agent is AgentName.ESCALATION
    assert result.handoff_required is True
