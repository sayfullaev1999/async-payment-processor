import asyncio

from faststream.rabbit import RabbitBroker

from src.core.settings import settings


async def main() -> None:
    broker = RabbitBroker(settings.RABBITMQ_URL)

    await broker.start()
    print("RabbitMQ connection: OK")

    await broker.stop()


if __name__ == "__main__":
    asyncio.run(main())
