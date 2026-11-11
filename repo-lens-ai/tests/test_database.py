import pytest
import pytest_asyncio

from app.database.connection import init_database, close_database
from app.database.models.repository import Repository, IngestionStatus

from app.services.ingestion_service import create_repository_record, update_repository_progress

# Initialize beanie before each test.
@pytest_asyncio.fixture
async def database():
    await init_database(database_name="repolens_test")
    yield
    await Repository.find(
        Repository.full_name == "test/repolens"
    ).delete()
    await close_database()


@pytest.mark.asyncio
async def test_insert_repository(database):
    repository = Repository(
        full_name = "test/repolens",
        commit_sha="abc123",
        default_branch="main",
    )

    await repository.insert()
    assert repository.id is not None


@pytest.mark.asyncio
async def test_get_repository(database):
    repository = Repository(
        full_name="test/repolens",
        commit_sha="abc123",
        default_branch="main"
    )

    await repository.insert()

    result = await Repository.get(repository.id)

    assert result is not None
    assert result.full_name == "test/repolens"

@pytest.mark.asyncio
async def test_update_repository(database):
    repository = Repository(
        full_name="test/repolens",
        commit_sha="abc123",
        default_branch="main"
    )

    await repository.insert()

    repository.status = IngestionStatus.IN_PROGRESS
    await repository.save()

    result = await Repository.get(repository.id)
    assert result.status == IngestionStatus.IN_PROGRESS

@pytest.mark.asyncio
async def test_delete_repository(database):
    repository = Repository(
        full_name="test/repolens",
        commit_sha="abc123",
        default_branch="main"
    )

    await repository.insert()
    await repository.delete()
    result = await Repository.get(repository.id)

    assert result is None


@pytest.mark.asyncio
async def test_create_repository_record(database):
    repository = await create_repository_record(
        full_name="test/repolens",
        commit_sha="abc123",
        default_branch="main",
        total_files=10
    )

    assert repository.id is not None
    assert repository.full_name == "test/repolens"
    assert repository.total_files == 10
    assert repository.status == IngestionStatus.IN_PROGRESS

@pytest.mark.asyncio
async def test_update_repository_progress(database):
    repository = await create_repository_record(
        full_name="test/repolens",
        commit_sha="abc123",
        default_branch="main",
        total_files=10
    )

    result = await update_repository_progress(
        repository=repository,
        completed_files=7,
        failed_files=3
    )

    saved_repository = await Repository.get(repository.id)

    assert result.completed_files == 7
    assert result.failed_files == 3

    assert saved_repository.completed_files == 7
    assert saved_repository.failed_files == 3