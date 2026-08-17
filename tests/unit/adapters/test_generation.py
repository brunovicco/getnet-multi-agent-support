import json

import httpx
import pytest

from getnet_support.adapters.generation import GROUNDING_INSTRUCTIONS, OpenAIResponsesGenerator
from getnet_support.domain.models import KnowledgeChunk, RetrievedChunk


def evidence() -> tuple[RetrievedChunk, ...]:
    return (
        RetrievedChunk(
            chunk=KnowledgeChunk(
                text="Payment Link can be shared through WhatsApp.",
                source="https://getnet.test/payment-link",
                title="Payment Link",
            ),
            score=0.9,
        ),
    )


@pytest.mark.asyncio
async def test_openai_generator_sends_grounded_responses_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url == "https://openai.test/v1/responses"
        assert request.headers["Authorization"] == "Bearer test-key"
        assert body["model"] == "test-model"
        assert body["instructions"] == GROUNDING_INSTRUCTIONS
        assert "Payment Link can be shared" in body["input"]
        assert body["store"] is False
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "Yes. The Payment Link can be shared through WhatsApp.",
                            }
                        ],
                    }
                ]
            },
        )

    generator = OpenAIResponsesGenerator(
        api_key="test-key",
        model="test-model",
        base_url="https://openai.test",
        transport=httpx.MockTransport(handler),
    )

    answer = await generator.generate("Can I sell through WhatsApp?", evidence())

    assert answer == "Yes. The Payment Link can be shared through WhatsApp."


@pytest.mark.asyncio
async def test_openai_generator_degrades_on_provider_failure() -> None:
    generator = OpenAIResponsesGenerator(
        api_key="test-key",
        model="test-model",
        transport=httpx.MockTransport(lambda _: httpx.Response(503)),
    )

    assert await generator.generate("Question", evidence()) is None
