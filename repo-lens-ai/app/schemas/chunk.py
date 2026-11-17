from pydantic import BaseModel, Field

class Chunk(BaseModel):
    repository_name: str
    file_path: str
    language: str # programming lanuguage/file type
    chunk_index: int = Field(ge=0)
    chunk_type: str
    name: str | None = None
    parent_name: str | None = None
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    content: str