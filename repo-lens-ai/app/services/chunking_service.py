from app.schemas.chunk import Chunk

import tree_sitter
import tree_sitter_python

from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

def count_tokens(content: str) -> int:
    tokens = tokenizer.encode(content, add_special_tokens = False)
    return len(tokens)


def extract_attribute_name(member) -> str | None:
    assignment_node = member.named_children[0]

    attribute_name_node = assignment_node.child_by_field_name("left")

    if attribute_name_node is None:
        return None

    return attribute_name_node.text.decode("utf-8")


def chunk_repository_file(
        extracted_file: dict,
        repository_name: str
) -> list[Chunk]:
    content = extracted_file["content"]
    file_path = extracted_file["path"]
    extension = extracted_file["extension"]

    if extension != ".py":
        return []

    structures = extract_python_structures(content)

    standalone_functions = [structure for structure in structures if structure["type"]=="function_definition" and structure["parent_name"] is None ]

    classes = [structure for structure in structures if structure["type"] == "class_definition" and structure["parent_name"] is None]

    chunks = []

    for structure in classes:
        if count_tokens(structure["content"]) <= 254:
            chunk = Chunk(
                repository_name=repository_name,
                file_path=file_path,
                language="python",
                chunk_index=len(chunks),
                chunk_type="class",
                name=structure["name"],
                parent_name=structure["parent_name"],
                start_line=structure["start_line"],
                end_line=structure["end_line"],
                content=structure["content"]
            )

            chunks.append(chunk)
        else:
            members = extract_class_members(structure["node"])

            for member in members:
                if member.type == "expression_statement":
                    attribute_name = extract_attribute_name(member)

                    chunk = Chunk(
                        repository_name=repository_name,
                        file_path=file_path,
                        language="python",
                        chunk_index=len(chunks),
                        chunk_type="attribute",
                        name=attribute_name,
                        parent_name=structure["name"],
                        start_line=member.start_point.row + 1,
                        end_line=member.end_point.row + 1,
                        content=member.text.decode("utf-8")
                    )

                    chunks.append(chunk)
                    continue

                if member.type == "decorated_definition":
                    definition_node = member.child_by_field_name("definition")
                    member_name_node = definition_node.child_by_field_name("name")
                else:
                    member_name_node = member.child_by_field_name("name")

                member_name = member_name_node.text.decode("utf-8")

                member_content = member.text.decode("utf-8")

                if count_tokens(member_content) <= 254:
                    chunk = Chunk(
                        repository_name=repository_name,
                        file_path=file_path,
                        language="python",
                        chunk_index=len(chunks),
                        chunk_type="method",
                        name=member_name,
                        parent_name=structure["name"],
                        start_line=member.start_point.row + 1,
                        end_line=member.end_point.row + 1,
                        content=member_content
                    )
                    chunks.append(chunk)
                else:
                    split_contents = split_oversized_content(member_content)

                    for split_content in split_contents:
                        chunk = Chunk(
                            repository_name=repository_name,
                            file_path=file_path,
                            language="python",
                            chunk_index=len(chunks),
                            chunk_type="method",
                            name=member_name,
                            parent_name=structure["name"],
                            start_line=member.start_point.row + 1,
                            end_line=member.end_point.row + 1,
                            content=split_content
                        )

                        chunks.append(chunk)

    for structure in standalone_functions:
        if count_tokens(structure["content"]) <= 254:
            chunk = Chunk(
                repository_name=repository_name,
                file_path=file_path,
                language="python",
                chunk_index=len(chunks),
                chunk_type="function",
                name=structure["name"],
                parent_name=None,
                start_line=structure["start_line"],
                end_line=structure["end_line"],
                content=structure["content"]
            )

            chunks.append(chunk)
        else: 
            split_contents = split_oversized_content(structure["content"])

            for split_content in split_contents:
                chunk = Chunk(
                    repository_name=repository_name,
                    file_path=file_path,
                    language="python",
                    chunk_index=len(chunks),
                    chunk_type="function",
                    name=structure["name"],
                    parent_name=None,
                    start_line=structure["start_line"],
                    end_line=structure["end_line"],
                    content=split_content
                )
                chunks.append(chunk)

    return chunks

def extract_python_structures(content: str) -> list[dict]:
    language = tree_sitter.Language(tree_sitter_python.language())
    parser = tree_sitter.Parser(language)

    source_code = content.encode("utf-8")
    tree = parser.parse(source_code)

    structures = []

    def traverse(node, parent_name = None):
        current_parent = parent_name
        if node.type in {"function_definition", "class_definition"}:
            name_node = node.child_by_field_name("name")
            name = name_node.text.decode("utf-8")
            structures.append({
                "type": node.type,
                "name": name,
                "parent_name":parent_name,
                "start_line": node.start_point.row+1,
                "end_line": node.end_point.row + 1,
                "content": node.text.decode("utf-8"),
                "node":node
            })
            if node.type == "class_definition":
                current_parent = name


        for child in node.children:
            traverse(child, current_parent)

    traverse(tree.root_node)

    return structures

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

def extract_class_members(class_node) -> list:
    members = []

    body_node = class_node.child_by_field_name("body")

    if body_node is None:
        return []

    return list(body_node.named_children)

def process_class_members(
    class_node,
    class_name: str,
    repository_name: str,
    file_path: str,
    chunks: list[Chunk]
) -> None:

    members = extract_class_members(class_node)

    for member in members:
        if member.type == "expression_statement":
            attribute_name = extract_attribute_name(member)

            chunk = Chunk(
                repository_name=repository_name,
                file_path=file_path,
                language="python",
                chunk_index=len(chunks),
                chunk_type="attribute",
                name=attribute_name,
                parent_name=class_name,
                start_line=member.start_point.row + 1,
                end_line=member.end_point.row + 1,
                content=member.text.decode("utf-8")
            )

            chunks.append(chunk)
            continue
        if member.type in ["function_definition", "decorated_definition"]:

            if member.type == "decorated_definition":
                definition_node = member.child_by_field_name("definition")
                member_name_node = definition_node.child_by_field_name("name")
            else:
                member_name_node = member.child_by_field_name("name")

            member_name = member_name_node.text.decode("utf-8")
            member_content = member.text.decode("utf-8")

            if count_tokens(member_content) <= 254:
                chunk = Chunk(
                    repository_name=repository_name,
                    file_path=file_path,
                    language="python",
                    chunk_index=len(chunks),
                    chunk_type="method",
                    name=member_name,
                    parent_name=class_name,
                    start_line=member.start_point.row + 1,
                    end_line=member.end_point.row + 1,
                    content=member_content
                )

                chunks.append(chunk)

            else:
                split_contents = split_oversized_content(member_content)

                for split_content in split_contents:
                    chunk = Chunk(
                        repository_name=repository_name,
                        file_path=file_path,
                        language="python",
                        chunk_index=len(chunks),
                        chunk_type="method",
                        name=member_name,
                        parent_name=class_name,
                        start_line=member.start_point.row + 1,
                        end_line=member.end_point.row + 1,
                        content=split_content
                    )

                    chunks.append(chunk)

            continue