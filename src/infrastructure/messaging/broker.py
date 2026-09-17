from faststream.rabbit import RabbitBroker

from src.core.settings import settings


broker = RabbitBroker(settings.RABBITMQ_URL)
