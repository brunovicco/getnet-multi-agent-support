"""In-memory customer data for a deterministic local demonstration."""

from datetime import UTC, datetime
from decimal import Decimal

from getnet_support.domain.models import CustomerProfile, TerminalStatus, Transaction

CUSTOMERS = {
    "cliente1988": CustomerProfile(
        user_id="cliente1988",
        name="João Silva",
        status="active",
        terminal_id="GET-12345",
    ),
    "cliente2026": CustomerProfile(
        user_id="cliente2026",
        name="Maria Oliveira",
        status="active",
        terminal_id="GET-67890",
    ),
}

TRANSACTIONS = (
    Transaction(
        transaction_id="txn-1001",
        user_id="cliente1988",
        amount=Decimal("249.90"),
        occurred_at=datetime(2026, 8, 16, 18, 30, tzinfo=UTC),
        payment_method="credit",
        status="approved",
        settlement_status="scheduled",
        expected_settlement_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
    ),
    Transaction(
        transaction_id="txn-1000",
        user_id="cliente1988",
        amount=Decimal("89.50"),
        occurred_at=datetime(2026, 8, 15, 14, 5, tzinfo=UTC),
        payment_method="pix",
        status="approved",
        settlement_status="settled",
        expected_settlement_at=datetime(2026, 8, 15, 14, 6, tzinfo=UTC),
    ),
    Transaction(
        transaction_id="txn-2001",
        user_id="cliente2026",
        amount=Decimal("710.00"),
        occurred_at=datetime(2026, 8, 16, 13, 0, tzinfo=UTC),
        payment_method="debit",
        status="approved",
        settlement_status="settled",
        expected_settlement_at=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
    ),
)

TERMINALS = {
    "GET-12345": TerminalStatus(
        terminal_id="GET-12345",
        connectivity="disconnected",
        operational_status="degraded",
        last_seen_at=datetime(2026, 8, 17, 12, 30, tzinfo=UTC),
        diagnostic="mobile data session is offline",
    ),
    "GET-67890": TerminalStatus(
        terminal_id="GET-67890",
        connectivity="connected",
        operational_status="operational",
        last_seen_at=datetime(2026, 8, 17, 12, 35, tzinfo=UTC),
        diagnostic="no active faults",
    ),
}


class FakeCustomerRepository:
    """Keep fake records isolated behind customer-scoped lookup methods."""

    async def get_profile(self, user_id: str) -> CustomerProfile | None:
        """Return exactly one profile by its external identifier."""
        return CUSTOMERS.get(user_id)

    async def get_transactions(self, user_id: str) -> tuple[Transaction, ...]:
        """Return only transactions owned by ``user_id``, newest first."""
        scoped = (transaction for transaction in TRANSACTIONS if transaction.user_id == user_id)
        return tuple(sorted(scoped, key=lambda transaction: transaction.occurred_at, reverse=True))

    async def get_terminal(self, user_id: str) -> TerminalStatus | None:
        """Resolve a terminal only through the requesting customer's profile."""
        profile = await self.get_profile(user_id)
        if profile is None:
            return None
        return TERMINALS.get(profile.terminal_id)
