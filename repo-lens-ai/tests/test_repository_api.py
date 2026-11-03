from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.schemas.repository import RepositoryInfo

client = TestClient(app)

@patch("app.api.routes.repository.verify_github_repository")
def test_verify_repository_success(mock_verify):
    mock_verify.return_value = RepositoryInfo(
        exists = True, 
        full_name = "psf/requests",
        description = "Repo for testing",
        private = False
    )

    response = client.post("/api/repositories/verify", json={
        "url": "https://github.com/psf/requests"
    })

    assert response.status_code == 200
    assert response.json() == {
        "exists": True,
        "full_name": "psf/requests",
        "description": "Repo for testing",
        "private": False,
        "message": None
    }

    mock_verify.assert_called_once()

def test_verify_repository_invalid_request():
    response = client.post("/api/repositories/verify", json={
        "url": "invalid-url"
    })

    assert response.status_code == 422 

@patch("app.api.routes.repository.verify_github_repository")
def test_verify_repository_not_found(mock_verify):
    mock_verify.return_value = RepositoryInfo(
        exists = False,
        message = "Repository not found or is private"
    )

    response = client.post("/api/repositories/verify", json={
        "url": "https://github.com/unknown/repository"
    })

    assert response.status_code == 200
    assert response.json() == {
        "exists": False,
        "full_name": None,
        "description": None,
        "private": None,
        "message": "Repository not found or is private"
    }