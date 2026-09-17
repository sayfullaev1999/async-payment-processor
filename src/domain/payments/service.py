from uuid import UUID

from sqlalchemy.exc import IntegrityError

from domain.payments.commands import CreatePaymentCommand
from domain.payments.models import Payment
from infrastructure.database.uow import UnitOfWork
from outbox.repository import OutboxRepository
from domain.payments.repository import PaymentRepository


class PaymentService:
    def __init__(
        self,
        payment_repository: PaymentRepository,
        outbox_repository: OutboxRepository,
        uow: UnitOfWork,
    ):
        self.payment_repository = payment_repository
        self.outbox_repository = outbox_repository
        self.uow = uow

    async def create(
        self,
        data: CreatePaymentCommand,
        idempotency_key: str,
    ) -> Payment:
        try:
            async with self.uow:
                payment = await self.payment_repository.create(
                    amount=data.amount,
                    currency=data.currency,
                    description=data.description,
                    payment_metadata=data.metadata,
                    idempotency_key=idempotency_key,
                    webhook_url=str(data.webhook_url),
                )

                await self.outbox_repository.add(
                    event_type="payments.new",
                    aggregate_id=payment.id,
                    payload={"payment_id": str(payment.id)},
                )
        except IntegrityError:
            return await self.payment_repository.get_by_idempotency_key(
                idempotency_key
            )

        return payment

    async def get_by_id(self, payment_id: UUID) -> Payment:
        payment = await self.payment_repository.get_by_id(payment_id)

        if not payment:
            # здесь позже добавим PaymentNotFoundError
            raise ValueError("Payment not found")

        return payment
