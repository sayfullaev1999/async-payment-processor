from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from domain.payments.enums import PaymentCurrency, PaymentStatus
from domain.payments.exceptions import PaymentNotFoundError
from domain.payments.models import Payment


@pytest.mark.asyncio
async def test_create_payment(
    service,
    payment_repository,
    outbox_repository,
    create_payment_command,
):
    payment = Payment(
        id=uuid4(),
        amount=create_payment_command.amount,
        currency=create_payment_command.currency,
        description=create_payment_command.description,
        payment_metadata=create_payment_command.metadata,
        status=PaymentStatus.PENDING,
        idempotency_key="test-key",
        webhook_url=str(create_payment_command.webhook_url),
    )

    payment_repository.create = AsyncMock(return_value=payment)
    outbox_repository.add = AsyncMock()

    result = await service.create(
        data=create_payment_command,
        idempotency_key="test-key",
    )

    assert result is payment
    assert result.status == PaymentStatus.PENDING

    payment_repository.create.assert_awaited_once_with(
        amount=Decimal("100.00"),
        currency=PaymentCurrency.USD,
        description="Test payment",
        payment_metadata={"order_id": "123"},
        idempotency_key="test-key",
        webhook_url="https://example.com/webhook",
    )

    outbox_repository.add.assert_awaited_once_with(
        event_type="payments.new",
        aggregate_id=payment.id,
        payload={"payment_id": str(payment.id)},
    )


@pytest.mark.asyncio
async def test_create_payment_returns_existing_payment_on_duplicate_idempotency_key(
    service,
    payment_repository,
    outbox_repository,
    create_payment_command,
):
    existing_payment = Payment(
        id=uuid4(),
        amount=Decimal("100.00"),
        currency=PaymentCurrency.USD,
        description="Existing payment",
        payment_metadata={},
        status=PaymentStatus.PENDING,
        idempotency_key="test-key",
        webhook_url="https://example.com/webhook",
    )

    payment_repository.create = AsyncMock(
        side_effect=IntegrityError(
            statement="duplicate",
            params={},
            orig=Exception(),
        )
    )
    payment_repository.get_by_idempotency_key = AsyncMock(
        return_value=existing_payment,
    )
    outbox_repository.add = AsyncMock()

    result = await service.create(
        data=create_payment_command,
        idempotency_key="test-key",
    )

    assert result is existing_payment

    payment_repository.get_by_idempotency_key.assert_awaited_once_with(
        "test-key",
    )

    outbox_repository.add.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_payment_by_id(
    service,
    payment_repository,
):
    payment = Payment(
        id=uuid4(),
        amount=Decimal("100.00"),
        currency=PaymentCurrency.USD,
        description="Test payment",
        payment_metadata={},
        status=PaymentStatus.PENDING,
        idempotency_key="test-key",
        webhook_url="https://example.com/webhook",
    )

    payment_repository.get_by_id = AsyncMock(return_value=payment)

    result = await service.get_by_id(payment.id)

    assert result is payment

    payment_repository.get_by_id.assert_awaited_once_with(payment.id)


@pytest.mark.asyncio
async def test_get_payment_by_id_raises_when_payment_not_found(
    service,
    payment_repository,
):
    payment_id = uuid4()

    payment_repository.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(PaymentNotFoundError, match="Payment not found"):
        await service.get_by_id(payment_id)

    payment_repository.get_by_id.assert_awaited_once_with(payment_id)