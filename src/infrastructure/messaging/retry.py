import asyncio
import logging

from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue
from faststream.rabbit.annotations import RabbitMessage
from pydantic import BaseModel

logger = logging.getLogger(__name__)

RETRY_HEADER = "x-retry-count"
MAX_RETRIES = 3
BASE_DELAY = 1.0  # 1s, 2s, 4s


async def handle_with_retry(
    msg: RabbitMessage,
    broker: RabbitBroker,
    queue: RabbitQueue,
    exchange: RabbitExchange,
    body: BaseModel,
) -> None:
    """
    Вызывается из except-блока consumer'а при технической ошибке.
    Если попыток меньше MAX_RETRIES — republish с задержкой и увеличенным счётчиком.
    Иначе — nack(requeue=False), брокер сам отправит в DLQ через x-dead-letter-exchange.
    """
    current_retry = int(msg.headers.get(RETRY_HEADER, 0))

    if current_retry >= MAX_RETRIES:
        logger.warning(
            "Message exceeded max retries (%s), sending to DLQ: %s",
            MAX_RETRIES,
            body,
        )
        await msg.nack(requeue=False)
        return

    next_retry = current_retry + 1
    delay = BASE_DELAY * (2 ** current_retry)  # 1s, 2s, 4s

    logger.warning(
        "Retry %s/%s for message after %.1fs: %s",
        next_retry,
        MAX_RETRIES,
        delay,
        body,
    )

    await asyncio.sleep(delay)

    await broker.publish(
        body,
        queue=queue,
        exchange=exchange,
        headers={RETRY_HEADER: str(next_retry)},
    )

    await msg.ack()
