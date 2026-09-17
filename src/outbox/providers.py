from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.database import Database
from faststream.rabbit import RabbitBroker

from outbox.relay import OutboxRelay
from outbox.repository import OutboxRepository


class OutboxProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def outbox_repository(self, session: AsyncSession) -> OutboxRepository:
        return OutboxRepository(session)

    @provide(scope=Scope.APP)
    def outbox_relay(self, broker: RabbitBroker, database: Database) -> OutboxRelay:
        return OutboxRelay(broker=broker, database=database)
