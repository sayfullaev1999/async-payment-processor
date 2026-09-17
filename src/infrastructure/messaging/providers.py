from dishka import Provider, Scope, provide
from faststream.rabbit import RabbitBroker

from infrastructure.messaging.broker import broker as rabbit_broker_instance


class MessagingProvider(Provider):
    scope = Scope.APP

    @provide
    def rabbit_broker(self) -> RabbitBroker:
        return rabbit_broker_instance
