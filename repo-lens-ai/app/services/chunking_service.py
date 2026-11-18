from app.schemas.chunk import Chunk

from app.services.chunking.python_chunker import chunk_python_file

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

    return []