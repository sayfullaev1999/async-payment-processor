from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Header, status

from domain.payments.commands import CreatePaymentCommand
from domain.payments.schemas import (
    CreatePaymentRequest,
    CreatePaymentResponse,
    PaymentResponse,
)
from domain.payments.service import PaymentService

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"],
)


@router.post(
    "",
    response_model=CreatePaymentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@inject
async def create_payment(
    data: CreatePaymentRequest,
    service: FromDishka[PaymentService],
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> CreatePaymentResponse:
    command = CreatePaymentCommand(
        amount=data.amount,
        currency=data.currency,
        description=data.description,
        metadata=data.metadata,
        webhook_url=str(data.webhook_url),
    )

    payment = await service.create(command, idempotency_key)

    return CreatePaymentResponse(
        payment_id=payment.id,
        status=payment.status,
        created_at=payment.created_at,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
)
@inject
async def get_payment(
    payment_id: UUID,
    service: FromDishka[PaymentService],
) -> PaymentResponse:
    payment = await service.get_by_id(payment_id)

    return PaymentResponse(
        payment_id=payment.id,
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description,
        metadata=payment.payment_metadata,
        status=payment.status,
        idempotency_key=payment.idempotency_key,
        webhook_url=payment.webhook_url,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )
