from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.payments.commands import CreatePaymentCommand
from domain.payments.service import PaymentService
from domain.payments.enums import PaymentCurrency


@pytest.fixture
def payment_repository():
    return MagicMock()


@pytest.fixture
def outbox_repository():
    return MagicMock()


@pytest.fixture
def uow():
    mock = MagicMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=False)
    return mock


@pytest.fixture
def service(payment_repository, outbox_repository, uow):
    return PaymentService(
        payment_repository=payment_repository,
        outbox_repository=outbox_repository,
        uow=uow,
    )


@pytest.fixture
def create_payment_command():
    return CreatePaymentCommand(
        amount=Decimal("100.00"),
        currency=PaymentCurrency.USD,
        description="Test payment",
        metadata={"order_id": "123"},
        webhook_url="https://example.com/webhook",
    )
