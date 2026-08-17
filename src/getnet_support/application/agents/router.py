"""Deterministic, testable intent routing."""

import re
import unicodedata
from dataclasses import dataclass

from getnet_support.domain.models import AgentName, RouteDecision


def normalize_text(value: str) -> str:
    """Normalize accents and punctuation while preserving word boundaries."""
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


@dataclass(frozen=True, slots=True)
class IntentRule:
    """One independently testable routing signal."""

    label: str
    agent: AgentName
    phrases: tuple[str, ...]
    weight: float

    def matches(self, normalized_message: str) -> bool:
        """Return whether any normalized phrase is present as complete words."""
        padded = f" {normalized_message} "
        return any(f" {normalize_text(phrase)} " in padded for phrase in self.phrases)


GETNET_PRODUCT_SIGNALS = (
    "getnet",
    "get classica",
    "get smart",
    "get mini",
    "payment link",
    "link de pagamento",
    "get tap",
    "pix",
    "crediario",
    "receivables advance",
    "antecipacao",
    "card machine",
    "maquina de cartao",
    "maquininha",
)

GENERAL_INFORMATION_SIGNALS = (
    "what is",
    "what are",
    "what's the difference",
    "who is",
    "where is",
    "when is",
    "why is",
    "which",
    "how does",
    "how do",
    "can i",
    "do i need",
    "qual e",
    "quais sao",
    "quem e",
    "onde fica",
    "quando e",
    "por que",
    "como funciona",
)


ROUTING_RULES: tuple[IntentRule, ...] = (
    IntentRule(
        "sensitive-data",
        AgentName.ESCALATION,
        ("password", "senha", "credit card number", "numero do cartao", "cvv", "api key"),
        1.0,
    ),
    IntentRule(
        "unsupported-action",
        AgentName.ESCALATION,
        (
            "cancel my account",
            "close my account",
            "transfer money",
            "refund this sale",
            "change my bank account",
            "cancelar minha conta",
            "transferir dinheiro",
        ),
        0.95,
    ),
    IntentRule(
        "terminal-incident",
        AgentName.SUPPORT,
        (
            "won't connect",
            "will not connect",
            "cannot connect",
            "sem internet",
            "nao conecta",
            "transaction decline",
            "transaction declined",
            "decline error",
            "venda negada",
            "machine error",
        ),
        0.9,
    ),
    IntentRule(
        "customer-settlement",
        AgentName.SUPPORT,
        (
            "my sales",
            "yesterday's sales",
            "yesterday sales",
            "be deposited",
            "my deposit",
            "my payment",
            "minhas vendas",
            "meu recebimento",
            "meu deposito",
        ),
        0.85,
    ),
    IntentRule(
        "current-information",
        AgentName.KNOWLEDGE,
        (
            "weather",
            "forecast",
            "exchange rate",
            "cotacao",
            "tempo amanha",
            "previsao do tempo",
        ),
        0.85,
    ),
    IntentRule(
        "getnet-product",
        AgentName.KNOWLEDGE,
        GETNET_PRODUCT_SIGNALS,
        0.8,
    ),
    IntentRule(
        "informational-question",
        AgentName.KNOWLEDGE,
        GENERAL_INFORMATION_SIGNALS,
        0.2,
    ),
)


class RouterAgent:
    """Route messages through an explicit weighted rule set."""

    def __init__(self, rules: tuple[IntentRule, ...] = ROUTING_RULES) -> None:
        """Use the default centralized rules or an injected evaluation rule set."""
        self._rules = rules

    def route(self, message: str) -> RouteDecision:
        """Return the strongest supported intent with a calibrated confidence."""
        normalized = normalize_text(message)
        matched = tuple(rule for rule in self._rules if rule.matches(normalized))
        if not matched:
            return RouteDecision(
                AgentName.ESCALATION,
                "No supported intent matched the request.",
                0.35,
            )

        escalation = tuple(rule for rule in matched if rule.agent is AgentName.ESCALATION)
        if escalation:
            strongest = max(escalation, key=lambda rule: rule.weight)
            return RouteDecision(
                AgentName.ESCALATION,
                f"Guardrail matched: {strongest.label}.",
                strongest.weight,
            )

        scores = {
            agent: sum(rule.weight for rule in matched if rule.agent is agent)
            for agent in (AgentName.KNOWLEDGE, AgentName.SUPPORT)
        }
        selected = max(scores, key=scores.__getitem__)
        selected_rules = tuple(rule for rule in matched if rule.agent is selected)
        raw_score = scores[selected]
        confidence = round(min(0.97, 0.55 + (raw_score * 0.32)), 3)
        labels = ", ".join(rule.label for rule in selected_rules)
        return RouteDecision(selected, f"Matched routing signals: {labels}.", confidence)
