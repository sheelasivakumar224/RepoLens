import pytest
import pytest_asyncio

from app.database.connection import init_database, close_database
from app.database.models.repository import Repository
from app.database.models.repository_file import RepositoryFile, FileStatus

from app.services.ingestion_service import create_repository_record, save_successful_file, save_failed_file

from app.storage.local_storage import LocalStorage

@pytest_asyncio.fixture
async def database():
    await init_database(database_name="repolens_test")

    yield

    await RepositoryFile.find_all().delete()
    await Repository.find(Repository.full_name == "test/repolens").delete()

    await close_database()

@pytest.mark.asyncio
async def test_insert_repository_file(database):
    repository = Repository(
        full_name="test/repolens",
        commit_sha="abc123",
        default_branch="main"
    )

    await repository.insert()

    repository_file = RepositoryFile(
        repository=repository,
        path="app/main.py",
        github_sha="file123",
        size=1024,
        storage_path="test/repolens/abc123/app/main.py"
    )

    await repository_file.insert()

    assert repository_file.id is not None
    assert repository_file.status == FileStatus.PENDING

@pytest.mark.asyncio
async def test_get_repository_file(database):
    repository = Repository(
        full_name="test/repolens",
        commit_sha="abc123",
        default_branch="main"
    )

    await repository.insert()

    repository_file = RepositoryFile(
        repository=repository,
        path="app/main.py",
        github_sha="file123",
        size=1024,
        storage_path="test/repolens/abc123/app/main.py"
    )

    await repository_file.insert()

    result = await RepositoryFile.get(repository_file.id)

    assert result is not None
    assert result.path == "app/main.py"
    assert result.github_sha == "file123"

@pytest.mark.asyncio
async def test_update_repository_file(database):
    repository = Repository(
        full_name="test/repolens",
        commit_sha="abc123",
        default_branch="main"
    )

    await repository.insert()

    repository_file = RepositoryFile(
        repository=repository,
        path="app/main.py",
        github_sha="file123",
        size=1024,
        storage_path="test/repolens/abc123/app/main.py"
    )

    await repository_file.insert()

    repository_file.status = FileStatus.COMPLETED
    await repository_file.save()

    result = await RepositoryFile.get(repository_file.id)

    assert result.status == FileStatus.COMPLETED

@pytest.mark.asyncio
async def test_delete_repository_file(database):
    repository = Repository(
        full_name="test/repolens",
        commit_sha="abc123",
        default_branch="main"
    )

    await repository.insert()

    repository_file = RepositoryFile(
        repository=repository,
        path="app/main.py",
        github_sha="file123",
        size=1024,
        storage_path="test/repolens/abc123/app/main.py"
    )

    await repository_file.insert()
    await repository_file.delete()

    result = await RepositoryFile.get(repository_file.id)

    assert result is None

@pytest.mark.asyncio
async def test_repository_file_link_resolution(database):
    repository = Repository(
        full_name="test/repolens",
        commit_sha="abc123",
        default_branch="main"
    )

    await repository.insert()

    repository_file = RepositoryFile(
        repository=repository,
        path="app/main.py",
        github_sha="file123",
        size=1024,
    )

    await repository_file.insert()

    result = await RepositoryFile.get(repository_file.id)

    assert result is not None

    await result.fetch_link(RepositoryFile.repository)

    assert result.repository.full_name == "test/repolens"

@pytest.mark.asyncio
async def test_save_successful_file(database, tmp_path):
    repository = await create_repository_record(
        full_name="test/repolens",
        commit_sha="abc123",
        default_branch="main",
        total_files=1
    )

    storage = LocalStorage(base_dir=str(tmp_path))

    file_info = {
        "path":"app/main.py",
        "content": "Hello its a test",
        "size":23,
        "sha":"file123"
    }

    result = await save_successful_file(
        repository=repository,
        file_info=file_info,
        storage=storage
    )

    assert result.id is not None
    assert result.path == "app/main.py"
    assert result.github_sha == "file123"
    assert result.status == FileStatus.COMPLETED

    saved_content = storage.read_file(
        "test/repolens/abc123/app/main.py"
    )

    assert saved_content == "Hello its a test"

@pytest.mark.asyncio
async def test_save_failed_file(database):
    repository = await create_repository_record(
        full_name="test/repolens",
        commit_sha="abc123",
        default_branch="main",
        total_files=1
    )

    file_info = {
        "path":"app/config.py",
        "size":23,
        "sha":"failed123",
        "error":"Github API request failed"
    }

    result = await save_failed_file(
        repository=repository,
        file_info=file_info
    )

    assert result.id is not None
    assert result.path == "app/config.py"
    assert result.github_sha == "failed123"
    assert result.status == FileStatus.FAILED
    assert result.error == "Github API request failed"
    assert result.storage_path is None # This ensures it is not stored in the local storage.
