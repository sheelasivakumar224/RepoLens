import tree_sitter
import tree_sitter_javascript

from app.schemas.chunk import Chunk
from app.services.chunking.chunking_utils import count_tokens, split_oversized_content

def parse_jsx_content(content: str):
    language = tree_sitter.Language(
        tree_sitter_javascript.language()
    )

    parser = tree_sitter.Parser(language)

    source_code = content.encode("utf-8")
    tree = parser.parse(source_code)

    return tree

def extract_jsx_structures(content: str) -> list[dict]:
    tree = parse_jsx_content(content)

    structures = []

    def traverse(node):

        source_node = node

        if node.type == "export_statement":
            if not node.named_children:
                return

            node = node.named_children[0]

        if node.type == "function_declaration":
            name_node = node.child_by_field_name("name")

            structures.append({
                "type": node.type,
                "name": name_node.text.decode("utf-8"),
                "parent_name": None,
                "start_line": source_node.start_point.row + 1,
                "end_line": source_node.end_point.row + 1,
                "content": source_node.text.decode("utf-8"),
                "node": node,
                "source_node": source_node
            })

            return

        if node.type == "lexical_declaration":
            for child in node.named_children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    value_node = child.child_by_field_name("value")

                    if value_node and value_node.type in {
                        "arrow_function",
                        "function_expression"
                    }:
                        structures.append({
                            "type": value_node.type,
                            "name": name_node.text.decode("utf-8"),
                            "parent_name": None,
                            "start_line": source_node.start_point.row + 1,
                            "end_line": source_node.end_point.row + 1,
                            "content": source_node.text.decode("utf-8"),
                            "node": node,
                            "source_node": source_node
                        })

                        return

        if node.type == "class_declaration":
            name_node = node.child_by_field_name("name")

            structures.append({
                "type": node.type,
                "name": name_node.text.decode("utf-8"),
                "parent_name": None,
                "start_line": source_node.start_point.row + 1,
                "end_line": source_node.end_point.row + 1,
                "content": source_node.text.decode("utf-8"),
                "node": node,
                "source_node": source_node
            })

            return

        for child in node.named_children:
            traverse(child)
        

    traverse(tree.root_node)

    return structures

def extract_jsx_class_members(class_node) -> list:
    body_node = class_node.child_by_field_name("body")

    if body_node is None:
        return []

    return list(body_node.named_children)

def process_jsx_class_members(
    class_node,
    class_name: str,
    repository_name: str,
    file_path: str,
    chunks: list[Chunk]
) -> None:

    members = extract_jsx_class_members(class_node)

    for member in members:

        if member.type == "field_definition":
            property_node = member.child_by_field_name("property")
            attribute_name = property_node.text.decode("utf-8")

            chunk = Chunk(
                repository_name=repository_name,
                file_path=file_path,
                language="javascript",
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

        if member.type == "method_definition":
            name_node = member.child_by_field_name("name")
            method_name = name_node.text.decode("utf-8")

            chunk = Chunk(
                repository_name=repository_name,
                file_path=file_path,
                language="javascript",
                chunk_index=len(chunks),
                chunk_type="method",
                name=method_name,
                parent_name=class_name,
                start_line=member.start_point.row + 1,
                end_line=member.end_point.row + 1,
                content=member.text.decode("utf-8")
            )

            chunks.append(chunk)
            continue

def process_jsx_function(
    function_node,
    function_name: str,
    repository_name: str,
    file_path: str,
    chunks: list[Chunk]
) -> None:

    function_content = function_node.text.decode("utf-8")

    if count_tokens(function_content) <= 254:
        content_parts = [function_content]
    else:
        content_parts = split_oversized_content(
            content=function_content,
            max_tokens=254,
            overlap=30
        )

    for content in content_parts:
        chunk = Chunk(
            repository_name=repository_name,
            file_path=file_path,
            language="javascript",
            chunk_index=len(chunks),
            chunk_type="function",
            name=function_name,
            parent_name=None,
            start_line=function_node.start_point.row + 1,
            end_line=function_node.end_point.row + 1,
            content=content
        )

        chunks.append(chunk)

def process_jsx_class(
    class_node,
    class_name: str,
    repository_name: str,
    file_path: str,
    chunks: list[Chunk],
    source_node=None
) -> None:
    if source_node is None:
        source_node = class_node

    class_content = source_node.text.decode("utf-8")

    if count_tokens(class_content) <= 254:
        chunk = Chunk(
            repository_name=repository_name,
            file_path=file_path,
            language="javascript",
            chunk_index=len(chunks),
            chunk_type="class",
            name=class_name,
            parent_name=None,
            start_line=source_node.start_point.row + 1,
            end_line=source_node.end_point.row + 1,
            content=class_content
        )

        chunks.append(chunk)

    else:
        process_jsx_class_members(
            class_node=class_node,
            class_name=class_name,
            repository_name=repository_name,
            file_path=file_path,
            chunks=chunks
        )
    
def chunk_jsx_file(
    extracted_file: dict,
    repository_name: str
) -> list[Chunk]:

    content = extracted_file["content"]
    file_path = extracted_file["path"]

    structures = extract_jsx_structures(content)

    classes = [
        structure for structure in structures
        if structure["type"] == "class_declaration"
        and structure["parent_name"] is None
    ]

    standalone_functions = [
        structure for structure in structures
        if structure["type"] in {
            "function_declaration",
            "arrow_function",
            "function_expression"
        }
        and structure["parent_name"] is None
    ]

    chunks = []

    for structure in classes:
        process_jsx_class(
            class_node=structure["node"],
            class_name=structure["name"],
            repository_name=repository_name,
            file_path=file_path,
            chunks=chunks,
            source_node=structure["source_node"]
        )

    for structure in standalone_functions:
        process_jsx_function(
            function_node=structure["source_node"],
            function_name=structure["name"],
            repository_name=repository_name,
            file_path=file_path,
            chunks=chunks
        )

    return chunks