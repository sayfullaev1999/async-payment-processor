from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from domain.payments.repository import PaymentRepository
from domain.payments.service import PaymentService
from infrastructure.database.uow import UnitOfWork
from outbox.repository import OutboxRepository


class PaymentProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def payment_repository(self, session: AsyncSession) -> PaymentRepository:
        return PaymentRepository(session)

    @provide(scope=Scope.REQUEST)
    async def payment_service(
        self,
        payment_repository: PaymentRepository,
        outbox_repository: OutboxRepository,
        uow: UnitOfWork,
    ) -> PaymentService:
        return PaymentService(
            payment_repository=payment_repository,
            outbox_repository=outbox_repository,
            uow=uow,
        )
