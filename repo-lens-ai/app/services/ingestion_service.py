from app.database.models.repository import Repository, IngestionStatus
from app.database.models.repository_file import RepositoryFile, FileStatus

from app.storage.base import FileStorage

from app.ingestion.github_ingestion import (
    get_repository_metadata, get_repository_tree, retrieve_repository_files, filter_repository_files, get_repository_commit
)

from app.services.github_service import verify_github_repository

from fastapi import HTTPException

from pathlib import Path

def check_existing_repository(
    repository: Repository
) -> bool:

    if repository.status == IngestionStatus.COMPLETED and repository.failed_files == 0:
        return True

    if repository.status == IngestionStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=409,
            detail="Repository ingestion is already in progress"
        )

    return False

async def get_existing_repository(
        full_name: str,
        commit_sha: str
) -> Repository | None:
    repository = await Repository.find_one(
        Repository.full_name == full_name,
        Repository.commit_sha == commit_sha
    )

    return repository


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
        repository: Repository,
        completed_files: int = 0,
        failed_files: int = 0
) -> Repository:
    repository.completed_files += completed_files
    repository.failed_files += failed_files

    await repository.save()
    return repository

def verify_repository_for_ingestion(url: str):
    repository_info = verify_github_repository(url)

    if not repository_info.exists:
        raise ValueError(repository_info.message)

    return repository_info

def extract_owner_and_repository(full_name: str) -> tuple[str, str]:
    owner, repository = full_name.split("/", maxsplit=1)
    return owner, repository

async def ingest_github_repository(url: str, storage: FileStorage) -> Repository:
    existing_repository = None
    repository_info = verify_repository_for_ingestion(url)
    owner, repository_name = extract_owner_and_repository(repository_info.full_name)
    metadata = get_repository_metadata(owner=owner,repository=repository_name)

    default_branch = metadata["default_branch"]

    commit_data = get_repository_commit(owner=owner, repository=repository_name, branch=default_branch)

    commit_sha = commit_data["sha"]
    tree_sha = commit_data["commit"]["tree"]["sha"]

    existing_repository = await get_existing_repository(
        full_name=repository_info.full_name,
        commit_sha=commit_sha
    )

    if existing_repository is not None:
        should_return = check_existing_repository(existing_repository)

        if should_return:
            return existing_repository

    try:
        tree_data = get_repository_tree(owner=owner, repository=repository_name, tree_sha=tree_sha)

        filtered_files = filter_repository_files(tree_data["tree"])

        ingestion_result = retrieve_repository_files(owner=owner, repository=repository_name, files=filtered_files)

        saved_repository = await persist_ingestion_results(
            full_name=repository_info.full_name,
            commit_sha=commit_sha,
            default_branch=default_branch,
            ingestion_results=ingestion_result,
            storage=storage
        )

        return saved_repository
    except Exception:
        if existing_repository is not None:
            existing_repository.status = IngestionStatus.FAILED
            await existing_repository.save()

        raise

async def persist_ingestion_results(
        full_name: str,
        commit_sha: str,
        default_branch: str, 
        ingestion_results: dict,
        storage: FileStorage
) -> Repository:

    successful_files = ingestion_results["successful_files"]
    failed_files = ingestion_results["failed_files"]


    existing_repository = await get_existing_repository(
        full_name=full_name, 
        commit_sha=commit_sha
    )
    total_files = len(successful_files) + len(failed_files)

    if existing_repository is None:

        repository = await create_repository_record(
            full_name=full_name,
            commit_sha=commit_sha,
            default_branch=default_branch,
            total_files=total_files
        )

    else:
        repository = existing_repository

        repository.total_files = total_files
        repository.completed_files = 0
        repository.failed_files = 0
        repository.status = IngestionStatus.IN_PROGRESS
        await repository.save()

        await delete_existing_repository_files(
            repository=repository,
            storage=storage
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

async def delete_existing_repository_files(
        repository: Repository,
        storage: FileStorage
) -> None:
    existing_files = await RepositoryFile.find(
        {"repository.$id": repository.id}
    ).to_list()

    for repository_file in existing_files:
        if repository_file.storage_path is not None:
            storage_key = (
                f"{repository.full_name}/{repository.commit_sha}/{repository_file.path}"
            )
            storage.delete_file(storage_key)

        await repository_file.delete()

async def get_successful_repository_files(repository: Repository) -> list[RepositoryFile]:
    repository_files = await RepositoryFile.find({
        "repository.$id": repository.id,
        "status" : FileStatus.COMPLETED
    }).to_list()

    return repository_files

async def extract_repository_file(
        repository_file: RepositoryFile,
        storage: FileStorage
) -> dict:

    content = storage.read_file(repository_file.storage_path)

    cleaned_content = preprocess_file_content(content=content)

    if not cleaned_content:
        return None

    return {
        "path": repository_file.path,
        "content" : cleaned_content,
        "extension" : Path(repository_file.path).suffix
    }


async def extract_repository_files(
    repository: Repository,
    storage: FileStorage
) -> dict:

    repository_files = await get_successful_repository_files(repository)

    extracted_files = []
    skipped_files = []

    for repository_file in repository_files:
        try:
            result = await extract_repository_file(
                repository_file=repository_file,
                storage=storage
            )

            if result is None:
                skipped_files.append({
                    "path": repository_file.path,
                    "reason": "File is empty"
                })
                continue

            extracted_files.append(result)
        except OSError as error:
            skipped_files.append({
                "path" : repository_file.path,
                "reason" : f"Unable to read file: {error}"
            })

    return {
        "extracted_files": extracted_files,
        "skipped_files": skipped_files
    }


def preprocess_file_content(content: str) -> str:
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    lines = [line.rstrip() for line in content.split("\n")]

    cleaned_lines = []

    for line in lines:
        if not line.strip() and (
            cleaned_lines and not cleaned_lines[-1].strip()
        ):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()