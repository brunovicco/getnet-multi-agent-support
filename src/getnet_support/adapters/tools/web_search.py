"""Credential-free safe fallback for current external information."""

from getnet_support.domain.models import WebSearchResult


class WebSearchTool:
    """Represent a production web-search integration without fabricating results."""

    def __init__(self, *, provider: str = "", api_key: str = "") -> None:
        """Capture provider configuration without making a network call."""
        self._provider = provider.strip()
        self._configured = bool(self._provider and api_key.strip())

    async def search(self, query: str) -> WebSearchResult:
        """Return an explicit fallback until a supported provider adapter is configured."""
        del query
        if self._configured:
            message = (
                f"The configured web search provider '{self._provider}' has no adapter in this "
                "challenge build. Add a provider implementation before using current results."
            )
        else:
            message = (
                "Current external information requires a configured web search provider. "
                "No current result was invented."
            )
        return WebSearchResult(answer=message, sources=(), available=False)
