from faststream.rabbit import RabbitBroker, RabbitExchange, ExchangeType, RabbitQueue

from core.settings import settings


broker = RabbitBroker(settings.RABBITMQ_URL)

payments_exchange = RabbitExchange(
    "payments",
    type=ExchangeType.DIRECT,
    durable=True,
)

dlx_exchange = RabbitExchange(
    "payments.dlx",
    type=ExchangeType.DIRECT,
    durable=True,
)

payments_new_queue = RabbitQueue(
    "payments.new",
    durable=True,
    arguments={
        "x-dead-letter-exchange": "payments.dlx",
        "x-dead-letter-routing-key": "payments.new.dlq",
    },
)
payments_new_dlq = RabbitQueue(
    "payments.new.dlq",
    durable=True,
)


payments_webhook_queue = RabbitQueue(
    "payments.webhook",
    durable=True,
    routing_key="payments.webhook",
    arguments={
        "x-dead-letter-exchange": "payments.dlx",
        "x-dead-letter-routing-key": "payments.webhook.dlq",
    },
)
payments_webhook_dlq = RabbitQueue(
    "payments.webhook.dlq",
    durable=True,
    routing_key="payments.webhook.dlq",
)