"""Recent transactions tool adapter."""

from getnet_support.adapters.repositories.fake_customer_repository import FakeCustomerRepository
from getnet_support.domain.models import Transaction


class RecentTransactionsTool:
    """Expose customer-scoped recent transactions."""

    def __init__(self, repository: FakeCustomerRepository) -> None:
        """Store the customer data boundary."""
        self._repository = repository

    async def get_recent_transactions(self, user_id: str) -> tuple[Transaction, ...]:
        """Retrieve transactions without allowing cross-customer filters."""
        return await self._repository.get_transactions(user_id)
