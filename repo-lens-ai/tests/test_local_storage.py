from pathlib import Path

import pytest

from app.storage.local_storage import LocalStorage

@pytest.fixture
def storage(tmp_path):
    return LocalStorage(base_dir=str(tmp_path))

def test_save_file(storage, tmp_path):
    content = "print('Hello world!')"

    saved_path = storage.save_file("test_repo/main.py", content)

    assert Path(saved_path).exists()
    assert Path(saved_path).read_text(encoding="utf-8") == content

def test_read_file(storage):
    content = "print('Hello world!')"
    storage.save_file("test_repo/main.py", content)
    result = storage.read_file("test_repo/main.py")

    assert result == content

def test_delete_file(storage, tmp_path):
    storage.save_file("test_repo/main.py", "temporary content")
    storage.delete_file("test_repo/main.py")

    assert not (tmp_path/"test_repo"/"main.py").exists()

def test_prevent_path_traversal(storage):
    with pytest.raises(ValueError):
        storage.save_file("../../outside.txt", "database injection")