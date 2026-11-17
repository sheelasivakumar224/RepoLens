import pytest
import pytest_asyncio

from unittest.mock import patch
from pathlib import Path

from app.database.connection import init_database, close_database
from app.database.models.repository import Repository
from app.database.models.repository_file import RepositoryFile, FileStatus

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

    successful_files = await ingestion_service.get_successful_repository_files(repository=repository)

    assert len(successful_files) == 1
    assert successful_files[0].path == "app/main.py"
    assert successful_files[0].status == FileStatus.COMPLETED

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

    extracted_file = await ingestion_service.extract_repository_file(
        repository_file=successful_files[0],
        storage=storage 
    )

    assert extracted_file["path"] == "app/main.py"
    assert extracted_file["content"] == "print('hello')"
    assert extracted_file["extension"] == ".py"

@pytest.mark.asyncio
async def test_duplicate_repository_submission(database, tmp_path):
    storage = LocalStorage(base_dir=str(tmp_path))

    repository_info = RepositoryInfo(
        exists = True,
        full_name="test/repolens-workflow",
        description="Test repository",
        private=False
    )

    metadata = {
        "full_name": "test/repolens-workflow",
        "default_branch": "main"
    }

    commit_data = {
        "sha": "commit123",
        "commit": {
            "tree": {
                "sha": "tree123"
            }
        }
    }

    tree_data = {
        "tree": [
            {
                "type": "blob",
                "path": "app/main.py",
                "size": 14,
                "sha": "file-sha-1"
            }
        ],
        "truncated": False
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
        "failed_files": []
    }
    with (
        patch.object(
            ingestion_service,
            "verify_github_repository",
            return_value=repository_info
        ),
        patch.object(
            ingestion_service,
            "get_repository_metadata",
            return_value=metadata
        ),
        patch.object(
            ingestion_service,
            "get_repository_commit",
            return_value=commit_data
        ),
        patch.object(
            ingestion_service,
            "get_repository_tree",
            return_value=tree_data
        ) as mock_tree,
        patch.object(
            ingestion_service,
            "retrieve_repository_files",
            return_value=ingestion_results
        ) as mock_retrieve
    ):

        first_result = await ingestion_service.ingest_github_repository(
            url="https://github.com/test/repolens-workflow",
            storage=storage
        )

        second_result = await ingestion_service.ingest_github_repository(
            url="https://github.com/test/repolens-workflow",
            storage=storage
        )

    assert first_result.id == second_result.id

    assert mock_tree.call_count == 1
    assert mock_retrieve.call_count == 1

    saved_files = await RepositoryFile.find_all().to_list()
    assert len(saved_files) == 1

    saved_repositories = await Repository.find_all().to_list()
    assert len(saved_repositories) == 1

@pytest.mark.asyncio
async def test_ingest_new_commit_for_existing_repository(database, tmp_path):

    storage = LocalStorage(base_dir=str(tmp_path))

    repository_info = RepositoryInfo(
        exists=True,
        full_name="test/repolens-workflow",
        description="Test repository",
        private=False
    )

    metadata = {
        "full_name": "test/repolens-workflow",
        "default_branch": "main"
    }

    first_commit = {
        "sha": "commit123",
        "commit": {"tree": {"sha": "tree123"}}
    }

    second_commit = {
        "sha": "commit456",
        "commit": {"tree": {"sha": "tree456"}}
    }

    tree_data = {
        "tree": [
            {
                "type": "blob",
                "path": "app/main.py",
                "size": 14,
                "sha": "file-sha-1"
            }
        ],
        "truncated": False
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
        "failed_files": []
    }

    with (
        patch.object(
            ingestion_service,
            "verify_github_repository",
            return_value=repository_info
        ),
        patch.object(
            ingestion_service,
            "get_repository_metadata",
            return_value=metadata
        ),
        patch.object(
            ingestion_service,
            "get_repository_commit",
            side_effect=[first_commit, second_commit]
        ),
        patch.object(
            ingestion_service,
            "get_repository_tree",
            return_value=tree_data
        ) as mock_tree,
        patch.object(
            ingestion_service,
            "retrieve_repository_files",
            return_value=ingestion_results
        ) as mock_retrieve
    ):
        first_result = await ingestion_service.ingest_github_repository(
            url="https://github.com/test/repolens-workflow",
            storage=storage
        )

        second_result = await ingestion_service.ingest_github_repository(
            url="https://github.com/test/repolens-workflow",
            storage=storage
        )

    assert first_result.id != second_result.id

    assert first_result.commit_sha == "commit123"
    assert second_result.commit_sha == "commit456"

    assert mock_tree.call_count == 2
    assert mock_retrieve.call_count == 2

    saved_repositories = await Repository.find_all().to_list()
    assert len(saved_repositories) == 2

    saved_files = await RepositoryFile.find_all().to_list()
    assert len(saved_files) == 2

    first_content = storage.read_file(
        "test/repolens-workflow/commit123/app/main.py"
    )

    second_content = storage.read_file(
        "test/repolens-workflow/commit456/app/main.py"
    )

    assert first_content == "print('hello')"
    assert second_content == "print('hello')"

