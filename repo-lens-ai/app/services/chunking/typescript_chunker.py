import tree_sitter
import tree_sitter_typescript

from app.schemas.chunk import Chunk
from app.services.chunking.chunking_utils import count_tokens, split_oversized_content

def extract_typescript_structures(content: str, file_path: str = "") -> list[dict]:
    if file_path.endswith(".tsx"):
        language = tree_sitter.Language(
            tree_sitter_typescript.language_tsx()
        )
    else:
        language = tree_sitter.Language(
            tree_sitter_typescript.language_typescript()
        )
    parser = tree_sitter.Parser(language)

    tree = parser.parse(content.encode("utf-8"))
    root_node = tree.root_node

    structures = []

    for source_node in root_node.named_children:
        node = source_node

        if node.type == "export_statement":
            if not node.named_children:
                continue
            node = node.named_children[0]

        if node.type == "interface_declaration":
            structures.append({
                "type":"interface",
                "name":node.child_by_field_name("name").text.decode("utf-8"),
                "node": node,
                "source_node":source_node,
                "parent_name": None
            })
        elif node.type == "type_alias_declaration":
            structures.append({
                "type":"type",
                "name":node.child_by_field_name("name").text.decode("utf-8"),
                "node": node,
                "source_node": source_node,
                "parent_name": None
            })
        elif node.type == "function_declaration":
            structures.append({
                "type": "function",
                "name": node.child_by_field_name("name").text.decode("utf-8"),
                "node": node,
                "source_node": source_node,
                "parent_name": None
            })
        elif node.type == "lexical_declaration":
            for child in node.named_children:
                if child.type == "variable_declarator":
                    value_node = child.child_by_field_name("value")

                    if value_node and value_node.type == "arrow_function":
                        structures.append({
                            "type": "function",
                            "name": child.child_by_field_name("name").text.decode("utf-8"),
                            "node":node,
                            "source_node": source_node,
                            "parent_name": None
                        })
        elif node.type == "class_declaration":
            structures.append({
                "type":"class",
                "name": node.child_by_field_name("name").text.decode("utf-8"),
                "node":node,
                "source_node": source_node,
                "parent_name": None
            })
    return structures

def extract_typescript_class_members(class_node):
    class_body = class_node.child_by_field_name("body")

    members = []

    for member in class_body.named_children:
        if member.type == "public_field_definition":
            members.append({
                "type":"attribute",
                "name":member.child_by_field_name("name").text.decode("utf-8"),
                "node": member
            })
        elif member.type == "method_definition":
            members.append({
                "type":"method",
                "name":member.child_by_field_name("name").text.decode("utf-8"),
                "node": member
            })
    return members

def process_typescript_class_attribute(
        member,
        class_name: str,
        repository_name: str,
        file_path: str,
        chunks: list[Chunk]
) -> None:
    content = member.text.decode("utf-8")

    if count_tokens(content) > 254:
        parts = split_oversized_content(content)

        for part in parts:
            chunks.append(
                Chunk(
                    repository_name=repository_name,
                    file_path=file_path,
                    language="typescript",
                    chunk_index=len(chunks),
                    chunk_type="attribute",
                    name=member.child_by_field_name("name").text.decode("utf-8"),
                    parent_name=class_name,
                    start_line=member.start_point.row + 1,
                    end_line=member.end_point.row + 1,
                    content=part
                )
            )
    else:
        chunks.append(
            Chunk(
                repository_name=repository_name,
                file_path=file_path,
                language="typescript",
                chunk_index=len(chunks),
                chunk_type="attribute",
                name=member.child_by_field_name("name").text.decode("utf-8"),
                parent_name=class_name,
                start_line=member.start_point.row + 1,
                end_line=member.end_point.row + 1,
                content=content
            )
        )

