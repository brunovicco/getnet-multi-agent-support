"""REQ-K5: navigation, contact, and duplicate text never reach the index."""

from getnet_support.adapters.rag.cleaning import canonical_source, clean_corpus, is_low_information
from getnet_support.domain.models import KnowledgeChunk

PRODUCT_CHUNK = KnowledgeChunk(
    title="Maquininhas Getnet",
    source="https://site.getnet.com.br/produtos-fisicos/",
    text=(
        "A Get Clássica oferece comprovante impresso e digital, tela sensível ao toque, Pix, QR "
        "Code, pagamento por aproximação e por chip, Wi-Fi e 3G para o lojista vender no balcão."
    ),
)
NAVIGATION_TEXT = (
    "Já sou cliente Get Atendimento das 06h00 às 22h00 Capitais e regiões metropolitanas fale "
    "conosco no WhatsApp ou pelo telefone com nossos especialistas todos os dias"
)


def _chunk(text: str, source: str) -> KnowledgeChunk:
    return KnowledgeChunk(title="page", source=source, text=text)


def test_text_repeated_across_pages_is_treated_as_site_chrome() -> None:
    chunks = (
        PRODUCT_CHUNK,
        _chunk(NAVIGATION_TEXT, "https://site.getnet.com.br/pix/"),
        _chunk(NAVIGATION_TEXT, "https://site.getnet.com.br/produtos-fisicos/"),
    )

    cleaned = clean_corpus(chunks)

    assert cleaned == (PRODUCT_CHUNK,)


def test_same_page_served_with_and_without_a_trailing_slash_is_not_chrome() -> None:
    chunks = (
        _chunk(PRODUCT_CHUNK.text, "https://www.getnet.net/en"),
        _chunk(PRODUCT_CHUNK.text, "https://www.getnet.net/en/"),
    )

    cleaned = clean_corpus(chunks)

    assert len(cleaned) == 1


def test_contact_blocks_are_low_information() -> None:
    contact = _chunk(
        "Atendimento Capitais 4002-4000 ou 4003-4000 Interior e demais localidades 0800-648-8000 "
        "fale com um dos nossos especialistas agora mesmo pelo aplicativo",
        "https://site.getnet.com.br/pix/",
    )

    assert is_low_information(contact) is True
    assert is_low_information(PRODUCT_CHUNK) is False


def test_short_menu_fragments_are_low_information() -> None:
    assert is_low_information(_chunk("Minha Conta Ajuda Blog", "https://x.example/")) is True


def test_canonical_source_ignores_the_trailing_slash() -> None:
    assert canonical_source("https://www.getnet.net/en/") == canonical_source(
        "https://www.getnet.net/en"
    )
