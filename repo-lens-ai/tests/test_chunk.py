from app.schemas.chunk import Chunk

def test_create_chunk():
    chunk = Chunk(
        repository_name="psf/requests",
        file_path="src/requests/auth.py",
        language="python",
        chunk_index=0,
        chunk_type="class",
        name="HTTPBasicAuth",
        start_line=10,
        end_line=50,
        content="class HTTPBasicAuth:\n    pass"
    )

    assert chunk.repository_name == "psf/requests"
    assert chunk.file_path == "src/requests/auth.py"
    assert chunk.chunk_index == 0
    assert chunk.name == "HTTPBasicAuth"
    assert chunk.start_line == 10
    assert chunk.end_line == 50