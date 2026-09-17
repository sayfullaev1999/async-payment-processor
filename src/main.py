from dishka.integrations.fastapi import setup_dishka

from fastapi import FastAPI

from core.containers import app_container
from core.settings import settings
from core.logging.middleware import logging_middleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
)

app.middleware("http")(logging_middleware)
setup_dishka(app_container, app)
