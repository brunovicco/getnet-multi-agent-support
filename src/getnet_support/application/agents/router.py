"""Hybrid intent routing: deterministic rules first, optional LLM classifier on top.

Routing is the single most evaluation-sensitive component of the system, so it is built in two
independent layers:

* a deterministic, dependency-free rule layer that works with no credentials, is fully
  reproducible, and is measured by an offline regression dataset (``evals/routing_dataset.jsonl``);
* an optional LLM classifier that generalizes to unseen paraphrases, and which never overrides a
  safety guardrail decision.

The rule layer supports token-prefix patterns (``conect*``) and co-occurrence groups (``all_of``)
so that a device word plus a fault word routes to support even when the exact sentence was never
anticipated. Phrase-sized rules alone do not survive paraphrase or translation.
"""

import re
import unicodedata
from dataclasses import dataclass

from getnet_support.application.ports import IntentClassifierPort
from getnet_support.domain.models import AgentName, RouteDecision

# A message is executed as an agent sequence only when it carries a customer-specific incident
# AND a public product topic ("my terminal is offline and how does antecipacao work?"). Score
# proximity alone is not enough: a device word such as "maquininha" is both an incident signal and
# a product signal, so a score-only rule would append marketing text to every incident answer.
SUPPORT_INCIDENT_LABELS = frozenset(
    {"terminal-incident", "transaction-incident", "customer-settlement-phrase"}
)
PRODUCT_TOPIC_SIGNALS = (
    "pix",
    "crediario",
    "antecipac*",
    "antecipar",
    "receivables advance",
    "link de pagamento",
    "payment link",
    "taxa*",
    "tarifa*",
    "aluguel",
    "parcelament*",
    "boleto",
    "tef",
    "conciliador",
    "split",
    "get conta",
    "get store",
    "qr code",
)


def normalize_text(value: str) -> str:
    """Normalize accents and punctuation while preserving word boundaries."""
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def tokenize_message(value: str) -> tuple[str, ...]:
    """Return normalized word tokens used by rules and language detection."""
    return tuple(normalize_text(value).split())


def _compile_pattern(phrase: str) -> tuple[str, ...]:
    """Normalize a pattern while preserving the trailing ``*`` prefix marker per token."""
    parts: list[str] = []
    for raw_token in phrase.split():
        wildcard = raw_token.endswith("*")
        normalized = normalize_text(raw_token)
        if not normalized:
            continue
        parts.extend(normalized.split())
        if wildcard and parts:
            parts[-1] = f"{parts[-1]}*"
    return tuple(parts)


def _token_matches(token: str, pattern: str) -> bool:
    if pattern.endswith("*"):
        return token.startswith(pattern[:-1])
    return token == pattern


def phrase_matches(tokens: tuple[str, ...], phrase: str) -> bool:
    """Return whether a pattern matches as complete words, honouring ``*`` prefixes."""
    parts = _compile_pattern(phrase)
    if not parts or len(parts) > len(tokens):
        return False
    span = len(parts)
    return any(
        all(_token_matches(tokens[start + offset], parts[offset]) for offset in range(span))
        for start in range(len(tokens) - span + 1)
    )


def _matches_any(tokens: tuple[str, ...], phrases: tuple[str, ...]) -> bool:
    return any(phrase_matches(tokens, phrase) for phrase in phrases)


@dataclass(frozen=True, slots=True)
class IntentRule:
    """One independently testable routing signal.

    ``any_of`` matches when a single pattern is present. ``all_of`` matches only when every
    group contributes at least one pattern, which models co-occurrence such as
    "device word" + "fault word".
    """

    label: str
    agent: AgentName
    weight: float
    any_of: tuple[str, ...] = ()
    all_of: tuple[tuple[str, ...], ...] = ()

    def matches(self, tokens: tuple[str, ...]) -> bool:
        """Return whether this rule fires for the normalized tokens."""
        if not self.any_of and not self.all_of:
            return False
        if self.any_of and not _matches_any(tokens, self.any_of):
            return False
        return all(_matches_any(tokens, group) for group in self.all_of)


