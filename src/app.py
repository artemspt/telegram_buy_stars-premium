from fastapi import FastAPI

from src.api import router
from src.logging import configure as configure_logging


def create_app() -> FastAPI:
    app = FastAPI()

    app.include_router(router)

    return app


configure_logging()

app = create_app()
