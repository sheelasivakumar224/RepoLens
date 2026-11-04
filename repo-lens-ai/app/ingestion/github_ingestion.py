import httpx
from pathlib import PurePosixPath
import base64

def get_repository_metadata(owner: str, repository: str) -> dict:
    url = f"https://api.github.com/repos/{owner}/{repository}"

    response = httpx.get(url, timeout=30)

    response.raise_for_status()
    return response.json()

def get_repository_tree(owner: str, repository:str, branch: str) -> list:
    url = (
        f"https://api.github.com/repos/{owner}/{repository}/git/trees/{branch}?recursive=1"
    )
    response = httpx.get(url, timeout=30)
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

def get_file_content(owner: str, repository: str, file_path: str) -> str:
    url = f"https://api.github.com/repos/{owner}/{repository}/contents/{file_path}"
    response = httpx.get(url, timeout=30)
    response.raise_for_status()

    file_data = response.json()

    if file_data.get("encoding") != "base64":
        raise ValueError("Unsupported file encoding")

    decoded_content = base64.b64decode(file_data["content"])

    return decoded_content.decode("utf-8")