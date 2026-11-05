from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.routes import health, repository
from app.ingestion.github_ingestion import verify_github_authentication


@asynccontextmanager
async def lifespan(app: FastAPI):
    verify_github_authentication()
    yield

app = FastAPI(title="RepoLens AI API", version="1.0.0", lifespan=lifespan)


app.include_router(health.router)
app.include_router(repository.router, prefix="/api")