from dishka import Provider, Scope, provide
from faststream.rabbit import RabbitBroker

from src.core.settings import settings


class MessagingProvider(Provider):
    scope = Scope.APP

    @provide
    def rabbit_broker(self) -> RabbitBroker:
        return RabbitBroker(settings.RABBITMQ_URL)
