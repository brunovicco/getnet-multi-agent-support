"""Deterministic language detection and bilingual response catalogue.

Getnet's audience is Brazilian, so every agent answer must be produced in the language of the
incoming message. Detection is intentionally lexical and dependency-free: it must work with no
provider credentials, and a wrong guess degrades to English rather than to a failure.
"""

from typing import Literal

Language = Literal["pt", "en"]

_PORTUGUESE_MARKERS: frozenset[str] = frozenset(
    {
        "a",
        "as",
        "ao",
        "com",
        "como",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "e",
        "em",
        "meu",
        "minha",
        "minhas",
        "meus",
        "na",
        "nao",
        "no",
        "o",
        "os",
        "ontem",
        "para",
        "pelo",
        "por",
        "posso",
        "preciso",
        "qual",
        "quais",
        "quando",
        "quanto",
        "quantas",
        "quantos",
        "que",
        "sem",
        "ser",
        "sobre",
        "um",
        "uma",
        "vou",
    }
)
_ENGLISH_MARKERS: frozenset[str] = frozenset(
    {
        "a",
        "about",
        "and",
        "are",
        "can",
        "do",
        "does",
        "for",
        "from",
        "how",
        "i",
        "is",
        "it",
        "many",
        "me",
        "my",
        "need",
        "of",
        "the",
        "to",
        "what",
        "when",
        "where",
        "which",
        "will",
        "with",
        "you",
        "your",
    }
)


def detect_language(message: str, tokens: tuple[str, ...] | None = None) -> Language:
    """Return the response language for a message, defaulting to English when ambiguous.

    ``tokens`` may be supplied by callers that already normalized the message, avoiding a second
    normalization pass on the request path.
    """
    if tokens is None:
        from getnet_support.application.agents.router import tokenize_message

        tokens = tokenize_message(message)
    if not tokens:
        return "en"
    portuguese = sum(1 for token in tokens if token in _PORTUGUESE_MARKERS)
    english = sum(1 for token in tokens if token in _ENGLISH_MARKERS)
    if portuguese > english:
        return "pt"
    return "en"


MESSAGES: dict[str, dict[Language, str]] = {
    "escalation_default": {
        "en": (
            "I could not resolve this request confidently and safely, so it is being handed to a "
            "human Getnet specialist."
        ),
        "pt": (
            "Não consegui resolver esta solicitação com segurança e confiança, então ela está "
            "sendo encaminhada para um especialista humano da Getnet."
        ),
    },
    "escalation_sensitive": {
        "en": (
            "For your security, sensitive data such as passwords, card numbers, or security codes "
            "is never handled in this channel. A human Getnet specialist will continue from here."
        ),
        "pt": (
            "Por segurança, dados sensíveis como senhas, números de cartão ou códigos de segurança "
            "nunca são tratados neste canal. Um especialista humano da Getnet dará continuidade."
        ),
    },
    "escalation_unsupported_action": {
        "en": (
            "This assistant cannot perform operations that change your account, contract, or "
            "money. A human Getnet specialist will take over this request."
        ),
        "pt": (
            "Este assistente não executa operações que alteram sua conta, seu contrato ou seu "
            "dinheiro. Um especialista humano da Getnet vai assumir esta solicitação."
        ),
    },
    "escalation_channels": {
        "en": "Handoff reference {reference}. Getnet support: 4002-4000 or 0800-648-8000.",
        "pt": "Protocolo de transferência {reference}. Getnet: 4002-4000 ou 0800-648-8000.",
    },
    "web_search_unavailable": {
        "en": (
            "Current external information is not available: no web search provider is configured, "
            "so no current result was invented. A human specialist can confirm it for you."
        ),
        "pt": (
            "Informação externa atualizada não está disponível: nenhum provedor de busca web está "
            "configurado, então nenhum resultado atual foi inventado. Um especialista humano pode "
            "confirmar essa informação para você."
        ),
    },
    "knowledge_insufficient_evidence": {
        "en": (
            "The indexed Getnet sources do not contain enough evidence to answer this question, so "
            "it is being handed to a human specialist instead of guessing."
        ),
        "pt": (
            "As fontes indexadas da Getnet não têm evidência suficiente para responder a esta "
            "pergunta, então ela está sendo encaminhada a um especialista humano em vez de ser "
            "respondida por suposição."
        ),
    },
    "knowledge_grounded_prefix": {
        "en": "Based on the indexed Getnet sources: {evidence}",
        "pt": "Com base nas fontes indexadas da Getnet: {evidence}",
    },
    "support_unknown_customer": {
        "en": "No customer was found for this user identifier. Human support is required.",
        "pt": (
            "Nenhum cliente foi encontrado para este identificador. É necessário atendimento "
            "humano."
        ),
    },
    "support_profile_status": {
        "en": "Customer profile status: {status}.",
        "pt": "Situação do cadastro do cliente: {status}.",
    },
    "support_latest_sale": {
        "en": "The most recent sale is {status} and its settlement is {settlement}.",
        "pt": "A venda mais recente está {status} e a liquidação está {settlement}.",
    },
    "support_settlement_date": {
        "en": "Expected settlement date: {date}.",
        "pt": "Data prevista de recebimento: {date}.",
    },
    "support_no_transactions": {
        "en": "No recent transactions were returned by the customer tool.",
        "pt": "A ferramenta de cliente não retornou transações recentes.",
    },
    "support_no_terminal": {
        "en": "No terminal is assigned to this customer.",
        "pt": "Nenhum terminal está associado a este cliente.",
    },
    "support_terminal_status": {
        "en": "Terminal {terminal} connectivity is {connectivity}; diagnostic: {diagnostic}.",
        "pt": "A conectividade do terminal {terminal} está {connectivity}; diagnóstico: "
        "{diagnostic}.",
    },
    "support_terminal_offline_guidance": {
        "en": (
            "Check the Wi-Fi or mobile signal, restart the terminal, and contact human support if "
            "it remains offline."
        ),
        "pt": (
            "Verifique o sinal de Wi-Fi ou de dados móveis, reinicie o terminal e acione o "
            "atendimento humano se ele continuar offline."
        ),
    },
    "support_out_of_scope": {
        "en": (
            "The support tools do not expose the operation requested; human support is recommended."
        ),
        "pt": (
            "As ferramentas de atendimento não expõem a operação solicitada; recomenda-se "
            "atendimento humano."
        ),
    },
}


def translate(key: str, language: Language, **values: object) -> str:
    """Return a catalogued message, failing loudly on an unknown key during development."""
    template = MESSAGES[key][language]
    return template.format(**values) if values else template
