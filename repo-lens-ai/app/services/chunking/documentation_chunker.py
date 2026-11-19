from pathlib import Path

from app.schemas.chunk import Chunk

from app.services.chunking.chunking_utils import count_tokens, split_oversized_content