from app.ingestion.github_ingestion import (
    get_repository_metadata,
    get_repository_tree,
    get_file_content,
    filter_repository_files,
    retrieve_repository_files, verify_github_authentication,
    github_request
)

from app.ingestion.github_ingestion import GITHUB_HEADERS

from unittest.mock import patch

import pytest
import binascii
import httpx

from app.main import app
from fastapi.testclient import TestClient



def test_filter_repository_files():
    tree = [
        {
            "path" : "main.py",
            "type" : "blob",
            "size" : 100,
            "sha" : "abc123"
        },
        {
            "path": "README.md",
            "type": "blob",
            "size": 200,
            "sha": "def456",
        },
        {
            "path": "image.png",
            "type": "blob",
            "size": 500,
            "sha": "ghi789",
        },
        {
            "path": "node_modules/package.py",
            "type": "blob",
            "size": 100,
            "sha": "jkl012",
        },
        {
            "path": "datasets/training.py",
            "type": "blob",
            "size": 100,
            "sha": "mno345",
        },
        {
            "path": "large.py",
            "type": "blob",
            "size": 6 * 1024 * 1024,
            "sha": "pqr678",
        },
        {
            "path": "src",
            "type": "tree",
        },
        {
            "path": "boundary.py",
            "type": "blob",
            "size": 5 * 1024 * 1024,
            "sha": "boundary123",
        }
    ]

    result = filter_repository_files(tree)

    result_paths = [file["path"] for file in result]

    assert result_paths == ["main.py", "README.md", "boundary.py"]

def test_get_file_content_small_file():
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

          assert content == "hello"

          expected_url = "https://api.github.com/repos/psf/requests/contents/README.md"

        # assert_called_once_with: was the mocked function called exactly once with the expected arguments.
          mock_get.assert_called_once_with(expected_url, headers=GITHUB_HEADERS, timeout=30)

def test_get_file_content_large_file():
     with patch("app.ingestion.github_ingestion.httpx.get") as mock_get:
          mock_response = mock_get.return_value
          mock_response.json.return_value = {
               "encoding" : "base64",
               "content" : "aGVsbG8="
          }

          content = get_file_content(
               owner="psf",
               repository="requests",
               file_path="large.py",
               sha="xyz789",
               size=2*1024*1024
          )

          assert content == "hello"

          expected_url = "https://api.github.com/repos/psf/requests/git/blobs/xyz789"

          mock_get.assert_called_once_with(expected_url, headers=GITHUB_HEADERS, timeout=30)

def test_get_file_content_invalid_base64():
     with patch("app.ingestion.github_ingestion.httpx.get") as mock_get:
          mock_response = mock_get.return_value
          mock_response.json.return_value = {
               "encoding" : "base64",
               "content" : "hello@123"
          }

          with pytest.raises(binascii.Error):
               get_file_content(
                    owner="psf",
                    repository="requests",
                    file_path="README.md",
                    sha="abc123",
                    size=100
               )

def test_get_repository_metadata():
     with patch("app.ingestion.github_ingestion.httpx.get") as mock_get:
          mock_response = mock_get.return_value
          expected_metadata = {
               "full_name" : "psf/requests",
               "default_branch" : "main",
               "description" : "A simple HTTP library"
          }

          mock_response.json.return_value = expected_metadata

          result = get_repository_metadata(
               owner="psf", repository="requests"
          )

          assert mock_get.call_args.kwargs["headers"] == GITHUB_HEADERS
          assert result == expected_metadata

          mock_get.assert_called_once_with("https://api.github.com/repos/psf/requests", headers=GITHUB_HEADERS, timeout=30)

def test_get_repository_tree():
     with patch("app.ingestion.github_ingestion.httpx.get") as mock_get:
        mock_response = mock_get.return_value
        expected_tree = {
                "tree": [
                    {
                        "path": "README.md",
                        "type": "blob",
                        "sha": "abc123",
                        "size": 100,
                    },
                    {
                        "path": "src",
                        "type": "tree",
                    },
                ],
                "truncated": False,
        }
        mock_response.json.return_value = expected_tree

        result = get_repository_tree(owner="psf", repository="requests", tree_sha="abc123")

        assert result == expected_tree

        mock_get.assert_called_once_with("https://api.github.com/repos/psf/requests/git/trees/abc123?recursive=1", headers = GITHUB_HEADERS, timeout=30)

