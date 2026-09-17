from dataclasses import dataclass
from decimal import Decimal

from domain.payments.enums import PaymentCurrency


@dataclass(frozen=True)
class CreatePaymentCommand:
    amount: Decimal
    currency: PaymentCurrency
    description: str
    metadata: dict
    webhook_url: str
