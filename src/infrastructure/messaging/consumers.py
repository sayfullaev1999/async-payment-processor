import asyncio
import logging
import random
from datetime import datetime, timezone

import httpx
from dishka_faststream import FromDishka, inject
from faststream import AckPolicy
from faststream.rabbit.annotations import RabbitMessage

from domain.payments.messages import PaymentNewMessage, WebhookDeliveryMessage
from domain.payments.enums import PaymentStatus
from domain.payments.repository import PaymentRepository
from infrastructure.database.uow import UnitOfWork
from infrastructure.messaging.broker import (
    broker,
    dlx_exchange,
    payments_new_dlq,
    payments_new_queue,
    payments_exchange,
    payments_webhook_dlq,
    payments_webhook_queue,
)
from infrastructure.messaging.retry import handle_with_retry
from outbox.repository import OutboxRepository

logger = logging.getLogger(__name__)


async def process_payment_new(
    message: PaymentNewMessage,
    payment_repository: PaymentRepository,
    outbox_repository: OutboxRepository,
    uow: UnitOfWork,
) -> None:
    async with uow:
        payment = await payment_repository.get_by_id(message.payment_id)

        if payment is None:
            return

        if payment.status != PaymentStatus.PENDING:
            return

        # Эмуляция обработки платёжным шлюзом
        await asyncio.sleep(random.uniform(2, 5))
        succeeded = random.random() < 0.9

        payment.status = PaymentStatus.SUCCEEDED if succeeded else PaymentStatus.FAILED
        payment.processed_at = datetime.now(timezone.utc)

        # Публикация webhook-уведомления идёт через Outbox в той же транзакции,
        # что и обновление статуса — иначе падение процесса между commit и
        # publish навсегда теряет уведомление клиента.
        await outbox_repository.add(
            event_type="payments.webhook",
            aggregate_id=payment.id,
            payload={
                "payment_id": str(payment.id),
                "webhook_url": payment.webhook_url,
                "status": payment.status.value,
            },
        )


@broker.subscriber(payments_new_queue, payments_exchange, ack_policy=AckPolicy.MANUAL)
@inject
async def handle_payment_new(
    message: PaymentNewMessage,
    msg: RabbitMessage,
    payment_repository: FromDishka[PaymentRepository],
    outbox_repository: FromDishka[OutboxRepository],
    uow: FromDishka[UnitOfWork],
) -> None:
    try:
        await process_payment_new(message, payment_repository, outbox_repository, uow)
        await msg.ack()

    except Exception:
        # техническая ошибка (БД недоступна, баг и т.п.) — не бизнес-провал платежа
        await handle_with_retry(msg, broker, payments_new_queue, payments_exchange, message)


async def process_webhook_delivery(
    message: WebhookDeliveryMessage,
    payment_repository: PaymentRepository,
    uow: UnitOfWork,
) -> None:
    async with uow:
        payment = await payment_repository.get_by_id(message.payment_id)

        # Идемпотентность против редоставки: если webhook уже был доставлен,
        # повторный POST на webhook_url не выполняется.
        if payment is None or payment.webhook_delivered_at is not None:
            return

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            message.webhook_url,
            json={
                "payment_id": str(message.payment_id),
                "status": message.status,
            },
        )
        response.raise_for_status()

    async with uow:
        payment = await payment_repository.get_by_id(message.payment_id)

        if payment is not None:
            payment.webhook_delivered_at = datetime.now(timezone.utc)


@broker.subscriber(payments_webhook_queue, payments_exchange, ack_policy=AckPolicy.MANUAL)
@inject
async def handle_webhook_delivery(
    message: WebhookDeliveryMessage,
    msg: RabbitMessage,
    payment_repository: FromDishka[PaymentRepository],
    uow: FromDishka[UnitOfWork],
) -> None:
    try:
        await process_webhook_delivery(message, payment_repository, uow)
        await msg.ack()

    except (httpx.HTTPError, httpx.TimeoutException):
        await handle_with_retry(msg, broker, payments_webhook_queue, payments_exchange, message)


# Подписчики на DLQ нужны не только для видимости упавших сообщений, но и чтобы
# FastStream реально задекларировал payments.dlx и обе .dlq очереди с биндингами —
# без активного subscriber/publisher на них они никогда не создаются в RabbitMQ.
@broker.subscriber(payments_new_dlq, dlx_exchange)
async def handle_payment_new_dlq(message: PaymentNewMessage) -> None:
    logger.error("Message moved to DLQ payments.new.dlq: %s", message)


@broker.subscriber(payments_webhook_dlq, dlx_exchange)
async def handle_webhook_delivery_dlq(message: WebhookDeliveryMessage) -> None:
    logger.error("Message moved to DLQ payments.webhook.dlq: %s", message)
