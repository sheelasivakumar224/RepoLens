from urllib.parse import urlparse
from github import Github, GithubException

def validate_github_url(url:str) -> bool:
    parsed_url = urlparse(url)

    if parsed_url.scheme != "https":
        return False

    if parsed_url.netloc !="github.com":
        return False

    path_parts = parsed_url.path.strip("/").split("/")

    if len(path_parts) != 2:
        return False

    owner, repository = path_parts

    if repository.endswith(".git"):
        repository = repository[:-4]

    if not owner or not repository:
        return False

    return True

def verify_github_repository(url: str) -> dict:
    if not validate_github_url(url):
        return {
            "exists" : False,
            "message" :"Invalid Github repository URL"
        }

    parsed_url = urlparse(url)
    owner, repository = parsed_url.path.strip("/").split("/")

    if repository.endswith(".git"):
        repository = repository[:-4]

    github = Github()
    try:
        repo = github.get_repo(f"{owner}/{repository}")

        return {
            "exists": True,
            "full_name" : repo.full_name,
            "description" : repo.description,
            "private" : repo.private
        }
    except GithubException as error:
        if error.status == 404:
            return {
                "exists" : False,
                "message" : "Repository not found or is private"
            }

        raise