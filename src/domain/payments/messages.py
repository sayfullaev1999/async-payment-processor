from uuid import UUID

from pydantic import BaseModel


class PaymentNewMessage(BaseModel):
    payment_id: UUID


class WebhookDeliveryMessage(BaseModel):
    payment_id: UUID
    webhook_url: str
    status: str
