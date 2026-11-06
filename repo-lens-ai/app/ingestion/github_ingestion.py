import httpx
from pathlib import PurePosixPath
import base64
import time

import logging

import os
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

GITHUB_HEADERS = {
    "Authorization" : f"Bearer {GITHUB_TOKEN}",
    "Accept" : "application/vnd.github+json"
}

def verify_github_authentication() -> bool:
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN is missing. Configure it in your .env file")
    
    url = "https://api.github.com/user"

    response = httpx.get(url, headers=GITHUB_HEADERS, timeout=30)
    response.raise_for_status()
    return True


logger = logging.getLogger(__name__)


def github_request(url: str) -> httpx.Response:
    response = httpx.get(
        url, headers=GITHUB_HEADERS, timeout=30
    )

    remaining = response.headers.get("x-ratelimit-remaining")

    if remaining == "0":
        reset_time = int(response.headers["x-ratelimit-reset"])
        wait_time = max(0, reset_time - time.time())
        time.sleep(wait_time)

    response.raise_for_status()
    return response


def get_repository_metadata(owner: str, repository: str) -> dict:
    url = f"https://api.github.com/repos/{owner}/{repository}"

    response = github_request(url)

    response.raise_for_status()
    return response.json()

def get_repository_tree(owner: str, repository:str, branch: str) -> list:
    url = (
        f"https://api.github.com/repos/{owner}/{repository}/git/trees/{branch}?recursive=1"
    )
    response = github_request(url)
    response.raise_for_status()

    return response.json()

ALLOWED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".md", ".rst", ".txt",
    ".json", ".yaml", ".yml", ".toml",
    ".sql",
}

EXCLUDED_DIRECTORIES = {
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    "data",
    "datasets",
    "checkpoints",
}

# 1 KB = 1024 bytes, 1 MB = 1024 x 1024 bytes.
# Github API's size field is measured in bytes.

MAX_FILE_SIZE = 5 * 1024 * 1024

def filter_repository_files(tree: list) -> list:
    filtered_files = []

    for item in tree:
        if item["type"] != "blob":
            continue

        path = PurePosixPath(item["path"])

        # Whether the file extension is in the allowed list
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue

        # Whether the file is in excluded directory
        if any(
            part.lower() in EXCLUDED_DIRECTORIES for part in path.parts[:-1]
        ): 
            continue

        if item.get("size") is None:
            continue

        # Whether the file size exceeds 5MB
        if item["size"] > MAX_FILE_SIZE:
            continue

        filtered_files.append(item)

    return filtered_files

def get_file_content(owner: str, repository: str, file_path: str, sha: str, size: int) -> str:
    if size <= 1024 * 1024:
        url = f"https://api.github.com/repos/{owner}/{repository}/contents/{file_path}"
    else:
        url = f"https://api.github.com/repos/{owner}/{repository}/git/blobs/{sha}"
    response = github_request(url)
    response.raise_for_status()

    file_data = response.json()

    if file_data.get("encoding") != "base64":
        raise ValueError("Unsupported file encoding")

    # validate=True: Makes Base64 decoding stricter by rejecting invalid characters instead of silently ignoring them.
    decoded_content = base64.b64decode(file_data["content"], validate=True)

    return decoded_content.decode("utf-8")

def retrieve_repository_files(owner:str, repository: str, files: list) -> dict:

    successful_files = []
    failed_files = []

    for file in files:
        file_path = file["path"]

        try:
            content = get_file_content(owner = owner, repository = repository, file_path = file_path, sha=file["sha"], size=file["size"])
            successful_files.append({"path": file_path, "content": content, "size": file["size"]})
            logger.info("Successfully retrieved %s", file_path)

        except (httpx.HTTPError, ValueError, KeyError) as error:
            failed_files.append({"path": file_path, "error": str(error)})
            logger.error("Failed to retrieve %s: %s", file_path, error)


    return {
        "successful_files" : successful_files,
        "failed_files" : failed_files
    }