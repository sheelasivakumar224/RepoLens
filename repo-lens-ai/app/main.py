from fastapi import FastAPI
from app.api.routes import health

app = FastAPI(title="RepoLens AI API", version="1.0.0")

app.include_router(health.router)