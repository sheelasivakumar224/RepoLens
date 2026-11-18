from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

def count_tokens(content: str) -> int:
    tokens = tokenizer.encode(content, add_special_tokens = False)
    return len(tokens)

def split_oversized_content(content:str, max_tokens: int = 254, overlap: int = 30) -> list[str]:
    tokens = tokenizer.encode(content, add_special_tokens=False)

    chunks = []
    start = 0

    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))

        chunk_tokens = tokens[start: end]

        chunk_content = tokenizer.decode(chunk_tokens, skip_special_tokens = True)

        chunks.append(chunk_content)

        if end == len(tokens):
            break

        start = end - overlap

    return chunks
