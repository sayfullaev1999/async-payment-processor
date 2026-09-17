import asyncio
import logging

from faststream.rabbit import RabbitBroker

from infrastructure.database.database import Database
from infrastructure.messaging.broker import payments_exchange
from outbox.repository import OutboxRepository

logger = logging.getLogger(__name__)


class OutboxRelay:
    def __init__(
        self,
        broker: RabbitBroker,
        database: Database,
        poll_interval: float = 2.0,
        batch_size: int = 100,
    ):
        self._broker = broker
        self._database = database
        self._poll_interval = poll_interval
        self._batch_size = batch_size
        self._running = False

    async def start(self) -> None:
        self._running = True
        while self._running:
            try:
                await self._process_batch()
            except Exception:
                logger.exception("Outbox relay batch failed")
            await asyncio.sleep(self._poll_interval)

    def stop(self) -> None:
        self._running = False

    async def _process_batch(self) -> None:
        async with self._database.session_factory() as session:
            outbox_repo = OutboxRepository(session)
            pending = await outbox_repo.get_pending(limit=self._batch_size)

            for event in pending:
                await self._broker.publish(
                    event.payload,
                    exchange=payments_exchange,
                    routing_key=event.event_type,
                )
                await outbox_repo.mark_published(event.id)

            await session.commit()
