"""Customer-specific support agent backed exclusively by typed tools."""

from getnet_support.application.agents.router import (
    DEVICE_TERMS,
    FAULT_TERMS,
    MONEY_TERMS,
    SETTLEMENT_PHRASES,
    phrase_matches,
    tokenize_message,
)
from getnet_support.application.language import detect_language, translate
from getnet_support.application.ports import (
    CustomerProfileToolPort,
    RecentTransactionsToolPort,
    TerminalStatusToolPort,
)
from getnet_support.domain.models import AgentName, AgentResult, RouteName

TERMINAL_SIGNALS = (*DEVICE_TERMS, *FAULT_TERMS, "connect", "internet", "wifi", "wi fi", "chip")
TRANSACTION_SIGNALS = (*MONEY_TERMS, *SETTLEMENT_PHRASES)


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
        tokens = tokenize_message(message)
        language = detect_language(message, tokens)
        profile = await self._customer_profiles.get_customer_profile(user_id)
        if profile is None:
            return AgentResult(
                answer=translate("support_unknown_customer", language),
                agent=AgentName.ESCALATION,
                route=RouteName.HUMAN_HANDOFF,
                handoff_required=True,
                tool_calls=1,
            )

        needs_terminal = _contains_signal(tokens, TERMINAL_SIGNALS)
        needs_transactions = _contains_signal(tokens, TRANSACTION_SIGNALS)
        answer_parts = [translate("support_profile_status", language, status=profile.status)]
        tool_calls = 1

        if needs_transactions:
            transactions = await self._recent_transactions.get_recent_transactions(user_id)
            tool_calls += 1
            if transactions:
                latest = transactions[0]
                answer_parts.append(
                    translate(
                        "support_latest_sale",
                        language,
                        status=latest.status,
                        settlement=latest.settlement_status.replace("_", " "),
                    )
                )
                if latest.expected_settlement_at is not None:
                    answer_parts.append(
                        translate(
                            "support_settlement_date",
                            language,
                            date=latest.expected_settlement_at.date().isoformat(),
                        )
                    )
            else:
                answer_parts.append(translate("support_no_transactions", language))

        if needs_terminal:
            terminal = await self._terminal_status.get_terminal_status(user_id)
            tool_calls += 1
            if terminal is None:
                answer_parts.append(translate("support_no_terminal", language))
            else:
                answer_parts.append(
                    translate(
                        "support_terminal_status",
                        language,
                        terminal=terminal.terminal_id,
                        connectivity=terminal.connectivity,
                        diagnostic=terminal.diagnostic,
                    )
                )
                if terminal.connectivity == "disconnected":
                    answer_parts.append(translate("support_terminal_offline_guidance", language))

        if not needs_terminal and not needs_transactions:
            answer_parts.append(translate("support_out_of_scope", language))

        return AgentResult(
            answer=" ".join(answer_parts),
            agent=AgentName.SUPPORT,
            route=RouteName.CUSTOMER_TOOLS,
            tool_calls=tool_calls,
        )


def _contains_signal(tokens: tuple[str, ...], signals: tuple[str, ...]) -> bool:
    return any(phrase_matches(tokens, signal) for signal in signals)
