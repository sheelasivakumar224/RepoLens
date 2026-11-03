from fastapi import FastAPI
from app.api.routes import health, repository

app = FastAPI(title="RepoLens AI API", version="1.0.0")

app.include_router(health.router)
app.include_router(repository.router, prefix="/api")