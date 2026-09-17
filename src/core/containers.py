from dishka import make_async_container
from dishka.integrations.fastapi import FastapiProvider

from infrastructure.database.providers import DatabaseProvider
from infrastructure.messaging.providers import MessagingProvider


app_container = make_async_container(
    FastapiProvider(),

    DatabaseProvider(),
    MessagingProvider()
)

