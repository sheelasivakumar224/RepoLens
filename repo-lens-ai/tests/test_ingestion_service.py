import pytest_asyncio

from app.database.connection import init_database, close_database
from app.database.models.repository import Repository, IngestionStatus
from app.database.models.repository_file import RepositoryFile, FileStatus

from app.services.ingestion_service import persist_ingestion_results

from app.storage.local_storage import LocalStorage

@pytest_asyncio.fixture
async def database():
    await init_database(database_name="repolens_test")

    yield

    await RepositoryFile.find_all().delete()
    await Repository.find(
        Repository.full_name == "test/repolens-orchestration"
    ).delete()

    await close_database()

async def test_persist_ingestion_results(database, tmp_path):

    ingestion_results = {
        "successful_files": [
            {
                "path": "app/main.py",
                "content": "print('hello')",
                "size": 14,
                "sha": "good123"
            }
        ],
        "failed_files" : [
            {
                "path": "app/config.py",
                "sha": "bad123",
                "size": 20,
                "error": "GitHub API request failed"
            }
        ]
    }

    storage = LocalStorage(base_dir=str(tmp_path))

    repository = await persist_ingestion_results(
        full_name="test/repolens-orchestration",
        commit_sha="abc123",
        default_branch="main",
        ingestion_results=ingestion_results,
        storage=storage
    )

    saved_repository = await Repository.get(repository.id)

    assert saved_repository.full_name == "test/repolens-orchestration"
    assert saved_repository.commit_sha == "abc123"
    assert saved_repository.default_branch == "main"
    assert saved_repository.total_files == 2
    assert saved_repository.completed_files == 1
    assert saved_repository.failed_files == 1
    assert saved_repository.status == IngestionStatus.COMPLETED

    successful_file = await RepositoryFile.find(
        RepositoryFile.path == "app/main.py"
    ).first_or_none()

    assert successful_file is not None
    assert successful_file.status == FileStatus.COMPLETED

    stored_content = storage.read_file(
        "test/repolens-orchestration/abc123/app/main.py"
    )

    assert stored_content == "print('hello')"

    failed_file = await RepositoryFile.find(
        RepositoryFile.path == "app/config.py"
    ).first_or_none()

    assert failed_file is not None
    assert failed_file.status == FileStatus.FAILED
    assert failed_file.error == "GitHub API request failed"