import pytest
import pytest_asyncio

from app.database.connection import init_database, close_database
from app.database.models.repository import Repository, IngestionStatus


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
