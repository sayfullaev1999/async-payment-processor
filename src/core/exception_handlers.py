from fastapi import Request, status, FastAPI
from fastapi.responses import JSONResponse

from domain.payments.exceptions import PaymentNotFoundError


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(PaymentNotFoundError, payment_not_found_handler)


async def payment_not_found_handler(
    request: Request,
    exc: PaymentNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Payment not found"},
    )
