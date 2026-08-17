from fastapi.testclient import TestClient

from getnet_support.adapters.settings import Settings
from getnet_support.entrypoints.http import create_app


def test_health_reports_local_capabilities() -> None:
    with TestClient(create_app(Settings())) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "getnet-multi-agent-support",
        "rag": "ready",
        "web_search": "unavailable",
    }


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


def test_chat_validates_empty_message() -> None:
    with TestClient(create_app(Settings())) as client:
        response = client.post("/chat", json={"message": "", "user_id": "cliente1988"})

    assert response.status_code == 422
