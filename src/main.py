from dishka.integrations.fastapi import setup_dishka

from fastapi import FastAPI, Depends

from core.containers import app_container
from core.security import verify_api_key
from core.settings import settings
from core.logging.middleware import logging_middleware
from domain.payments.router import router as payments_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    dependencies=[Depends(verify_api_key)]
)

app.middleware("http")(logging_middleware)
app.include_router(payments_router)
setup_dishka(app_container, app)
