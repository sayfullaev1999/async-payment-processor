import asyncio
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
    payments_new_queue,
    payments_exchange,
    payments_webhook_queue,
)
from infrastructure.messaging.retry import handle_with_retry


@broker.subscriber(payments_new_queue, payments_exchange, ack_policy=AckPolicy.MANUAL)
@inject
async def handle_payment_new(
    message: PaymentNewMessage,
    msg: RabbitMessage,
    payment_repository: FromDishka[PaymentRepository],
    uow: FromDishka[UnitOfWork],
) -> None:
    try:
        async with uow:
            payment = await payment_repository.get_by_id(message.payment_id)

            if payment is None:
                await msg.ack()
                return

            if payment.status != PaymentStatus.PENDING:
                await msg.ack()
                return

            # Эмуляция обработки платёжным шлюзом
            await asyncio.sleep(random.uniform(2, 5))
            succeeded = random.random() < 0.9

            payment.status = PaymentStatus.SUCCEEDED if succeeded else PaymentStatus.FAILED
            payment.processed_at = datetime.now(timezone.utc)

        await broker.publish(
            WebhookDeliveryMessage(
                payment_id=payment.id,
                webhook_url=payment.webhook_url,
                status=payment.status,
            ),
            queue=payments_webhook_queue,
            exchange=payments_exchange,
        )

        await msg.ack()

    except Exception:
        # техническая ошибка (БД недоступна, баг и т.п.) — не бизнес-провал платежа
        await handle_with_retry(msg, broker, payments_new_queue, payments_exchange, message)


@broker.subscriber(payments_webhook_queue, payments_exchange, ack_policy=AckPolicy.MANUAL)
async def handle_webhook_delivery(message: WebhookDeliveryMessage, msg: RabbitMessage) -> None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                message.webhook_url,
                json={
                    "payment_id": str(message.payment_id),
                    "status": message.status,
                },
            )
            response.raise_for_status()

        await msg.ack()

    except (httpx.HTTPError, httpx.TimeoutException):
        await handle_with_retry(msg, broker, payments_webhook_queue, payments_exchange, message)
