from datetime import datetime, timezone
from enum import Enum

from beanie import Document
from pydantic import Field

class IngestionStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Repository(Document):
    full_name: str
    commit_sha: str
    default_branch: str
    status: IngestionStatus = IngestionStatus.PENDING
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    created_at: datetime = Field(default_factory = lambda:  datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory = lambda:  datetime.now(timezone.utc))
    class Settings:
        name = "repositories"