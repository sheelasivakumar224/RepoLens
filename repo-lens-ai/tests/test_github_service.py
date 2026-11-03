import pytest

from app.services.github_service import validate_github_url, verify_github_repository

from unittest.mock import Mock, patch
from github import GithubException

@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://github.com/psf/requests", True),
        ("https://github.com/tiangolo/fastapi", True),
        ("https://github.com/psf/requests.git", True),
        ("https://github.com/psf/requests/", True),
        ("http://github.com/psf/requests", False),
        ("https://google.com/psf/requests", False),
        ("https://github.com/psf", False),
        ("hello-world", False)
    ]
)
def test_validate_github_url(url, expected):
    assert validate_github_url(url) == expected

@patch("app.services.github_service.Github")
def test_verify_github_repository_success(mock_github):
    mock_repo = Mock()
    mock_repo.full_name = "psf/requests"
    mock_repo.description = "A simple, yet elegant HTTP library."
    mock_repo.private = False

    mock_github.return_value.get_repo.return_value = mock_repo

    result = verify_github_repository("https://github.com/psf/requests")

    assert result == {
        "exists" : True,
        "full_name" : "psf/requests",
        "description" : "A simple, yet elegant HTTP library.",
        "private" : False
    }

@patch("app.services.github_service.Github")
def test_verify_github_repository_not_found(mock_github):
    mock_github.return_value.get_repo.side_effect = GithubException(404, {"message": "Not Found"}, None)
    result = verify_github_repository(
        "https://github.com/unknown/repository"
    )

    assert result == {
        "exists" : False,
        "message" : "Repository not found or is private"
    }

@patch("app.services.github_service.Github")
def test_verify_github_repository_invalid_url(mock_github):
    result = verify_github_repository(
        "https://google.com/psf/requests"
    )

    assert result == {
        "exists" : False,
        "message" : "Invalid Github repository URL"
    }
    mock_github.assert_not_called()

@patch("app.services.github_service.Github")
def test_verify_github_repository_api_error(mock_github):
    mock_github.return_value.get_repo.side_effect = GithubException(500, {"message": "Internal Server Error"}, None)

    with pytest.raises(GithubException):
        verify_github_repository("https://github.com/psf/requests")