from pathlib import Path

from fastapi.testclient import TestClient

from getnet_support.adapters.rag.corpus_store import save_corpus
from getnet_support.adapters.settings import Settings
from getnet_support.domain.models import KnowledgeChunk
from getnet_support.entrypoints.http import create_app


def test_root_exposes_service_navigation() -> None:
    with TestClient(create_app(Settings())) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "getnet-multi-agent-support",
        "version": "0.1.0",
        "documentation": "/docs",
        "health": "/health",
        "chat": "/chat",
    }


def test_favicon_does_not_create_a_not_found_error() -> None:
    with TestClient(create_app(Settings())) as client:
        response = client.get("/favicon.ico")

    assert response.status_code == 204
    assert response.content == b""


def test_health_reports_local_capabilities() -> None:
    with TestClient(create_app(Settings())) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "getnet-multi-agent-support",
        "rag": "ready",
        "web_search": "unavailable",
        "answer_generation": "extractive",
        "router": "rules",
    }


def test_health_reports_configured_optional_providers_without_calling_them() -> None:
    settings = Settings(
        web_search_provider="tavily",
        web_search_api_key="test-web-key",
        llm_provider="openai",
        llm_api_key="test-llm-key",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/health")

    assert response.json()["web_search"] == "configured"
    assert response.json()["answer_generation"] == "openai"
    assert response.json()["router"] == "rules"


def test_health_reports_the_opt_in_llm_router() -> None:
    settings = Settings(
        llm_provider="openai",
        llm_api_key="test-llm-key",
        llm_router_enabled=True,
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/health")

    assert response.json()["router"] == "openai+rules"


def test_chat_loads_the_configured_local_corpus(tmp_path: Path) -> None:
    artifact = tmp_path / "custom-corpus.json"
    save_corpus(
        artifact,
        (
            KnowledgeChunk(
                title="Challenge-only Getnet capability",
                source="https://getnet.test/quantum-checkout",
                text=(
                    "Getnet Quantum Checkout is a challenge-only test capability identified by "
                    "the code QX-4242."
                ),
            ),
        ),
    )
    with TestClient(create_app(Settings(getnet_corpus_path=artifact))) as client:
        response = client.post(
            "/chat",
            json={
                "message": "Can Getnet Quantum Checkout use code QX-4242?",
                "user_id": "cliente1988",
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["route"] == "getnet_rag"
    assert "QX-4242" in body["answer"]
    assert body["sources"][0]["url"] == "https://getnet.test/quantum-checkout"


def test_chat_routes_support_request() -> None:
    with TestClient(create_app(Settings())) as client:
        response = client.post(
            "/chat",
            json={
                "message": "My card machine will not connect to the internet",
                "user_id": "cliente1988",
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["agent"] == "support"
    assert body["route"] == "customer_tools"
    assert len(body["trace_id"]) == 32


def test_chat_routes_general_information_to_web_search() -> None:
    with TestClient(create_app(Settings())) as client:
        response = client.post(
            "/chat",
            json={
                "message": "What is the capital of Argentina?",
                "user_id": "cliente1988",
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["agent"] == "knowledge"
    assert body["route"] == "web_search"
    assert "not available" in body["answer"]
    assert "WEB_SEARCH_API_KEY" not in body["answer"]


def test_chat_validates_empty_message() -> None:
    with TestClient(create_app(Settings())) as client:
        response = client.post("/chat", json={"message": "", "user_id": "cliente1988"})

    assert response.status_code == 422