def test_retrieve_repository_files_success():
    files = [
          {
            "path": "README.md",
            "sha": "abc123",
            "size": 100,
        },
        {
            "path": "main.py",
            "sha": "def456",
            "size": 200,
        },
    ]
    with patch("app.ingestion.github_ingestion.get_file_content") as mock_get_content:
        mock_get_content.side_effect = [
             "# Project README",
             "print('Hello World')"
        ]

        result = retrieve_repository_files(
             owner="psf",
             repository="requests",
             files=files
        )

        assert len(result["successful_files"]) == 2
        assert len(result["failed_files"]) == 0

        assert result["successful_files"][0]["content"] == "# Project README"
        assert result["successful_files"][1]["content"] == "print('Hello World')"

        assert mock_get_content.call_count == 2

def test_retrieve_repository_files_failed():
    files = [
        {
            "path": "README.md",
            "size": 100,
            "sha": "abc123",
        },
        {
            "path": "invalid.py",
            "size": 100,
            "sha": "def456",
        },
        {
            "path": "setup.py",
            "size": 100,
            "sha": "ghi789",
        },
    ]

    with patch("app.ingestion.github_ingestion.get_file_content") as mock_get_content:
        mock_get_content.side_effect = [
            "# Project README",
            httpx.HTTPStatusError(
                "Simulated download failure",
                request=httpx.Request(
                    "GET",
                    "https://api.github.com",
                ),
                response=httpx.Response(404),
            ),
            "print('Setup')"
        ]
        result = retrieve_repository_files(owner="psf", repository="requests", files=files)

        assert len(result["successful_files"]) == 2
        assert len(result["failed_files"]) == 1

        assert result["successful_files"][0]["path"] == "README.md"
        assert result["successful_files"][1]["path"] == "setup.py"

        assert result["failed_files"][0]["path"] == "invalid.py"

        assert mock_get_content.call_count == 3

def test_retrieve_repository_files_unexpected_error():
     files = [
          {
               "path" : "main.py",
               "size" : 100,
               "sha" : "abc123"
          }
     ]

     with patch("app.ingestion.github_ingestion.get_file_content") as mock_get_content:
          mock_get_content.side_effect = TypeError("Unexpected programming error")

          with pytest.raises(TypeError, match="Unexpected programming error"):
               retrieve_repository_files(owner="psf", repository="requests", files=files)

def test_verify_github_authentication_success():
     with patch("app.ingestion.github_ingestion.httpx.get") as mock_get:
          mock_response = mock_get.return_value
          mock_response.status_code = 200

          result = verify_github_authentication()

          assert result is True
          mock_response.raise_for_status.assert_called_once()

def test_verify_github_authentication_failure():
     with patch("app.ingestion.github_ingestion.httpx.get") as mock_get:
          mock_response = mock_get.return_value
          mock_response.raise_for_status.side_effect = (
               httpx.HTTPStatusError(
                    "401 Unauthorized",
                    request=httpx.Request("GET", "https://api.github.com/user"),
                    response=httpx.Response(
                         401, 
                         request=httpx.Request("GET", "https://api.github.com/user")
                    )
               )
          )

          with pytest.raises(httpx.HTTPStatusError):
               verify_github_authentication()

def test_application_startup_fails_without_github_authentication():
     with patch(
        "app.main.verify_github_authentication",
        side_effect=httpx.HTTPStatusError(
            "401 Unauthorized",
            request=httpx.Request(
                "GET", "https://api.github.com/user"
            ),
            response=httpx.Response(
                401,
                request=httpx.Request(
                    "GET", "https://api.github.com/user"
                ),
            ),
        ),
    ):
        with pytest.raises(httpx.HTTPStatusError):
            with TestClient(app):
                pass

def test_verify_github_authentication_missing_token():
     with patch("app.ingestion.github_ingestion.GITHUB_TOKEN", None):
          with patch("app.ingestion.github_ingestion.httpx.get") as mock_get:
            with pytest.raises(RuntimeError, match="GITHUB_TOKEN is missing"):
                    verify_github_authentication()

            mock_get.assert_not_called()

