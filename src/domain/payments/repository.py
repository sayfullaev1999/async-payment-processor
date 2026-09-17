from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.payments.models import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        amount,
        currency,
        description: str,
        payment_metadata: dict,
        idempotency_key: str,
        webhook_url: str,
    ) -> Payment:
        payment = Payment(
            amount=amount,
            currency=currency,
            description=description,
            payment_metadata=payment_metadata,
            idempotency_key=idempotency_key,
            webhook_url=webhook_url,
        )

        self.session.add(payment)

        await self.session.flush()

        return payment

    async def get_by_id(self, id_: UUID) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(Payment.id == id_)
        )

        return result.scalar_one_or_none()

    async def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(
                Payment.idempotency_key == idempotency_key
            )
        )

        return result.scalar_one_or_none()
