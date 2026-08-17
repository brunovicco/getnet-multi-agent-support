"""Small offline corpus backed by specific official Getnet sources."""

from getnet_support.domain.models import KnowledgeChunk

DEFAULT_GETNET_CORPUS = (
    KnowledgeChunk(
        title="Getnet physical products",
        source="https://site.getnet.com.br/produtos-fisicos/",
        text=(
            "Get Clássica provides printed and digital receipts, a touchscreen, Pix, QR Code, "
            "contactless and chip payments, Wi-Fi and 3G. Get Smart has those payment features "
            "and additionally provides access to business-management applications."
        ),
    ),
    KnowledgeChunk(
        title="Getnet Payment Link",
        source="https://site.getnet.com.br/link-de-pagamento/",
        text=(
            "Payment Link lets a merchant create an online checkout link for credit, debit and "
            "Pix. The link can be shared through WhatsApp, social networks, email or other remote "
            "channels, so a physical card machine or website is not required for the sale."
        ),
    ),
    KnowledgeChunk(
        title="Pix with Getnet",
        source="https://site.getnet.com.br/pix/",
        text=(
            "Getnet customers can contract Pix regardless of which bank is linked to receive "
            "sales. Pix sales can be tracked in the Getnet Brasil app, Portal Minha Conta and the "
            "POS sales report. A receiving account still has to be linked during activation."
        ),
    ),
    KnowledgeChunk(
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
        title="Crediário Getnet manual",
        source="https://site.getnet.com.br/wp-content/uploads/2024/09/Folder_Credirio.pdf",
        text=(
            "The Crediário Getnet manual states that installments vary by financial institution: "
            "up to 24 installments generally and up to 48 with Santander, subject to change and "
            "the issuing institution's conditions."
        ),
    ),
)
