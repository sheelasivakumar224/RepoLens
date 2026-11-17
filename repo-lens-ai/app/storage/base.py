from typing import Protocol

class FileStorage(Protocol):
    def save_file(self, path: str, content: str) -> str:
        '''
        Save repository file content
        '''
        ...

    def read_file(self, path: str) -> str:
        '''
        REad previously saved content
        '''
        ...

    def delete_file(self, path: str) -> None:
        '''
        Delete the stored file
        '''
        ...