"""REQ-L1: responses are produced in the language of the incoming message."""

import pytest

from getnet_support.application.language import MESSAGES, detect_language, translate


@pytest.mark.parametrize(
    "message",
    [
        "Quando cai o dinheiro da venda de ontem?",
        "Minha maquininha não está pegando sinal",
        "Preciso de conta bancária para receber via Pix?",
    ],
)
def test_portuguese_messages_are_detected(message: str) -> None:
    assert detect_language(message) == "pt"


@pytest.mark.parametrize(
    "message",
    [
        "When will the money from yesterday's sales be deposited?",
        "My card machine won't connect to the internet",
        "What is the euro exchange rate today?",
    ],
)
def test_english_messages_are_detected(message: str) -> None:
    assert detect_language(message) == "en"


def test_empty_message_falls_back_to_english() -> None:
    assert detect_language("") == "en"


def test_every_catalogue_entry_covers_both_languages() -> None:
    assert all({"pt", "en"} == set(entry) for entry in MESSAGES.values())


def test_translation_interpolates_values() -> None:
    rendered = translate("support_settlement_date", "pt", date="2026-08-18")

    assert "2026-08-18" in rendered
