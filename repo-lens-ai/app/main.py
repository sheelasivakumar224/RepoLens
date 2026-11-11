from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.routes import health, repository
from app.ingestion.github_ingestion import verify_github_authentication
from app.database.connection import init_database, close_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    verify_github_authentication()
    await init_database()

    yield
    await close_database()

app = FastAPI(title="RepoLens AI API", version="1.0.0", lifespan=lifespan)


app.include_router(health.router)
app.include_router(repository.router, prefix="/api")