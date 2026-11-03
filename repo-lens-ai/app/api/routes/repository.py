from fastapi import APIRouter

from app.schemas.repository import RepositoryInfo, RepositoryRequest
from app.services.github_service import verify_github_repository

router = APIRouter()

@router.post("/repositories/verify", response_model = RepositoryInfo)
def verify_repository(request: RepositoryRequest):
    return verify_github_repository(str(request.url))