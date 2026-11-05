from app.ingestion.github_ingestion import get_repository_metadata, get_repository_tree, filter_repository_files, get_file_content, retrieve_repository_files
from unittest.mock import patch
import httpx

# metadata = get_repository_metadata("psf", "requests")


# tree_response = get_repository_tree(owner="psf", repository="requests", branch=metadata["default_branch"])

# tree = tree_response["tree"]

# filtered_files = filter_repository_files(tree)

# results = retrieve_repository_files(owner="psf", repository="requests", files=filtered_files[:5])

# print("\nSuccessful files: ", len(results["successful_files"]))
# print("Failed files: ", len(results["failed_files"]))

# for file in results["successful_files"]:
#     print("\nFile: ", file["path"])
#     print("Content length: ", len(file["content"]))

with patch("app.ingestion.github_ingestion.httpx.get") as mock_get:
    mock_response = mock_get.return_value
    mock_response.json.return_value = {
        "encoding" : "base64",
        "content" : "aGVsbG8="
    }

    content = get_file_content(
        owner="psf",
        repository="requests",
        file_path="README.md",
        sha="abc123",
        size=100
    )

    print("\nSmall file test:")
    print("Content: ", content)
    print("API URL: ",mock_get.call_args[0][0])

with patch("app.ingestion.github_ingestion.httpx.get") as mock_get:
    mock_response = mock_get.return_value
    mock_response.json.return_value = {
        "encoding" : "base64",
        "content" : "aGVsbG8="
    }

    content = get_file_content(
        owner="psf",
        repository="requests",
        file_path="large_file.py",
        sha="xyz789",
        size=2*1024*1024
    )

    print("\nLarge file test:")
    print("Content: ", content)
    print("API URL: ",mock_get.call_args[0][0])




test_files = [
    {"path": "README.md", "size": 100, "sha":"abc123"},
    {"path": "invalid.py", "size": 100, "sha": "def456"},
    {"path": "setup.py", "size": 100, "sha":"ghi789"},
]

with patch(
    "app.ingestion.github_ingestion.get_file_content"
) as mock_get_content:

    mock_get_content.side_effect = [
        "# README content",
        httpx.HTTPStatusError(
            "Simulated download failure", 
            request=httpx.Request("GET", "https://api.github.com"),
            response=httpx.Response(404)
        ),
        "# Setup content",
    ]

    test_results = retrieve_repository_files(
        owner="psf",
        repository="requests",
        files=test_files,
        
    )

print("\nFailure handling test:")
print("Successful:", len(test_results["successful_files"]))
print("Failed:", len(test_results["failed_files"]))
print("Failed file:", test_results["failed_files"][0]["path"])