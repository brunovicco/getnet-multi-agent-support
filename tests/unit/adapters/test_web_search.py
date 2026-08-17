import json

import httpx
import pytest

from getnet_support.adapters.tools.web_search import WebSearchTool


@pytest.mark.asyncio
async def test_tavily_search_returns_answer_and_sources() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url == "https://tavily.test/search"
        assert request.headers["Authorization"] == "Bearer tvly-test"
        assert body["include_answer"] == "basic"
        assert body["query"] == "weather Porto Alegre tomorrow"
        return httpx.Response(
            200,
            json={
                "answer": "Tomorrow is expected to be mild.",
                "results": [
                    {
                        "title": "Forecast source",
                        "url": "https://weather.test/forecast",
                        "content": "A mild forecast.",
                    }
                ],
            },
        )

    tool = WebSearchTool(
        provider="tavily",
        api_key="tvly-test",
        base_url="https://tavily.test",
        transport=httpx.MockTransport(handler),
    )

    result = await tool.search("weather Porto Alegre tomorrow")

    assert result.available is True
    assert result.answer == "Tomorrow is expected to be mild."
    assert result.sources[0].url == "https://weather.test/forecast"


@pytest.mark.asyncio
async def test_tavily_search_degrades_on_provider_failure() -> None:
    tool = WebSearchTool(
        provider="tavily",
        api_key="tvly-test",
        transport=httpx.MockTransport(lambda _: httpx.Response(503)),
    )

    result = await tool.search("current query")

    assert result.available is False
    assert result.sources == ()
    assert "could not complete" in result.answer


@pytest.mark.asyncio
async def test_unknown_web_provider_is_rejected_without_network() -> None:
    result = await WebSearchTool(provider="unknown", api_key="key").search("query")

    assert result.available is False
    assert "not supported" in result.answer
