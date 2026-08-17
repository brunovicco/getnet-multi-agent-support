"""Tavily web search adapter with a credential-free safe fallback."""

import httpx
from pydantic import BaseModel, Field, ValidationError

from getnet_support.domain.models import Source, WebSearchResult


class _TavilyResult(BaseModel):
    """Validated subset of one Tavily search result."""

    title: str
    url: str
    content: str = ""


class _TavilyPayload(BaseModel):
    """Validated subset of the Tavily search response."""

    answer: str | None = None
    results: list[_TavilyResult] = Field(default_factory=list)


class WebSearchTool:
    """Search Tavily when configured and never fabricate current information."""

    def __init__(
        self,
        *,
        provider: str = "",
        api_key: str = "",
        base_url: str = "https://api.tavily.com",
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Capture provider configuration without making a startup network call."""
        self._provider = provider.strip().casefold()
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def search(self, query: str) -> WebSearchResult:
        """Return Tavily-grounded current information or a controlled unavailable result."""
        if not self._provider or not self._api_key:
            return self._unavailable(
                "Current external information requires a configured provider: set "
                "WEB_SEARCH_PROVIDER=tavily and WEB_SEARCH_API_KEY. No current result was "
                "invented."
            )
        if self._provider != "tavily":
            return self._unavailable(
                f"The configured web search provider '{self._provider}' is not supported."
            )

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    f"{self._base_url}/search",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "search_depth": "basic",
                        "max_results": 3,
                        "topic": "general",
                        "include_answer": "basic",
                        "include_raw_content": False,
                        "include_images": False,
                    },
                )
                response.raise_for_status()
                payload = _TavilyPayload.model_validate(response.json())
        except (httpx.HTTPError, ValidationError, ValueError):
            return self._unavailable(
                "The configured web search provider could not complete the request. "
                "No current result was invented."
            )

        sources = self._unique_sources(payload.results)
        answer = (payload.answer or "").strip()
        if not answer and payload.results:
            answer = payload.results[0].content.strip()
        if not answer or not sources:
            return self._unavailable(
                "The web search provider returned no grounded result for this request."
            )
        return WebSearchResult(answer=answer, sources=sources, available=True)

    @staticmethod
    def _unique_sources(results: list[_TavilyResult]) -> tuple[Source, ...]:
        sources: list[Source] = []
        seen: set[str] = set()
        for result in results:
            if result.url in seen or not result.url.strip():
                continue
            seen.add(result.url)
            sources.append(Source(title=result.title.strip() or result.url, url=result.url))
        return tuple(sources)

    @staticmethod
    def _unavailable(answer: str) -> WebSearchResult:
        return WebSearchResult(answer=answer, sources=(), available=False)
