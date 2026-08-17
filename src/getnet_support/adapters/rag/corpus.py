"""Small offline corpus backed by specific official Getnet sources.

Each Portuguese chunk is a reviewed translation of the English chunk above it, citing the same
official page. Getnet's customers write in Portuguese, and a lexical index does not bridge
languages: without a Portuguese-language chunk, a Portuguese question about a product silently
falls back to escalation. No claim exists in one language that is absent from the other.
"""

from getnet_support.domain.models import KnowledgeChunk

DEFAULT_GETNET_CORPUS = (
    KnowledgeChunk(
        curated=True,
        title="Getnet physical products",
        source="https://site.getnet.com.br/produtos-fisicos/",
        text=(
            "Get Clássica provides printed and digital receipts, a touchscreen, Pix, QR Code, "
            "contactless and chip payments, Wi-Fi and 3G. Get Smart has those payment features "
            "and additionally provides access to business-management applications."
        ),
    ),
    KnowledgeChunk(
        curated=True,
        title="Getnet Payment Link",
        source="https://site.getnet.com.br/link-de-pagamento/",
        text=(
            "Payment Link lets a merchant create an online checkout link for credit, debit and "
            "Pix. The link can be shared through WhatsApp, social networks, email or other remote "
            "channels, so a physical card machine or website is not required for the sale."
        ),
    ),
    KnowledgeChunk(
        curated=True,
        title="Pix with Getnet",
        source="https://site.getnet.com.br/pix/",
        text=(
            "Getnet customers can contract Pix regardless of which bank is linked to receive "
            "sales. Pix sales can be tracked in the Getnet Brasil app, Portal Minha Conta and the "
            "POS sales report. A receiving account still has to be linked during activation."
        ),
    ),
    KnowledgeChunk(
        curated=True,
        title="Getnet receivables advance",
        source="https://site.getnet.com.br/quando-vale-a-pena-antecipar-as-suas-vendas-no-cartao/",
        text=(
            "Receivables advance gives a merchant access before the original settlement date to "
            "money from completed credit sales, subject to a fee. Getnet says eligible credit "
            "sales can be advanced through the Getnet Brasil app; rates and cash-flow impact "
            "should be evaluated before confirming."
        ),
    ),
    KnowledgeChunk(
        curated=True,
        title="Crediário Getnet manual",
        source="https://site.getnet.com.br/wp-content/uploads/2024/09/Folder_Credirio.pdf",
        text=(
            "The Crediário Getnet manual states that installments vary by financial institution: "
            "up to 24 installments generally and up to 48 with Santander, subject to change and "
            "the issuing institution's conditions."
        ),
    ),
    KnowledgeChunk(
        curated=True,
        title="Maquininhas Getnet",
        source="https://site.getnet.com.br/produtos-fisicos/",
        text=(
            "A Get Clássica oferece comprovante impresso e digital, tela sensível ao toque, Pix, "
            "QR Code, pagamento por aproximação e por chip, Wi-Fi e 3G. A Get Smart tem os mesmos "
            "recursos de pagamento e ainda dá acesso a aplicativos de gestão do negócio."
        ),
    ),
    KnowledgeChunk(
        curated=True,
        title="Link de Pagamento Getnet",
        source="https://site.getnet.com.br/link-de-pagamento/",
        text=(
            "O Link de Pagamento permite ao lojista criar um link de checkout online para crédito, "
            "débito e Pix. O link pode ser compartilhado por WhatsApp, redes sociais, e-mail ou "
            "outros canais remotos, então não é necessário ter maquininha física nem site para "
            "concluir a venda."
        ),
    ),
    KnowledgeChunk(
        curated=True,
        title="Pix na Getnet",
        source="https://site.getnet.com.br/pix/",
        text=(
            "O cliente Getnet pode contratar o Pix independentemente de qual banco esteja ligado "
            "ao recebimento das vendas. As vendas por Pix podem ser acompanhadas no app Getnet "
            "Brasil, no Portal Minha Conta e no relatório de vendas da maquininha. Uma conta de "
            "recebimento ainda precisa ser vinculada na ativação."
        ),
    ),
    KnowledgeChunk(
        curated=True,
        title="Antecipação de recebíveis Getnet",
        source="https://site.getnet.com.br/quando-vale-a-pena-antecipar-as-suas-vendas-no-cartao/",
        text=(
            "A antecipação de recebíveis dá ao lojista acesso, antes da data original de "
            "liquidação, ao dinheiro de vendas no crédito já concluídas, mediante uma taxa. "
            "Segundo a Getnet, as vendas no crédito elegíveis podem ser antecipadas pelo app "
            "Getnet Brasil; taxas e impacto no fluxo de caixa devem ser avaliados antes de "
            "confirmar."
        ),
    ),
    KnowledgeChunk(
        curated=True,
        title="Manual do Crediário Getnet",
        source="https://site.getnet.com.br/wp-content/uploads/2024/09/Folder_Credirio.pdf",
        text=(
            "O manual do Crediário Getnet informa que a quantidade de parcelas varia conforme a "
            "instituição financeira: em geral até 24 parcelas e até 48 parcelas com o Santander, "
            "sujeito a alteração e às condições da instituição emissora."
        ),
    ),
)
