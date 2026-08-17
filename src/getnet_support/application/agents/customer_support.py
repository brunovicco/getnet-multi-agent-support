"""Customer-specific support agent backed exclusively by typed tools."""

from getnet_support.application.agents.router import normalize_text
from getnet_support.application.ports import (
    CustomerProfileToolPort,
    RecentTransactionsToolPort,
    TerminalStatusToolPort,
)
from getnet_support.domain.models import AgentName, AgentResult, RouteName

TERMINAL_SIGNALS = (
    "machine",
    "terminal",
    "maquininha",
    "connect",
    "internet",
    "decline",
    "declined",
    "negada",
)
TRANSACTION_SIGNALS = (
    "sale",
    "sales",
    "transaction",
    "deposit",
    "settlement",
    "venda",
    "vendas",
    "recebimento",
    "deposito",
)


class CustomerSupportAgent:
    """Resolve customer incidents without generating unverified account facts."""

    def __init__(
        self,
        customer_profiles: CustomerProfileToolPort,
        recent_transactions: RecentTransactionsToolPort,
        terminal_status: TerminalStatusToolPort,
    ) -> None:
        """Inject the only capabilities allowed to read customer data."""
        self._customer_profiles = customer_profiles
        self._recent_transactions = recent_transactions
        self._terminal_status = terminal_status

    async def handle(self, message: str, user_id: str) -> AgentResult:
        """Select only necessary tools and compose an evidence-based support answer."""
        profile = await self._customer_profiles.get_customer_profile(user_id)
        if profile is None:
            return AgentResult(
                answer="No customer was found for this user identifier. Human support is required.",
                agent=AgentName.ESCALATION,
                route=RouteName.HUMAN_HANDOFF,
                handoff_required=True,
                tool_calls=1,
            )

        normalized = normalize_text(message)
        needs_terminal = self._contains_signal(normalized, TERMINAL_SIGNALS)
        needs_transactions = self._contains_signal(normalized, TRANSACTION_SIGNALS)
        answer_parts = [f"Customer profile status: {profile.status}."]
        tool_calls = 1

        if needs_transactions:
            transactions = await self._recent_transactions.get_recent_transactions(user_id)
            tool_calls += 1
            if transactions:
                latest = transactions[0]
                settlement = latest.settlement_status.replace("_", " ")
                answer_parts.append(
                    f"The most recent sale is {latest.status} and its settlement is {settlement}."
                )
                if latest.expected_settlement_at is not None:
                    settlement_date = latest.expected_settlement_at.date().isoformat()
                    answer_parts.append(f"Expected settlement date: {settlement_date}.")
            else:
                answer_parts.append("No recent transactions were returned by the customer tool.")

        if needs_terminal:
            terminal = await self._terminal_status.get_terminal_status(user_id)
            tool_calls += 1
            if terminal is None:
                answer_parts.append("No terminal is assigned to this customer.")
            else:
                answer_parts.append(
                    f"Terminal {terminal.terminal_id} connectivity is {terminal.connectivity}; "
                    f"diagnostic: {terminal.diagnostic}."
                )
                if terminal.connectivity == "disconnected":
                    answer_parts.append(
                        "Check Wi-Fi or mobile signal, restart the terminal, and contact human "
                        "support if it remains offline."
                    )

        if not needs_terminal and not needs_transactions:
            answer_parts.append(
                "The support tools do not expose the operation requested; "
                "human support is recommended."
            )

        return AgentResult(
            answer=" ".join(answer_parts),
            agent=AgentName.SUPPORT,
            route=RouteName.CUSTOMER_TOOLS,
            tool_calls=tool_calls,
        )

    @staticmethod
    def _contains_signal(normalized: str, signals: tuple[str, ...]) -> bool:
        padded = f" {normalized} "
        return any(f" {normalize_text(signal)} " in padded for signal in signals)