def test_github_request_success():
     with patch("app.ingestion.github_ingestion.httpx.get") as mock_get:
          mock_response = mock_get.return_value
          mock_response.status_code = 200
          mock_response.headers = {
               "x-ratelimit-remaining" : "100"
          }

          result = github_request("https://api.github.com/user")

          assert result == mock_response
          mock_response.raise_for_status.assert_called_once()
          mock_get.assert_called_once()

def test_github_request_primary_rate_limit():
     with patch("app.ingestion.github_ingestion.httpx.get") as mock_get:
          with patch("app.ingestion.github_ingestion.time.time", return_value = 1000):
               with patch("app.ingestion.github_ingestion.time.sleep") as mock_sleep:
                    rate_limited_response = httpx.Response(
                         403, 
                         headers={
                              "x-ratelimit-remaining":"0",
                              "x-ratelimit-reset" : "1060"
                         },
                         request=httpx.Request("GET", "https://api.github.com/user"),
                    )

                    success_response = httpx.Response(
                         200, 
                         request = httpx.Request("GET", "https://api.github.com/user"),
                    )

                    mock_get.side_effect = [
                         rate_limited_response,
                         success_response
                    ]

                    result = github_request("https://api.github.com/user")

                    assert result.status_code == 200
                    mock_sleep.assert_called_once_with(60)
                    assert mock_get.call_count == 2

def test_github_request_secondary_rate_limit():
    with patch("app.ingestion.github_ingestion.httpx.get") as mock_get:
        with patch("app.ingestion.github_ingestion.time.sleep") as mock_sleep:

            rate_limited_response = httpx.Response(
                429,
                headers={"Retry-After": "60"},
                json={"message": "Secondary rate limit"},
                request=httpx.Request("GET", "https://api.github.com/user"),
            )

            success_response = httpx.Response(
                200,
                request=httpx.Request("GET", "https://api.github.com/user"),
            )

            mock_get.side_effect = [
                rate_limited_response,
                success_response,
            ]

            result = github_request("https://api.github.com/user")

            assert result.status_code == 200
            mock_sleep.assert_called_once_with(60)
            assert mock_get.call_count == 2

def test_github_request_secondary_rate_limit_backoff():
    with patch("app.ingestion.github_ingestion.httpx.get") as mock_get:
        with patch("app.ingestion.github_ingestion.time.sleep") as mock_sleep:

            rate_limited_response = httpx.Response(
                403,
                json={"message": "You have exceeded a secondary rate limit."},
                request=httpx.Request("GET", "https://api.github.com/user"),
            )

            success_response = httpx.Response(
                200,
                request=httpx.Request("GET", "https://api.github.com/user"),
            )

            mock_get.side_effect = [
                rate_limited_response,
                success_response,
            ]

            result = github_request("https://api.github.com/user")

            assert result.status_code == 200
            mock_sleep.assert_called_once_with(60)
            assert mock_get.call_count == 2

def test_github_request_permission_error():
    with patch("app.ingestion.github_ingestion.httpx.get") as mock_get:
        with patch("app.ingestion.github_ingestion.time.sleep") as mock_sleep:

            error_response = httpx.Response(
                403,
                json={"message": "Resource not accessible by integration"},
                request=httpx.Request("GET", "https://api.github.com/user"),
            )

            mock_get.return_value = error_response

            with pytest.raises(httpx.HTTPStatusError):
                github_request("https://api.github.com/user")

            mock_get.assert_called_once()
            mock_sleep.assert_not_called()
        
def test_github_request_max_retries_exhausted():
    with patch("app.ingestion.github_ingestion.httpx.get") as mock_get:
        with patch("app.ingestion.github_ingestion.time.sleep") as mock_sleep:

            rate_limited_response = httpx.Response(
                403,
                json={"message": "You have exceeded a secondary rate limit."},
                request=httpx.Request("GET", "https://api.github.com/user"),
            )

            mock_get.return_value = rate_limited_response

            with pytest.raises(httpx.HTTPStatusError):
                github_request("https://api.github.com/user")

            assert mock_get.call_count == 4
            assert mock_sleep.call_count == 3
            assert [call.args[0] for call in mock_sleep.call_args_list] == [
                60, 120, 240
            ]