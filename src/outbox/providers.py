from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from outbox.repository import OutboxRepository


class OutboxProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def outbox_repository(self, session: AsyncSession) -> OutboxRepository:
        return OutboxRepository(session)
