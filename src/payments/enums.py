from enum import Enum


class PaymentStatus(Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PaymentCurrency(Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
