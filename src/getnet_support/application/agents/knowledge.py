"""Grounded product knowledge and current-information agent."""

from getnet_support.application.agents.router import normalize_text
from getnet_support.application.ports import (
    AnswerGeneratorPort,
    GetnetKnowledgePort,
    WebSearchPort,
)
from getnet_support.domain.models import AgentName, AgentResult, RetrievedChunk, RouteName, Source

CURRENT_INFORMATION_SIGNALS = (
    "weather",
    "forecast",
    "exchange rate",
    "cotacao",
    "previsao do tempo",
    "today",
    "tomorrow",
    "hoje",
    "amanha",
)
MINIMUM_RETRIEVAL_SCORE = 0.08


class KnowledgeAgent:
    """Select Getnet RAG or current web search, then require grounding."""

    def __init__(
        self,
        getnet_knowledge: GetnetKnowledgePort,
        web_search: WebSearchPort,
        answer_generator: AnswerGeneratorPort | None = None,
    ) -> None:
        """Inject retrieval, web search, and optional answer generation capabilities."""
        self._getnet_knowledge = getnet_knowledge
        self._web_search = web_search
        self._answer_generator = answer_generator

    async def handle(self, message: str) -> AgentResult:
        """Answer from evidence or safely request human help."""
        if self._requires_current_information(message):
            result = await self._web_search.search(message)
            if not result.available:
                return AgentResult(
                    answer=result.answer,
                    agent=AgentName.KNOWLEDGE,
                    route=RouteName.WEB_SEARCH,
                    sources=result.sources,
                    tool_calls=1,
                )
            return AgentResult(
                answer=result.answer,
                agent=AgentName.KNOWLEDGE,
                route=RouteName.WEB_SEARCH,
                sources=result.sources,
                tool_calls=1,
                retrieval_result_count=len(result.sources),
            )

        retrieval = await self._getnet_knowledge.search(message, top_k=3)
        candidates = tuple(
            match for match in retrieval.matches if match.score >= MINIMUM_RETRIEVAL_SCORE
        )
        if not candidates:
            return AgentResult(
                answer=(
                    "The Getnet knowledge base does not contain enough evidence to answer this "
                    "request. Human support is recommended."
                ),
                agent=AgentName.ESCALATION,
                route=RouteName.HUMAN_HANDOFF,
                handoff_required=True,
                tool_calls=1,
            )

        # The tiny offline corpus keeps one self-contained chunk per product topic. Retrieval is
        # top-k for observability/evaluation, while generation uses the strongest chunk to avoid
        # diluting a focused answer with merely lexical secondary matches.
        relevant = candidates[:1]
        sources = self._unique_sources(relevant)
        evidence = " ".join(match.chunk.text.strip() for match in relevant)
        generated_answer = (
            await self._answer_generator.generate(message, relevant)
            if self._answer_generator is not None
            else None
        )
        return AgentResult(
            answer=generated_answer or f"Based on the indexed Getnet sources: {evidence}",
            agent=AgentName.KNOWLEDGE,
            route=RouteName.GETNET_RAG,
            sources=sources,
            tool_calls=2 if self._answer_generator is not None else 1,
            retrieval_result_count=len(relevant),
        )

    @staticmethod
    def _requires_current_information(message: str) -> bool:
        normalized = normalize_text(message)
        padded = f" {normalized} "
        return any(
            f" {normalize_text(signal)} " in padded for signal in CURRENT_INFORMATION_SIGNALS
        )

    @staticmethod
    def _unique_sources(matches: tuple[RetrievedChunk, ...]) -> tuple[Source, ...]:
        sources: list[Source] = []
        seen: set[str] = set()
        for match in matches:
            chunk = match.chunk
            if chunk.source not in seen:
                seen.add(chunk.source)
                sources.append(Source(title=chunk.title, url=chunk.source))
        return tuple(sources)
