import pytest
import pytest_asyncio

from unittest.mock import patch

from app.database.connection import init_database, close_database
from app.database.models.repository import Repository
from app.database.models.repository_file import RepositoryFile

from app.services import ingestion_service

from app.schemas.repository import RepositoryInfo

from app.storage.local_storage import LocalStorage

@pytest_asyncio.fixture
async def database():
    await init_database(database_name="repolens_test")

    yield

    await RepositoryFile.find_all().delete()

    await Repository.find(
        Repository.full_name == "test/repolens-workflow"
    ).delete()

    await close_database()

@pytest.mark.asyncio
async def test_ingest_github_repository_workflow(database, tmp_path):

    storage = LocalStorage(base_dir=str(tmp_path))

    repository_info = RepositoryInfo(
        exists=True,
        full_name="test/repolens-workflow",
        description="Test repository",
        private=False
    )

    metadata = {
        "full_name" : "test/repolens-workflow",
        "default_branch" : "main"
    }

    commit_data = {
        "sha" : "commit123",
        "commit": {
            "tree" : {
                "sha": "tree123"
            }
        }
    }

    tree_data = {
        "tree" : [
            {
                "type": "blob",
                "path": "app/main.py",
                "size": 14,
                "sha": "file-sha-1"
            },
            {
                "type": "blob",
                "path": "app/config.py",
                "size": 20,
                "sha": "file-sha-2"
            }
        ],
        "truncated" : False
    }

    ingestion_results = {
        "successful_files": [
            {
                "path": "app/main.py",
                "content": "print('hello')",
                "size": 14,
                "sha": "file-sha-1"
            }
        ],
        "failed_files": [
            {
                "path": "app/config.py",
                "size": 20,
                "sha": "file-sha-2",
                "error": "Unable to download file"
            }
        ]
    }

    with (patch.object(ingestion_service, "verify_github_repository", return_value=repository_info),
          patch.object(ingestion_service, "get_repository_metadata", return_value=metadata),
          patch.object(ingestion_service, "get_repository_commit", return_value=commit_data),
          patch.object(ingestion_service, "get_repository_tree", return_value=tree_data),
          patch.object(ingestion_service, "retrieve_repository_files", return_value = ingestion_results)):

        repository = await ingestion_service.ingest_github_repository(
            url="https://github.com/test/repolens-workflow",
            storage=storage
        )

    assert repository.full_name == "test/repolens-workflow"
    assert repository.commit_sha == "commit123"
    assert repository.default_branch == "main"

    assert repository.total_files == 2
    assert repository.completed_files == 1
    assert repository.failed_files == 1
    assert repository.status.value == "COMPLETED"

    saved_content = storage.read_file(
        "test/repolens-workflow/commit123/app/main.py"
    )

    assert saved_content == "print('hello')"

    saved_files = await RepositoryFile.find_all().to_list()

    assert len(saved_files) == 2