DEVICE_TERMS = (
    "maquininha*",
    "maquina*",
    "maquinha",
    "terminal*",
    "pos",
    "pinpad",
    "pin pad",
    "leitor*",
    "machine",
    "machines",
    "device",
    "reader",
    "equipamento*",
    "aparelho*",
    "get clas*",
    "get smart",
    "get mini",
    "get tap",
)
FAULT_TERMS = (
    "erro*",
    "error",
    "errors",
    "falha*",
    "problema*",
    "defeito*",
    "quebrad*",
    "travand*",
    "travou",
    "trava",
    "reinici*",
    "desliga*",
    "nao liga",
    "nao funciona",
    "nao esta funcionando",
    "parou",
    "parada",
    "offline",
    "off line",
    "desconectad*",
    "sem internet",
    "sem sinal",
    "sem conexao",
    "sem rede",
    "nao conecta*",
    "nao esta conectando",
    "nao pega*",
    "not connecting",
    "won't connect",
    "will not connect",
    "cannot connect",
    "can't connect",
    "not working",
    "does not work",
    "doesn't work",
    "broken",
    "stuck",
    "crash*",
    "restarting",
    "no signal",
    "no internet",
    "negad*",
    "recusad*",
    "declin*",
    "rejeitad*",
    "sem bateria",
    "nao imprime",
    "not printing",
    # Progressive forms are common in spoken Portuguese complaints ("nao esta pegando sinal").
    "pegando",
    "conectando",
    "funcionando",
    "imprimindo",
    "carregando",
    "aparecendo",
)
POSSESSIVE_TERMS = (
    "meu",
    "meus",
    "minha",
    "minhas",
    "my",
    "our",
    "mine",
)
MONEY_TERMS = (
    "venda*",
    "sale",
    "sales",
    "dinheiro",
    "valor*",
    "recebiment*",
    "receber",
    "recebi",
    "recebo",
    "deposit*",
    "liquidac*",
    "settlement",
    "settled",
    "pagament*",
    "payment",
    "payments",
    "saldo",
    "extrato",
    "transacao",
    "transacoes",
    "transaction",
    "transactions",
    "repasse",
)
SETTLEMENT_PHRASES = (
    "quando cai",
    "quando caiu",
    "quando vou receber",
    "quando recebo",
    "quando eu recebo",
    "cai o dinheiro",
    "caiu o dinheiro",
    "caiu na conta",
    "nao caiu",
    "ainda nao recebi",
    "nao recebi",
    "venda de ontem",
    "vendas de ontem",
    "yesterday's sales",
    "yesterday sales",
    "be deposited",
    "when will the money",
    "not been deposited",
    "have not received",
    "haven't received",
    "status da minha venda",
)
GETNET_PRODUCT_SIGNALS = (
    "getnet",
    "get clas*",
    "get smart",
    "get mini",
    "get tap",
    "get conta",
    "get store",
    "payment link",
    "link de pagamento",
    "pix",
    "crediario",
    "receivables advance",
    "antecipac*",
    "antecipar",
    "card machine",
    "maquina de cartao",
    "maquininha*",
    "tap on phone",
    "qr code",
    "conciliador",
    "tef",
    "credenciament*",
    "bandeira*",
    "boleto",
    "taxa*",
    "tarifa*",
    "aluguel",
    "parcelament*",
    "parcela*",
    "installment*",
    "e commerce",
    "checkout",
    "split",
    "conversor de moedas",
)
CURRENT_INFORMATION_SIGNALS = (
    "weather",
    "forecast",
    "previsao*",
    "clima",
    "temperatura",
    "tempo amanha",
    "cotac*",
    "exchange rate",
    "dolar",
    "euro",
    "bitcoin",
    "bolsa",
    "noticia*",
    "news",
    "hoje",
    "amanha",
    "today",
    "tomorrow",
    "right now",
    "agora",
)
GENERAL_INFORMATION_SIGNALS = (
    "what is",
    "what are",
    "what's",
    "difference between",
    "who is",
    "where is",
    "when is",
    "why is",
    "which",
    "how does",
    "how do",
    "how much",
    "how many",
    "can i",
    "do i need",
    "is it possible",
    "explain",
    "tell me about",
    "qual",
    "quais",
    "quem",
    "onde",
    "quando",
    "por que",
    "porque",
    "como funciona",
    "como faco",
    "posso",
    "preciso",
    "quantas",
    "quantos",
    "e possivel",
    "diferenca entre",
    "o que e",
    "me explica",
    "explique",
)
SENSITIVE_DATA_SIGNALS = (
    "password",
    "passwords",
    "senha*",
    "credit card number",
    "card number",
    "numero do cartao",
    "numero do meu cartao",
    "cvv",
    "codigo de seguranca",
    "api key",
    "token de acesso",
    "chave de api",
    "meu cpf completo",
    "dados do cartao",
)
UNSUPPORTED_ACTION_SIGNALS = (
    "cancel my account",
    "close my account",
    "transfer money",
    "refund this sale",
    "change my bank account",
    "cancelar minha conta",
    "encerrar minha conta",
    "cancelar meu contrato",
    "transferir dinheiro",
    "estornar",
    "estorno",
    "alterar minha conta",
    "trocar minha conta",
    "mudar minha conta bancaria",
    "trocar a titularidade",
    "aumentar meu limite",
    "renegociar",
    "cancelar minha maquininha",
)


