from pathlib import Path

from app.storage.base import FileStorage

class LocalStorage:
    def __init__(self, base_dir: str="data/repositories"):
        self.base_dir = Path(base_dir).resolve()

    def save_file(self, path: str, content: str) -> str:
        file_path = (self.base_dir/path).resolve()

        if not file_path.is_relative_to(self.base_dir):
            raise ValueError("Invalid Storage path")

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        return str(file_path)

    def read_file(self, path: str) -> str:
        file_path = (self.base_dir/path).resolve()

        if not file_path.is_relative_to(self.base_dir):
            raise ValueError("Invalid storage path")

        return file_path.read_text(encoding="utf-8")

    def delete_file(self, path: str) -> None:
        file_path = (self.base_dir/path).resolve()

        if not file_path.is_relative_to(self.base_dir):
            raise ValueError("Invalid storage path")

        if file_path.exists():
            file_path.unlink()