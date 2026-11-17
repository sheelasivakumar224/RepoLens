from fastapi import APIRouter, Request

from app.schemas.repository import RepositoryInfo, RepositoryRequest, ResponseIngestionResponse
from app.services.github_service import verify_github_repository
from app.services.ingestion_service import ingest_github_repository

router = APIRouter()

@router.post("/repositories/verify", response_model = RepositoryInfo)
def verify_repository(request: RepositoryRequest):
    return verify_github_repository(str(request.url))

@router.post("/repositories/ingest", response_model = ResponseIngestionResponse)
async def ingest_respository(request: RepositoryRequest, app_request: Request):
    storage = app_request.app.state.storage

    return await ingest_github_repository(
        url = str(request.url),
        storage=storage
    )