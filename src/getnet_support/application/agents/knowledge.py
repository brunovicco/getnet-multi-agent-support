"""Grounded Getnet product knowledge and general-information agent."""

from getnet_support.application.agents.router import (
    CURRENT_INFORMATION_SIGNALS,
    GETNET_PRODUCT_SIGNALS,
    phrase_matches,
    tokenize_message,
)
from getnet_support.application.language import detect_language, translate
from getnet_support.application.ports import (
    AnswerGeneratorPort,
    GetnetKnowledgePort,
    WebSearchPort,
)
from getnet_support.domain.models import AgentName, AgentResult, RetrievedChunk, RouteName, Source

# Lexical cosine similarity alone is not a relevance guarantee on a small corpus: an unrelated
# chunk that shares common Portuguese words can outscore any similarity threshold. Similarity is
# therefore only a noise floor here, and coverage below is the actual relevance gate.
MINIMUM_RETRIEVAL_SCORE = 0.08
# Coverage is the share of the question's IDF mass present in the chunk, measured by the retrieval
# adapter. The gate exists because a score threshold alone cannot separate "shares common words"
# from "answers the question": a crediario question once retrieved the antecipacao article above
# the score gate and produced a confident, wrongly-cited answer. The gate itself only has to
# reject near-zero coverage, because selection below is coverage-first; it is deliberately low so
# that a mixed-intent question, whose support words are unanswerable by a product corpus and so
# cap the achievable coverage, still gets a grounded product answer.
MINIMUM_TERM_COVERAGE = 0.20
# A reviewed chunk wins a near-tie against a scraped one, so a page teaser that merely mentions
# the topic does not outrank text that answers it. Both constants are calibration targets for the
# offline dataset (docs/EVALUATION.md).
CURATED_PREFERENCE_RATIO = 0.65
RETRIEVAL_TOP_K = 5


class KnowledgeAgent:
    """Select Getnet RAG or general web search, then require grounding."""

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
        tokens = tokenize_message(message)
        language = detect_language(message, tokens)
        if self._requires_web_search(tokens):
            result = await self._web_search.search(message)
            # The adapter's message is operator-facing (it names the missing configuration). The
            # merchant gets the catalogued equivalent in their own language instead.
            return AgentResult(
                answer=(
                    result.answer
                    if result.available
                    else translate("web_search_unavailable", language)
                ),
                agent=AgentName.KNOWLEDGE,
                route=RouteName.WEB_SEARCH,
                sources=result.sources,
                tool_calls=1,
                retrieval_result_count=len(result.sources) if result.available else 0,
            )

        retrieval = await self._getnet_knowledge.search(message, top_k=RETRIEVAL_TOP_K)
        candidates = tuple(
            match
            for match in retrieval.matches
            if match.score >= MINIMUM_RETRIEVAL_SCORE and match.coverage >= MINIMUM_TERM_COVERAGE
        )
        if not candidates:
            return AgentResult(
                answer=translate("knowledge_insufficient_evidence", language),
                agent=AgentName.ESCALATION,
                route=RouteName.HUMAN_HANDOFF,
                handoff_required=True,
                tool_calls=1,
            )

        # Retrieval stays top-k for observability and evaluation, while generation uses a single
        # chunk: the reviewed corpus keeps one self-contained chunk per product topic, and merging
        # secondary lexical matches only dilutes a focused answer.
        relevant = (select_evidence(candidates),)
        sources = self._unique_sources(relevant)
        evidence = " ".join(match.chunk.text.strip() for match in relevant)
        generated_answer = (
            await self._answer_generator.generate(message, relevant)
            if self._answer_generator is not None
            else None
        )
        fallback = translate("knowledge_grounded_prefix", language, evidence=evidence)
        return AgentResult(
            answer=generated_answer or fallback,
            agent=AgentName.KNOWLEDGE,
            route=RouteName.GETNET_RAG,
            sources=sources,
            tool_calls=2 if self._answer_generator is not None else 1,
            retrieval_result_count=len(relevant),
        )

    @staticmethod
    def _requires_web_search(tokens: tuple[str, ...]) -> bool:
        """Use web search for general questions and time-sensitive Getnet questions."""
        requires_current_information = any(
            phrase_matches(tokens, signal) for signal in CURRENT_INFORMATION_SIGNALS
        )
        references_getnet_product = any(
            phrase_matches(tokens, signal) for signal in GETNET_PRODUCT_SIGNALS
        )
        return requires_current_information or not references_getnet_product

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


def select_evidence(candidates: tuple[RetrievedChunk, ...]) -> RetrievedChunk:
    """Return the chunk used for generation.

    Ranking is by similarity, but selection is by evidence coverage: among chunks that already
    passed both gates, the one that addresses more of the question is the better answer even when
    another chunk is lexically closer. Reviewed evidence wins a near-tie.
    """
    best = max(candidates, key=lambda candidate: (candidate.coverage, candidate.score))
    if best.chunk.curated:
        return best
    for candidate in candidates:
        if (
            candidate.chunk.curated
            and candidate.coverage >= best.coverage * CURATED_PREFERENCE_RATIO
            and candidate.score >= best.score * CURATED_PREFERENCE_RATIO
        ):
            return candidate
    return best