ROUTING_RULES: tuple[IntentRule, ...] = (
    IntentRule(
        label="sensitive-data",
        agent=AgentName.ESCALATION,
        weight=1.0,
        any_of=SENSITIVE_DATA_SIGNALS,
    ),
    IntentRule(
        label="unsupported-action",
        agent=AgentName.ESCALATION,
        weight=0.95,
        any_of=UNSUPPORTED_ACTION_SIGNALS,
    ),
    IntentRule(
        label="terminal-incident",
        agent=AgentName.SUPPORT,
        weight=0.9,
        all_of=(DEVICE_TERMS, FAULT_TERMS),
    ),
    IntentRule(
        label="transaction-incident",
        agent=AgentName.SUPPORT,
        weight=0.9,
        any_of=(
            "transaction decline",
            "transaction declined",
            "decline error",
            "venda negada",
            "venda recusada",
            "compra negada",
            "cartao recusado",
            "transacao negada",
            "erro na venda",
            "codigo de erro",
            "error code",
        ),
    ),
    IntentRule(
        label="customer-settlement-phrase",
        agent=AgentName.SUPPORT,
        weight=0.85,
        any_of=SETTLEMENT_PHRASES,
    ),
    IntentRule(
        label="customer-settlement-context",
        agent=AgentName.SUPPORT,
        weight=0.6,
        all_of=(POSSESSIVE_TERMS, MONEY_TERMS),
    ),
    IntentRule(
        label="current-information",
        agent=AgentName.KNOWLEDGE,
        weight=0.85,
        any_of=CURRENT_INFORMATION_SIGNALS,
    ),
    IntentRule(
        label="getnet-product",
        agent=AgentName.KNOWLEDGE,
        weight=0.8,
        any_of=GETNET_PRODUCT_SIGNALS,
    ),
    IntentRule(
        label="informational-question",
        agent=AgentName.KNOWLEDGE,
        weight=0.25,
        any_of=GENERAL_INFORMATION_SIGNALS,
    ),
)


class RouterAgent:
    """Route messages through explicit rules, with an optional LLM classifier on top."""

    def __init__(
        self,
        rules: tuple[IntentRule, ...] = ROUTING_RULES,
        classifier: IntentClassifierPort | None = None,
    ) -> None:
        """Use the default centralized rules, an injected evaluation set, and a classifier."""
        self._rules = rules
        self._classifier = classifier

    async def route(self, message: str) -> RouteDecision:
        """Return the route, delegating to the classifier only when no guardrail fired."""
        rule_decision = self.route_with_rules(message)
        if self._classifier is None or rule_decision.guardrail:
            return rule_decision
        classified = await self._classifier.classify(message)
        if classified is None:
            return rule_decision
        return RouteDecision(
            agent=classified.agent,
            reason=f"LLM classifier: {classified.reason}",
            confidence=classified.confidence,
            secondary_agent=classified.secondary_agent or rule_decision.secondary_agent,
        )

    def route_with_rules(self, message: str) -> RouteDecision:
        """Return the deterministic decision used as default and as classifier fallback."""
        tokens = tokenize_message(message)
        matched = tuple(rule for rule in self._rules if rule.matches(tokens))
        if not matched:
            return RouteDecision(
                agent=AgentName.ESCALATION,
                reason="No supported intent matched the request.",
                confidence=0.35,
            )

        escalation = tuple(rule for rule in matched if rule.agent is AgentName.ESCALATION)
        if escalation:
            strongest = max(escalation, key=lambda rule: rule.weight)
            return RouteDecision(
                agent=AgentName.ESCALATION,
                reason=f"Guardrail matched: {strongest.label}.",
                confidence=strongest.weight,
                guardrail=True,
            )

        scores = {
            agent: sum(rule.weight for rule in matched if rule.agent is agent)
            for agent in (AgentName.KNOWLEDGE, AgentName.SUPPORT)
        }
        selected = max(scores, key=scores.__getitem__)
        runner_up = min(scores, key=scores.__getitem__)
        selected_rules = tuple(rule for rule in matched if rule.agent is selected)
        labels = ", ".join(rule.label for rule in selected_rules)
        has_incident = any(rule.label in SUPPORT_INCIDENT_LABELS for rule in matched)
        has_product_topic = _matches_any(tokens, PRODUCT_TOPIC_SIGNALS)
        secondary = (
            runner_up if runner_up is not selected and has_incident and has_product_topic else None
        )
        return RouteDecision(
            agent=selected,
            reason=f"Matched routing signals: {labels}.",
            confidence=score_to_confidence(scores[selected]),
            secondary_agent=secondary,
        )


def score_to_confidence(score: float) -> float:
    """Map an accumulated rule score to the routing confidence used by the orchestrator.

    This is a monotonic heuristic priority score, not a calibrated probability. It exists so the
    escalation threshold is a single documented number; calibration against the offline routing
    dataset is tracked in ``docs/EVALUATION.md``.
    """
    return round(min(0.97, 0.55 + (score * 0.32)), 3)
