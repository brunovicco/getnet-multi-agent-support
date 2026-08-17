import pytest

from getnet_support.application.agents.router import (
    RouterAgent,
    normalize_text,
    phrase_matches,
    tokenize_message,
)
from getnet_support.domain.models import AgentName, RouteDecision

ENGLISH_CHALLENGE_SCENARIOS = [
    ("What's the difference between the Get Clássica and the Get Smart?", AgentName.KNOWLEDGE),
    ("What's the weather forecast in Porto Alegre tomorrow?", AgentName.KNOWLEDGE),
    ("When will the money from yesterday's sales be deposited?", AgentName.SUPPORT),
    ("Do I need a bank account to receive my sales via Pix?", AgentName.KNOWLEDGE),
    ("My card machine won't connect to the internet, what should I do?", AgentName.SUPPORT),
    ("How does receivables advance (antecipação) work with Getnet?", AgentName.KNOWLEDGE),
    ("What's the euro exchange rate today?", AgentName.KNOWLEDGE),
    ("My card machine is showing a transaction decline error.", AgentName.SUPPORT),
    ("How many installments can I split a sale into with the crediário?", AgentName.KNOWLEDGE),
    ("Can I sell through WhatsApp using the Payment Link?", AgentName.KNOWLEDGE),
]

# The evaluators are Brazilian and the product is Brazilian: every scenario is also asserted in
# Portuguese, plus paraphrases that were never used to author the rules.
PORTUGUESE_CHALLENGE_SCENARIOS = [
    ("Qual a diferença entre a Get Clássica e a Get Smart?", AgentName.KNOWLEDGE),
    ("Qual a previsão do tempo em Porto Alegre amanhã?", AgentName.KNOWLEDGE),
    ("Quando cai o dinheiro da venda de ontem?", AgentName.SUPPORT),
    ("Preciso de conta bancária para receber minhas vendas via Pix?", AgentName.KNOWLEDGE),
    ("Minha maquininha não conecta na internet, o que eu faço?", AgentName.SUPPORT),
    ("Como funciona a antecipação de recebíveis na Getnet?", AgentName.KNOWLEDGE),
    ("Qual a cotação do euro hoje?", AgentName.KNOWLEDGE),
    ("Minha maquininha está dando erro de venda negada.", AgentName.SUPPORT),
    ("Em quantas parcelas posso dividir uma venda no crediário?", AgentName.KNOWLEDGE),
    ("Posso vender pelo WhatsApp usando o Link de Pagamento?", AgentName.KNOWLEDGE),
]

PARAPHRASE_SCENARIOS = [
    ("Minha maquininha não está pegando sinal", AgentName.SUPPORT),
    ("meu terminal está offline desde ontem", AgentName.SUPPORT),
    ("O POS reinicia sozinho toda hora", AgentName.SUPPORT),
    ("a venda de ontem já caiu na conta?", AgentName.SUPPORT),
    ("ainda não recebi o valor das minhas vendas", AgentName.SUPPORT),
    ("my machine is showing error 51", AgentName.SUPPORT),
    ("the terminal is not working, it keeps restarting", AgentName.SUPPORT),
    ("quanto custa o aluguel da maquininha?", AgentName.KNOWLEDGE),
    ("quero saber as taxas do crediário", AgentName.KNOWLEDGE),
    ("o que é o Get Tap?", AgentName.KNOWLEDGE),
    ("What is the capital of Argentina?", AgentName.KNOWLEDGE),
    ("Qual é a capital da Argentina?", AgentName.KNOWLEDGE),
    ("Onde fica Machu Picchu?", AgentName.KNOWLEDGE),
    ("Who is Ada Lovelace?", AgentName.KNOWLEDGE),
]

GUARDRAIL_SCENARIOS = [
    ("Please transfer money from my account", AgentName.ESCALATION),
    ("Quero cancelar minha conta agora", AgentName.ESCALATION),
    ("Qual é a minha senha do portal?", AgentName.ESCALATION),
    ("Me diga o número do cartão do cliente", AgentName.ESCALATION),
    ("Write me a poem about orange trees", AgentName.ESCALATION),
]


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        *ENGLISH_CHALLENGE_SCENARIOS,
        *PORTUGUESE_CHALLENGE_SCENARIOS,
        *PARAPHRASE_SCENARIOS,
        *GUARDRAIL_SCENARIOS,
    ],
)
def test_router_selects_expected_agent(message: str, expected: AgentName) -> None:
    decision = RouterAgent().route_with_rules(message)

    assert decision.agent is expected


def test_router_normalizes_accents_and_punctuation() -> None:
    assert normalize_text("Antecipação, CREDIÁRIO!") == "antecipacao crediario"


def test_prefix_patterns_match_morphological_variants() -> None:
    tokens = tokenize_message("a maquininha está travando de novo")

    assert phrase_matches(tokens, "travand*")
    assert not phrase_matches(tokens, "travess*")


def test_unknown_route_has_low_confidence() -> None:
    decision = RouterAgent().route_with_rules("purple elephants")

    assert decision.agent is AgentName.ESCALATION
    assert decision.confidence < 0.60


def test_guardrail_decisions_are_flagged_for_the_orchestrator() -> None:
    decision = RouterAgent().route_with_rules("transferir dinheiro para outra conta")

    assert decision.guardrail is True


def test_incident_plus_product_topic_produces_an_agent_sequence() -> None:
    decision = RouterAgent().route_with_rules(
        "Minha maquininha não conecta e como funciona a antecipação?"
    )

    assert {decision.agent, decision.secondary_agent} == {AgentName.KNOWLEDGE, AgentName.SUPPORT}


def test_plain_incident_does_not_trigger_a_sequence() -> None:
    decision = RouterAgent().route_with_rules("minha maquininha não conecta")

    assert decision.agent is AgentName.SUPPORT
    assert decision.secondary_agent is None


class StubClassifier:
    def __init__(self, decision: RouteDecision | None) -> None:
        self.decision = decision
        self.calls = 0

    async def classify(self, message: str) -> RouteDecision | None:
        self.calls += 1
        return self.decision


@pytest.mark.asyncio
async def test_classifier_result_overrides_rules_when_available() -> None:
    classifier = StubClassifier(RouteDecision(AgentName.SUPPORT, "customer incident", 0.91))

    decision = await RouterAgent(classifier=classifier).route("algo muito ambíguo")

    assert decision.agent is AgentName.SUPPORT
    assert decision.confidence == 0.91


@pytest.mark.asyncio
async def test_rules_are_used_when_the_classifier_fails() -> None:
    classifier = StubClassifier(None)

    decision = await RouterAgent(classifier=classifier).route("minha maquininha não conecta")

    assert classifier.calls == 1
    assert decision.agent is AgentName.SUPPORT


@pytest.mark.asyncio
async def test_guardrails_are_never_delegated_to_the_classifier() -> None:
    classifier = StubClassifier(RouteDecision(AgentName.KNOWLEDGE, "looks harmless", 0.99))

    decision = await RouterAgent(classifier=classifier).route("qual é a minha senha?")

    assert classifier.calls == 0
    assert decision.agent is AgentName.ESCALATION