@pytest.mark.asyncio
async def test_delete_existing_repository_files(database, tmp_path):
    repository = Repository(
        full_name = "test/repolens-workflow",
        commit_sha="abc123",
        default_branch="main"
    )
    await repository.insert()

    storage = LocalStorage(base_dir=str(tmp_path))

    storage_key = "test/repolens-workflow/abc123/app/main.py"

    saved_path = storage.save_file(storage_key, "print('Hello World')")

    repository_file = RepositoryFile(
        repository=repository,
        path="app/main.py",
        github_sha="file123",
        size=100,
        storage_path=saved_path
    )

    await repository_file.insert()

    await ingestion_service.delete_existing_repository_files(
        repository=repository,
        storage=storage
    )

    remaining_files = await RepositoryFile.find(
        {"repository.$id": repository.id}
    ).to_list()

    assert len(remaining_files) == 0
    assert not Path(saved_path).exists()

@pytest.mark.asyncio
async def test_retry_failed_repository(database, tmp_path):
    storage = LocalStorage(base_dir=str(tmp_path))
    
    repository_info = RepositoryInfo(
        exists=True,
        full_name="test/repolens-workflow",
        description="Test repository",
        private=False
    )

    metadata = {
        "full_name": "test/repolens-workflow",
        "default_branch": "main"
    }

    commit_data = {
        "sha": "commit123",
        "commit": {
            "tree": {
                "sha": "tree123"
            }
        }
    }

    tree_data = {
        "tree": [],
        "truncated": False
    }

    first_results = {
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
                "path": "requirements.txt",
                "size": 20,
                "sha": "file-sha-2",
                "error": "Download failed"
            }
        ]
    }

    second_results = {
        "successful_files": [
            {
                "path": "app/main.py",
                "content": "print('hello again')",
                "size": 20,
                "sha": "file-sha-1-new"
            },
            {
                "path": "requirements.txt",
                "content": "fastapi",
                "size": 7,
                "sha": "file-sha-2"
            }
        ],
        "failed_files": []
    }

    with (
        patch.object(
            ingestion_service,
            "verify_github_repository",
            return_value=repository_info
        ),
        patch.object(
            ingestion_service,
            "get_repository_metadata",
            return_value=metadata
        ),
        patch.object(
            ingestion_service,
            "get_repository_commit",
            return_value=commit_data
        ),
        patch.object(
            ingestion_service,
            "get_repository_tree",
            return_value=tree_data
        ),
        patch.object(
            ingestion_service,
            "retrieve_repository_files",
            side_effect=[first_results, second_results]
        )
    ):

        first_result = await ingestion_service.ingest_github_repository(
            url="https://github.com/test/repolens-workflow",
            storage=storage
        )

        # Simulate an overall ingestion failure.
        first_result.status = ingestion_service.IngestionStatus.FAILED
        await first_result.save()

        second_result = await ingestion_service.ingest_github_repository(
            url="https://github.com/test/repolens-workflow",
            storage=storage
        )

    assert first_result.id == second_result.id

    saved_repositories = await Repository.find_all().to_list()
    saved_files = await RepositoryFile.find_all().to_list()

    assert len(saved_repositories) == 1
    assert len(saved_files) == 2

    assert second_result.status == ingestion_service.IngestionStatus.COMPLETED
    assert second_result.total_files == 2
    assert second_result.completed_files == 2
    assert second_result.failed_files == 0

    file_paths = {file.path for file in saved_files}

    assert file_paths == {
        "app/main.py",
        "requirements.txt"
    }

@pytest.mark.asyncio
async def test_ingestion_failure_marks_existing_repository_as_failed(database):
    repository_info = RepositoryInfo(
        exists=True,
        full_name="test/repolens-workflow",
        description="Test repository",
        private=False
    )

    metadata = {
        "full_name": "test/repolens-workflow",
        "default_branch": "main"
    }

    commit_data = {
        "sha": "commit123",
        "commit": {
            "tree": {
                "sha": "tree123"
            }
        }
    }

    # Create an existing repository record.
    repository = await ingestion_service.create_repository_record(
        full_name="test/repolens-workflow",
        commit_sha="commit123",
        default_branch="main",
        total_files=2
    )

    # Simulate a previously failed ingestion.
    repository.status = ingestion_service.IngestionStatus.FAILED
    await repository.save()

    with (
        patch.object(
            ingestion_service,
            "verify_repository_for_ingestion",
            return_value=repository_info
        ),
        patch.object(
            ingestion_service,
            "get_repository_metadata",
            return_value=metadata
        ),
        patch.object(
            ingestion_service,
            "get_repository_commit",
            return_value=commit_data
        ),
        patch.object(
            ingestion_service,
            "get_repository_tree",
            side_effect=RuntimeError("Unexpected GitHub API error")
        )
    ):
        with pytest.raises(RuntimeError, match="Unexpected GitHub API error"):
            await ingestion_service.ingest_github_repository(
                url="https://github.com/test/repolens-workflow",
                storage=LocalStorage(base_dir=str(database))
            )

    saved_repository = await Repository.get(repository.id)

    assert saved_repository.status == ingestion_service.IngestionStatus.FAILED