def process_typescript_class_method(
        member,
        class_name: str,
        repository_name: str,
        file_path: str,
        chunks: list[Chunk]
) -> None:
    content = member.text.decode("utf-8")
    method_name = member.child_by_field_name("name").text.decode("utf-8")

    if count_tokens(content) > 254:
        parts = split_oversized_content(content)

        for part in parts:
            chunks.append(
                Chunk(
                    repository_name=repository_name,
                    file_path=file_path,
                    language="typescript",
                    chunk_index=len(chunks),
                    chunk_type="method",
                    name=method_name,
                    parent_name=class_name,
                    start_line=member.start_point.row + 1,
                    end_line=member.end_point.row+1,
                    content=part
                )
            )
    else:
        chunks.append(
            Chunk(
                    repository_name=repository_name,
                    file_path=file_path,
                    language="typescript",
                    chunk_index=len(chunks),
                    chunk_type="method",
                    name=method_name,
                    parent_name=class_name,
                    start_line=member.start_point.row + 1,
                    end_line=member.end_point.row+1,
                    content=content
                )
        )

def process_typescript_class_members(
        class_node,
        class_name: str,
        repository_name: str,
        file_path: str,
        chunks: list[Chunk]
)-> None:

    members = extract_typescript_class_members(class_node)

    for member in members:
        if member["type"] == "attribute":
            process_typescript_class_attribute(
                member=member["node"],
                class_name=class_name,
                repository_name=repository_name,
                file_path=file_path,
                chunks=chunks
            )
        elif member["type"] == "method":
            process_typescript_class_method(
                member=member["node"],
                class_name=class_name,
                repository_name=repository_name,
                file_path=file_path,
                chunks=chunks
            )

def process_typescript_function(
    node,
    function_name: str,
    repository_name: str,
    file_path: str,
    chunks: list[Chunk]
) -> None:

    content = node.text.decode("utf-8")

    if count_tokens(content) > 254:
        parts = split_oversized_content(content)

        for part in parts:
            chunks.append(
                Chunk(
                    repository_name=repository_name,
                    file_path=file_path,
                    language="typescript",
                    chunk_index=len(chunks),
                    chunk_type="function",
                    name=function_name,
                    parent_name=None,
                    start_line=node.start_point.row + 1,
                    end_line=node.end_point.row + 1,
                    content=part
                )
            )

    else:
        chunks.append(
            Chunk(
                repository_name=repository_name,
                file_path=file_path,
                language="typescript",
                chunk_index=len(chunks),
                chunk_type="function",
                name=function_name,
                parent_name=None,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                content=content
            )
        )

def chunk_typescript_file(
        extracted_file: dict,
        repository_name: str
) -> list[Chunk]:
    content = extracted_file["content"]
    file_path = extracted_file["path"]

    structures = extract_typescript_structures(content, file_path)

    chunks = []

    for structure in structures:
        if structure["type"] in ["interface", "type"]:
            node = structure["node"]
            structure_content = structure["source_node"].text.decode("utf-8")

            chunks.append(
                Chunk(
                repository_name=repository_name,
                file_path=file_path,
                language="typescript",
                chunk_index=len(chunks),
                chunk_type=structure["type"],
                name=structure["name"],
                parent_name=None,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                content=structure_content
            )
            )
        elif structure["type"] == "class":
            node = structure["node"]
            class_name = structure["name"]
            class_content = structure["source_node"].text.decode("utf-8")

            if count_tokens(class_content) > 254:
                process_typescript_class_members(
                    class_node=node,
                    class_name=class_name,
                    repository_name=repository_name,
                    file_path=file_path,
                    chunks=chunks
                )

            else:
                chunks.append(
                    Chunk(
                        repository_name=repository_name,
                        file_path=file_path,
                        language="typescript",
                        chunk_index=len(chunks),
                        chunk_type="class",
                        name=class_name,
                        parent_name=None,
                        start_line=node.start_point.row + 1,
                        end_line=node.end_point.row + 1,
                        content=class_content
                    )
                )
        elif structure["type"] == "function":
            process_typescript_function(
                node=structure["source_node"],
                function_name=structure["name"],
                repository_name=repository_name,
                file_path=file_path,
                chunks=chunks
            )
    return chunks