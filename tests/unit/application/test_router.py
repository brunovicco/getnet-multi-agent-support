import pytest

from getnet_support.application.agents.router import RouterAgent, normalize_text
from getnet_support.domain.models import AgentName


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("What's the difference between the Get Clássica and the Get Smart?", AgentName.KNOWLEDGE),
        ("What's the weather forecast in Porto Alegre tomorrow?", AgentName.KNOWLEDGE),
        ("What's the euro exchange rate today?", AgentName.KNOWLEDGE),
        ("What is the capital of Argentina?", AgentName.KNOWLEDGE),
        ("Who is Ada Lovelace?", AgentName.KNOWLEDGE),
        ("Qual é a capital da Argentina?", AgentName.KNOWLEDGE),
        ("Onde fica Machu Picchu?", AgentName.KNOWLEDGE),
        ("When will the money from yesterday's sales be deposited?", AgentName.SUPPORT),
        ("My card machine won't connect to the internet", AgentName.SUPPORT),
        ("My card machine is showing a transaction decline error.", AgentName.SUPPORT),
        ("Do I need a bank account to receive my sales via Pix?", AgentName.KNOWLEDGE),
        ("How does receivables advance work with Getnet?", AgentName.KNOWLEDGE),
        ("How many installments are available with crediário?", AgentName.KNOWLEDGE),
        ("Can I sell through WhatsApp using the Payment Link?", AgentName.KNOWLEDGE),
        ("Please transfer money from my account", AgentName.ESCALATION),
        ("Write me a poem about orange trees", AgentName.ESCALATION),
    ],
)
def test_router_selects_expected_agent(message: str, expected: AgentName) -> None:
    decision = RouterAgent().route(message)

    assert decision.agent is expected


def test_router_normalizes_accents_and_punctuation() -> None:
    assert normalize_text("Antecipação, CREDIÁRIO!") == "antecipacao crediario"


def test_unknown_route_has_low_confidence() -> None:
    decision = RouterAgent().route("purple elephants")

    assert decision.agent is AgentName.ESCALATION
    assert decision.confidence < 0.60
