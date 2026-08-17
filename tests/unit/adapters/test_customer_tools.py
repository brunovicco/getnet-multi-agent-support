import pytest

from getnet_support.adapters.repositories.fake_customer_repository import FakeCustomerRepository
from getnet_support.adapters.tools.customer import CustomerProfileTool
from getnet_support.adapters.tools.terminal import TerminalStatusTool
from getnet_support.adapters.tools.transactions import RecentTransactionsTool


@pytest.mark.asyncio
async def test_known_customer_returns_profile() -> None:
    profile = await CustomerProfileTool(FakeCustomerRepository()).get_customer_profile(
        "cliente1988"
    )

    assert profile is not None
    assert profile.terminal_id == "GET-12345"


@pytest.mark.asyncio
async def test_unknown_customer_returns_none() -> None:
    profile = await CustomerProfileTool(FakeCustomerRepository()).get_customer_profile("missing")

    assert profile is None


@pytest.mark.asyncio
async def test_transactions_are_customer_scoped() -> None:
    transactions = await RecentTransactionsTool(FakeCustomerRepository()).get_recent_transactions(
        "cliente1988"
    )

    assert len(transactions) == 2
    assert {transaction.user_id for transaction in transactions} == {"cliente1988"}
    assert transactions[0].occurred_at > transactions[1].occurred_at


@pytest.mark.asyncio
async def test_terminal_corresponds_to_customer_assignment() -> None:
    terminal = await TerminalStatusTool(FakeCustomerRepository()).get_terminal_status("cliente1988")

    assert terminal is not None
    assert terminal.terminal_id == "GET-12345"
    assert terminal.connectivity == "disconnected"
