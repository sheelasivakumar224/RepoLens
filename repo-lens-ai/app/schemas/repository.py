from pydantic import BaseModel, HttpUrl, ConfigDict

from datetime import datetime

from app.database.models.repository import IngestionStatus

class RepositoryInfo(BaseModel):
    exists: bool
    full_name: str | None = None
    description: str | None = None
    private: bool | None = None
    message: str | None = None

class RepositoryRequest(BaseModel):
    url: HttpUrl

class ResponseIngestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    full_name: str
    commit_sha: str
    default_branch: str
    status: IngestionStatus
    total_files: int
    completed_files: int
    failed_files: int
    created_at: datetime
    updated_at: datetime