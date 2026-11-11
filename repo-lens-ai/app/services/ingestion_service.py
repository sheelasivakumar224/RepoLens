from app.database.models.repository import Repository, IngestionStatus
from app.database.models.repository_file import RepositoryFile, FileStatus
from app.storage.base import FileStorage

async def create_repository_record(
        full_name: str,
        commit_sha: str,
        default_branch: str,
        total_files: int
) -> Repository:
    repository = Repository(
        full_name = full_name,
        commit_sha = commit_sha,
        default_branch = default_branch,
        total_files = total_files,
        status = IngestionStatus.IN_PROGRESS
    )

    await repository.insert()

    return repository

async def save_successful_file(
        repository: Repository,
        file_info: dict,
        storage: FileStorage
) -> RepositoryFile:

    storage_key = (
        f"{repository.full_name}/{repository.commit_sha}/{file_info['path']}"
    )

    saved_path = storage.save_file(storage_key, file_info["content"])

    repository_file = RepositoryFile(
        repository=repository,
        path=file_info["path"],
        github_sha=file_info["sha"],
        size=file_info["size"],
        storage_path=saved_path,
        status=FileStatus.COMPLETED
    )

    await repository_file.insert()

    return repository_file

async def save_failed_file(
        repository: Repository,
        file_info: dict
) -> RepositoryFile:
    repository_file = RepositoryFile(
        repository = repository,
        path=file_info["path"],
        github_sha=file_info["sha"],
        size=file_info["size"],
        status=FileStatus.FAILED,
        error=file_info["error"]
    )

    await repository_file.insert()

    return repository_file

async def update_repository_progress(
        repository: RepositoryFile,
        completed_files: int = 0,
        failed_files: int = 0
) -> Repository:
    repository.completed_files += completed_files
    repository.failed_files += failed_files

    await repository.save()
    return repository

async def persist_ingestion_results(
        full_name: str,
        commit_sha: str,
        default_branch: str, 
        ingestion_results: dict,
        storage: FileStorage
) -> Repository:

    successful_files = ingestion_results["successful_files"]
    failed_files = ingestion_results["failed_files"]

    total_files = len(successful_files) + len(failed_files)

    repository = await create_repository_record(
        full_name=full_name,
        commit_sha=commit_sha,
        default_branch=default_branch,
        total_files=total_files
    )

    for file_info in successful_files:
        await save_successful_file(
            repository=repository,
            file_info=file_info,
            storage=storage
        )

    for file_info in failed_files:
        await save_failed_file(
            repository=repository,
            file_info=file_info
        )

    await update_repository_progress(
        repository=repository,
        completed_files=len(successful_files),
        failed_files=len(failed_files)
    )

    repository.status = IngestionStatus.COMPLETED
    await repository.save()

    return repository