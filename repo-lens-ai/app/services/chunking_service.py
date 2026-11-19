from app.schemas.chunk import Chunk

from app.services.chunking.python_chunker import chunk_python_file
from app.services.chunking.javascript_chunker import chunk_javascript_file
from app.services.chunking.typescript_chunker import chunk_typescript_file

def chunk_repository_file(
    extracted_file: dict,
    repository_name: str
) -> list[Chunk]:
    extension = extracted_file["extension"]

    if extension == ".py":
        return chunk_python_file(
            extracted_file=extracted_file,
            repository_name=repository_name
        )
    elif extension == ".js":
        return chunk_javascript_file(
            extracted_file=extracted_file,
            repository_name=repository_name
        )

    elif extension in [".ts", ".tsx"]:
        return chunk_typescript_file(
            extracted_file=extracted_file,
            repository_name=repository_name
        )

    return []