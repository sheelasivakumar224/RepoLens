from pydantic import BaseModel, HttpUrl

class RepositoryInfo(BaseModel):
    exists: bool
    full_name: str | None = None
    description: str | None = None
    private: bool | None = None
    message: str | None = None

class RepositoryRequest(BaseModel):
    url: HttpUrl