from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from domain.payments.enums import PaymentCurrency, PaymentStatus
from domain.payments.messages import PaymentNewMessage, WebhookDeliveryMessage
from domain.payments.models import Payment
from infrastructure.messaging.consumers import (
    process_payment_new,
    process_webhook_delivery,
)


def _make_payment(**overrides):
    defaults = dict(
        id=uuid4(),
        amount=Decimal("100.00"),
        currency=PaymentCurrency.USD,
        description="Test payment",
        payment_metadata={},
        status=PaymentStatus.PENDING,
        idempotency_key="test-key",
        webhook_url="https://example.com/webhook",
    )
    defaults.update(overrides)
    return Payment(**defaults)


def _patched_gateway(succeeded: bool):
    return (
        patch("infrastructure.messaging.consumers.asyncio.sleep", AsyncMock()),
        patch("infrastructure.messaging.consumers.random.uniform", return_value=0),
        patch(
            "infrastructure.messaging.consumers.random.random",
            return_value=0.0 if succeeded else 0.99,
        ),
    )


@pytest.mark.asyncio
async def test_process_payment_new_marks_succeeded_and_writes_webhook_outbox_event(
    payment_repository, outbox_repository, uow,
):
    payment = _make_payment()
    payment_repository.get_by_id = AsyncMock(return_value=payment)
    outbox_repository.add = AsyncMock()

    sleep_p, uniform_p, random_p = _patched_gateway(succeeded=True)
    with sleep_p, uniform_p, random_p:
        await process_payment_new(
            PaymentNewMessage(payment_id=payment.id),
            payment_repository,
            outbox_repository,
            uow,
        )

    assert payment.status == PaymentStatus.SUCCEEDED
    assert payment.processed_at is not None

    outbox_repository.add.assert_awaited_once_with(
        event_type="payments.webhook",
        aggregate_id=payment.id,
        payload={
            "payment_id": str(payment.id),
            "webhook_url": payment.webhook_url,
            "status": "succeeded",
        },
    )


@pytest.mark.asyncio
async def test_process_payment_new_marks_failed_on_simulated_gateway_error(
    payment_repository, outbox_repository, uow,
):
    payment = _make_payment()
    payment_repository.get_by_id = AsyncMock(return_value=payment)
    outbox_repository.add = AsyncMock()

    sleep_p, uniform_p, random_p = _patched_gateway(succeeded=False)
    with sleep_p, uniform_p, random_p:
        await process_payment_new(
            PaymentNewMessage(payment_id=payment.id),
            payment_repository,
            outbox_repository,
            uow,
        )

    assert payment.status == PaymentStatus.FAILED
    outbox_repository.add.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_payment_new_skips_missing_payment(
    payment_repository, outbox_repository, uow,
):
    payment_repository.get_by_id = AsyncMock(return_value=None)
    outbox_repository.add = AsyncMock()

    await process_payment_new(
        PaymentNewMessage(payment_id=uuid4()),
        payment_repository,
        outbox_repository,
        uow,
    )

    outbox_repository.add.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_payment_new_is_idempotent_against_redelivery(
    payment_repository, outbox_repository, uow,
):
    # Сообщение payments.new пришло повторно (redelivery), но платёж уже обработан.
    payment = _make_payment(status=PaymentStatus.SUCCEEDED)
    payment_repository.get_by_id = AsyncMock(return_value=payment)
    outbox_repository.add = AsyncMock()

    await process_payment_new(
        PaymentNewMessage(payment_id=payment.id),
        payment_repository,
        outbox_repository,
        uow,
    )

    outbox_repository.add.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_webhook_delivery_sends_request_and_marks_delivered(
    payment_repository, uow,
):
    payment = _make_payment(status=PaymentStatus.SUCCEEDED)
    payment_repository.get_by_id = AsyncMock(return_value=payment)

    message = WebhookDeliveryMessage(
        payment_id=payment.id,
        webhook_url=payment.webhook_url,
        status="succeeded",
    )

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("infrastructure.messaging.consumers.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await process_webhook_delivery(message, payment_repository, uow)

    mock_client.post.assert_awaited_once_with(
        payment.webhook_url,
        json={"payment_id": str(payment.id), "status": "succeeded"},
    )
    assert payment.webhook_delivered_at is not None


@pytest.mark.asyncio
async def test_process_webhook_delivery_is_idempotent_against_redelivery(
    payment_repository, uow,
):
    delivered_at = datetime.now(timezone.utc)
    payment = _make_payment(
        status=PaymentStatus.SUCCEEDED,
        webhook_delivered_at=delivered_at,
    )
    payment_repository.get_by_id = AsyncMock(return_value=payment)

    message = WebhookDeliveryMessage(
        payment_id=payment.id,
        webhook_url=payment.webhook_url,
        status="succeeded",
    )

    with patch("infrastructure.messaging.consumers.httpx.AsyncClient") as mock_client_cls:
        await process_webhook_delivery(message, payment_repository, uow)

    # POST на webhook_url не должен уйти повторно
    mock_client_cls.assert_not_called()
    assert payment.webhook_delivered_at == delivered_at


@pytest.mark.asyncio
async def test_process_webhook_delivery_skips_missing_payment(
    payment_repository, uow,
):
    payment_repository.get_by_id = AsyncMock(return_value=None)

    message = WebhookDeliveryMessage(
        payment_id=uuid4(),
        webhook_url="https://example.com/webhook",
        status="succeeded",
    )

    with patch("infrastructure.messaging.consumers.httpx.AsyncClient") as mock_client_cls:
        await process_webhook_delivery(message, payment_repository, uow)

    mock_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_process_webhook_delivery_propagates_http_errors_for_retry(
    payment_repository, uow,
):
    payment = _make_payment(status=PaymentStatus.SUCCEEDED)
    payment_repository.get_by_id = AsyncMock(return_value=payment)

    message = WebhookDeliveryMessage(
        payment_id=payment.id,
        webhook_url=payment.webhook_url,
        status="succeeded",
    )

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

    with patch("infrastructure.messaging.consumers.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(httpx.TimeoutException):
            await process_webhook_delivery(message, payment_repository, uow)

    assert payment.webhook_delivered_at is None
