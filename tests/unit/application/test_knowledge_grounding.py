"""REQ-K1, REQ-K2: an answer is produced only when the evidence actually addresses the question."""

import pytest

from getnet_support.adapters.rag.corpus import DEFAULT_GETNET_CORPUS
from getnet_support.adapters.rag.retriever import LocalTfidfRetriever
from getnet_support.adapters.tools.web_search import WebSearchTool
from getnet_support.application.agents.knowledge import KnowledgeAgent
from getnet_support.domain.models import (
    AgentName,
    KnowledgeChunk,
    RetrievalResult,
    RetrievedChunk,
    RouteName,
)

OFF_TOPIC_CHUNK = KnowledgeChunk(
    title="Getnet receivables advance",
    source="https://site.getnet.com.br/quando-vale-a-pena-antecipar-as-suas-vendas-no-cartao/",
    text=(
        "A antecipação de recebíveis permite receber antes da data de liquidação as vendas no "
        "crédito já concluídas, mediante uma taxa cobrada pela operação."
    ),
)


class StubRetriever:
    """Return a fixed, deliberately off-topic match above the score gate."""

    def __init__(self, score: float) -> None:
        self.score = score

    async def search(self, query: str, *, top_k: int = 3) -> RetrievalResult:
        return RetrievalResult(matches=(RetrievedChunk(chunk=OFF_TOPIC_CHUNK, score=self.score),))


def build_agent(retriever: object) -> KnowledgeAgent:
    return KnowledgeAgent(retriever, WebSearchTool())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_lexically_similar_but_off_topic_evidence_is_rejected() -> None:
    agent = build_agent(StubRetriever(score=0.42))

    result = await agent.handle("Em quantas parcelas posso dividir uma venda no crediário?")

    assert result.agent is AgentName.ESCALATION
    assert result.route is RouteName.HUMAN_HANDOFF
    assert result.handoff_required is True
    assert result.sources == ()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "expected_term"),
    [
        ("Em quantas parcelas posso dividir uma venda no crediário?", "Crediário"),
        ("How many installments can I split a sale into with the crediário?", "Crediário"),
        ("Qual a diferença entre a Get Clássica e a Get Smart?", "Get Smart"),
        ("What's the difference between the Get Clássica and the Get Smart?", "Get Smart"),
        ("Posso vender pelo WhatsApp usando o Link de Pagamento?", "WhatsApp"),
        ("Preciso de conta bancária para receber minhas vendas via Pix?", "Pix"),
    ],
)
async def test_challenge_questions_are_answered_from_the_matching_topic(
    question: str, expected_term: str
) -> None:
    agent = build_agent(LocalTfidfRetriever(DEFAULT_GETNET_CORPUS))

    result = await agent.handle(question)

    assert result.route is RouteName.GETNET_RAG
    assert expected_term in result.answer
    assert result.sources


@pytest.mark.asyncio
async def test_portuguese_questions_are_answered_in_portuguese() -> None:
    agent = build_agent(LocalTfidfRetriever(DEFAULT_GETNET_CORPUS))

    result = await agent.handle("Qual a diferença entre a Get Clássica e a Get Smart?")

    assert result.answer.startswith("Com base nas fontes indexadas da Getnet")
