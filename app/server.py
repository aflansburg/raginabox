from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import Settings
from app.core.embeddings import EmbeddingService
from app.core.vectorstore import VectorStore
from app.routes.api import router

BASE_DIR = Path(__file__).resolve().parent


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    app = FastAPI(title="raginabox", version="0.1.0")

    app.state.settings = settings
    app.state.vector_store = VectorStore()
    app.state.embedding_service = EmbeddingService(
        base_url=settings.embedding_base_url,
        model=settings.embedding_model,
    )
    app.state.templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
    app.mount("/documents", StaticFiles(directory=str(BASE_DIR.parent / "documents")), name="documents")
    app.include_router(router)

    return app
