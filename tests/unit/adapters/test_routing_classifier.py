"""Contract tests for the optional intent classifier adapter."""

import httpx
import pytest

from getnet_support.adapters.routing.openai_intent_classifier import OpenAIIntentClassifier
from getnet_support.domain.models import AgentName


def _responses_payload(text: str) -> dict[str, object]:
    return {"output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]}


def _client(handler: object, **kwargs: object) -> OpenAIIntentClassifier:
    return OpenAIIntentClassifier(
        api_key="test-key",
        model="test-model",
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        **kwargs,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_valid_structured_output_becomes_a_route_decision() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_responses_payload(
                '{"agent": "support", "reason": "incident", "confidence": 0.9}'
            ),
        )

    decision = await _client(handler).classify("minha maquininha não liga")

    assert decision is not None
    assert decision.agent is AgentName.SUPPORT
    assert decision.confidence == 0.9


@pytest.mark.asyncio
async def test_the_routing_call_requests_the_configured_reasoning_effort() -> None:
    """Classification of one sentence does not need deliberation, and sits on the request path."""
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json=_responses_payload(
                '{"agent": "knowledge", "reason": "product", "confidence": 0.8}'
            ),
        )

    await _client(handler, reasoning_effort="none").classify("o que é o Get Tap?")

    assert captured["reasoning"] == {"effort": "none"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "handler_result",
    [
        httpx.Response(500),
        httpx.Response(200, json={"output": []}),
        httpx.Response(200, json=_responses_payload("not json at all")),
        httpx.Response(200, json=_responses_payload('{"agent": "invented", "confidence": 1}')),
    ],
)
async def test_every_provider_failure_degrades_to_none(handler_result: httpx.Response) -> None:
    decision = await _client(lambda request: handler_result).classify("qualquer coisa")

    assert decision is None


@pytest.mark.asyncio
async def test_a_timeout_degrades_to_none_within_the_budget() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    assert await _client(handler, timeout_seconds=0.5).classify("qualquer coisa") is None
