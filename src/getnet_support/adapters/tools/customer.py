"""Customer profile tool adapter."""

from getnet_support.adapters.repositories.fake_customer_repository import FakeCustomerRepository
from getnet_support.domain.models import CustomerProfile


class CustomerProfileTool:
    """Expose the minimum customer profile lookup used by support."""

    def __init__(self, repository: FakeCustomerRepository) -> None:
        """Store the customer data boundary."""
        self._repository = repository

    async def get_customer_profile(self, user_id: str) -> CustomerProfile | None:
        """Retrieve a profile scoped by the caller-provided user identifier."""
        return await self._repository.get_profile(user_id)
