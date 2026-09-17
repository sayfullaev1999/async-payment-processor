import asyncio

from dishka_faststream import setup_dishka
from faststream.rabbit import RabbitBroker

from core.containers import worker_container
from infrastructure.messaging import consumers  # noqa: F401
from outbox.relay import OutboxRelay


async def main():
    async with worker_container() as scope:
        broker = await scope.get(RabbitBroker)
        outbox_relay = await scope.get(OutboxRelay)

        setup_dishka(worker_container, broker=broker)

        relay_task = asyncio.create_task(outbox_relay.start())

        await broker.start()

        try:
            await asyncio.Event().wait()
        finally:
            outbox_relay.stop()
            relay_task.cancel()
            await broker.stop()


if __name__ == '__main__':
    asyncio.run(main())
