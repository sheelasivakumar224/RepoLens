import tree_sitter
import tree_sitter_javascript

from app.schemas.chunk import Chunk

from app.services.chunking.chunking_utils import count_tokens, split_oversized_content

def extract_javascript_structures(content: str) -> list[dict]:
    language = tree_sitter.Language(tree_sitter_javascript.language())
    parser = tree_sitter.Parser(language)

    source_code = content.encode("utf-8")
    tree = parser.parse(source_code)

    structures = []

    def traverse(node):
        if node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            name = name_node.text.decode("utf-8")

            structures.append({
                "type": node.type,
                "name": name,
                "parent_name": None,
                "start_line": node.start_point.row + 1,
                "end_line": node.end_point.row + 1,
                "content": node.text.decode("utf-8"),
                "node": node
            })
            return
        
        if node.type == "lexical_declaration":
            for child in node.named_children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    value_node = child.child_by_field_name("value")

                    if value_node.type in {"arrow_function", "function_expression"}:
                        structures.append({
                            "type": value_node.type,
                            "name": name_node.text.decode("utf-8"),
                            "parent_name": None,
                            "start_line": node.start_point.row + 1,
                            "end_line": node.end_point.row + 1,
                            "content": node.text.decode("utf-8"),
                            "node": node
                        })
                        return

                    
        if node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            name = name_node.text.decode("utf-8")

            structures.append({
                "type": "class_declaration",
                "name": name,
                "parent_name": None,
                "start_line": node.start_point.row + 1,
                "end_line": node.end_point.row + 1,
                "content": node.text.decode("utf-8"),
                "node": node
            })
            return


        for child in node.children:
            traverse(child)
    
    traverse(tree.root_node)

    return structures

def extract_javascript_class_members(class_node) -> list:
    body_node = class_node.child_by_field_name("body")

    if body_node is None:
        return []

    return list(body_node.named_children)

def process_javascript_class_members(
        class_node, 
        class_name: str,
        repository_name: str,
        file_path: str,
        chunks: list[Chunk]
) -> None:
    members = extract_javascript_class_members(class_node)

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
                end_line=member.end_point.row+1,
                content=member.text.decode("utf-8")
            )

            chunks.append(chunk)
            continue

        if member.type == "method_definition":
            name_node = member.child_by_field_name("name")
            method_name = name_node.text.decode("utf-8")

            method_content = member.text.decode("utf-8")

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
                content=method_content
            )

            chunks.append(chunk)
            continue

def process_javascript_function(
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

def process_javascript_class(
    class_node,
    class_name: str,
    repository_name: str,
    file_path: str,
    chunks: list[Chunk]
) -> None:

    class_content = class_node.text.decode("utf-8")
    if count_tokens(class_content) <= 254:
        chunk = Chunk(
            repository_name=repository_name,
            file_path=file_path,
            language="javascript",
            chunk_index=len(chunks),
            chunk_type="class",
            name=class_name,
            parent_name=None,
            start_line=class_node.start_point.row + 1,
            end_line=class_node.end_point.row + 1,
            content=class_node.text.decode("utf-8")
        )
        
        chunks.append(chunk)
    else:
        process_javascript_class_members(
            class_node=class_node,
            class_name=class_name,
            repository_name=repository_name,
            file_path=file_path,
            chunks=chunks
        )

def chunk_javascript_file(extracted_file: dict, repository_name: str)-> list[Chunk]:
    content = extracted_file["content"]
    file_path = extracted_file["path"]

    structures = extract_javascript_structures(content)

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
        if count_tokens(structure["content"]) <= 254:
            chunk = Chunk(
                repository_name=repository_name,
                file_path=file_path,
                language="javascript",
                chunk_index=len(chunks),
                chunk_type="class",
                name=structure["name"],
                parent_name=None,
                start_line=structure["start_line"],
                end_line=structure["end_line"],
                content=structure["content"]
            )

            chunks.append(chunk)

        else:
            process_javascript_class_members(
                class_node=structure["node"],
                class_name=structure["name"],
                repository_name=repository_name,
                file_path=file_path,
                chunks=chunks
            )

    for structure in standalone_functions:
        process_javascript_function(
            function_node=structure["node"],
            function_name=structure["name"],
            repository_name=repository_name,
            file_path=file_path,
            chunks=chunks
        )

    return chunks