def test_preprocess_file_content():
    content = (
        "# Application entry point    \r\n"
        "\r\n"
        "def main():    \r\n"
        "    print('Hello')    \r\n"
    )

    result = ingestion_service.preprocess_file_content(content=content)

    expected = (
        "# Application entry point\n"
        "\n"
        "def main():\n"
        "    print('Hello')"
    )

    assert result == expected

@pytest.mark.asyncio
async def test_extract_repository_file_preprocesses_content(database, tmp_path):
    storage = LocalStorage(base_dir=str(tmp_path))

    original_content = (
        "# Main file    \n"
        "\n"
        "def main():    \n"
        "    print('Hello')    \n"
    )

    storage_path = storage.save_file(
        "test_repo/main.py",
        original_content
    )

    repository = Repository(
        full_name="test/repo",
        commit_sha="test_sha",
        default_branch="main",
        total_files=1
    )

    await repository.insert()

    repository_file = RepositoryFile(
        repository=repository,
        path="main.py",
        storage_path=storage_path,
        github_sha="test_sha",
        size=len(original_content),
    )

    result = await ingestion_service.extract_repository_file(
        repository_file=repository_file,
        storage=storage
    )

    expected_content = (
        "# Main file\n"
        "\n"
        "def main():\n"
        "    print('Hello')"
    )

    print("ACTUAL:", repr(result["content"]))
    print("EXPECTED:", repr(expected_content))
    assert result["content"] == expected_content
    assert result["path"] == "main.py"
    assert result["extension"] == ".py"

@pytest.mark.asyncio
async def test_extract_repository_file_skips_empty_content(database, tmp_path):
    storage = LocalStorage(base_dir=str(tmp_path))

    storage_path = storage.save_file("test_repo/empty.py", "  \n\n  ")

    repository = Repository(
        full_name=f"test/{tmp_path.name}",
        commit_sha="test_sha",
        default_branch="main",
        total_files=1
    )

    await repository.insert()

    repository_file = RepositoryFile(
        repository=repository,
        path="empty.py",
        storage_path=storage_path,
        github_sha="empty_test_sha",
        size=8,
    )

    result = await ingestion_service.extract_repository_file(
        repository_file=repository_file,
        storage=storage
    )

    assert result is None

@pytest.mark.asyncio
async def test_extract_repository_files(database, tmp_path):
    storage = LocalStorage(base_dir=str(tmp_path))

    repository = Repository(
        full_name=f"test/{tmp_path.name}",
        commit_sha="extraction_test_sha",
        default_branch="main",
        total_files=2
    )
    await repository.insert()

    content = "def main():\n    print('Hello')"
    saved_path = storage.save_file(
        f"{repository.full_name}/{repository.commit_sha}/main.py",
        content
    )

    successful_file = RepositoryFile(
        repository=repository,
        path="main.py",
        github_sha="sha_1",
        size=len(content),
        storage_path=saved_path,
        status=FileStatus.COMPLETED
    )
    await successful_file.insert()

    empty_path = storage.save_file(
        f"{repository.full_name}/{repository.commit_sha}/empty.py",
        "   \n\n   "
    )

    empty_file = RepositoryFile(
        repository=repository,
        path="empty.py",
        github_sha="sha_2",
        size=8,
        storage_path=empty_path,
        status=FileStatus.COMPLETED
    )
    await empty_file.insert()

    result = await ingestion_service.extract_repository_files(
        repository=repository,
        storage=storage
    )
    assert len(result["extracted_files"]) == 1
    assert result["extracted_files"][0]["path"] == "main.py"

    assert len(result["skipped_files"]) == 1
    assert result["skipped_files"][0] == {
        "path": "empty.py",
        "reason": "File is empty"
    }


@pytest.mark.asyncio
async def test_extract_repository_files_skips_missing_file(database, tmp_path):
    storage = LocalStorage(base_dir=str(tmp_path))

    repository = Repository(
        full_name=f"test/{tmp_path.name}",
        commit_sha="missing_file_test_sha",
        default_branch="main",
        total_files=2
    )
    await repository.insert()

    content = "print('Hello')"

    saved_path = storage.save_file(
        f"{repository.full_name}/{repository.commit_sha}/main.py",
        content
    )

    valid_file = RepositoryFile(
        repository=repository,
        path="main.py",
        github_sha="sha_1",
        size=len(content),
        storage_path=saved_path,
        status=FileStatus.COMPLETED
    )
    await valid_file.insert()

    missing_file = RepositoryFile(
        repository=repository,
        path="missing.py",
        github_sha="sha_2",
        size=100,
        storage_path=str(tmp_path / "missing.py"),
        status=FileStatus.COMPLETED
    )
    await missing_file.insert()

    result = await ingestion_service.extract_repository_files(
        repository=repository,
        storage=storage
    )

    assert len(result["extracted_files"]) == 1
    assert result["extracted_files"][0]["path"] == "main.py"

    assert len(result["skipped_files"]) == 1
    assert result["skipped_files"][0]["path"] == "missing.py"
    assert result["skipped_files"][0]["reason"].startswith(
        "Unable to read file:"
    )