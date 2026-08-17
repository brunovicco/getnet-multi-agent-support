"""Terminal status tool adapter."""

from getnet_support.adapters.repositories.fake_customer_repository import FakeCustomerRepository
from getnet_support.domain.models import TerminalStatus


class TerminalStatusTool:
    """Resolve status through the terminal assigned to a customer profile."""

    def __init__(self, repository: FakeCustomerRepository) -> None:
        """Store the customer data boundary."""
        self._repository = repository

    async def get_terminal_status(self, user_id: str) -> TerminalStatus | None:
        """Retrieve only the terminal assigned to ``user_id``."""
        return await self._repository.get_terminal(user_id)
