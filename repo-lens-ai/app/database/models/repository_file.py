from enum import Enum 
from beanie import Document, Link

from app.database.models.repository import Repository

class FileStatus(str, Enum):
    PENDING="PENDING"
    COMPLETED="COMPLETED"
    FAILED="FAILED"

class RepositoryFile(Document):
    repository: Link[Repository] # Connects a file document to its parent repository document

    path: str
    github_sha: str # For file content comparison
    size: int

    storage_path: str | None=None

    status: FileStatus = FileStatus.PENDING
    error: str | None=None

    class Settings:
        name = "repository_files"