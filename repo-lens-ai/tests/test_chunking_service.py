import tree_sitter
import tree_sitter_python

from app.services.chunking.python_chunker import extract_python_structures, extract_class_members, extract_attribute_name, chunk_python_file

from app.services.chunking.chunking_utils import count_tokens, split_oversized_content, tokenizer

def test_tree_sitter_python_parser():
    language = tree_sitter.Language(tree_sitter_python.language())
    parser = tree_sitter.Parser(language)

    source_code = b"def greet(): \n print('Hello')"

    tree = parser.parse(source_code)

    assert tree.root_node.type == "module"
    assert tree.root_node.children[0].type == "function_definition"

def test_extract_python_structures():
    content = """
    class Calculator:
        def add(self, a, b):
            return a + b

    def multiply(a, b):
        return a * b
    """

    structures = extract_python_structures(content)

    assert len(structures) == 3

    assert structures[0]["type"] == "class_definition"
    assert structures[0]["name"] == "Calculator"
    assert structures[0]["parent_name"] is None

    assert structures[1]["type"] == "function_definition"
    assert structures[1]["name"] == "add"
    assert structures[1]["parent_name"] == "Calculator"

    assert structures[2]["type"] == "function_definition"
    assert structures[2]["name"] == "multiply"
    assert structures[2]["parent_name"] is None

def test_count_tokens():
    content = "Python is a programming language."

    token_count = count_tokens(content)

    assert isinstance(token_count, int)
    assert token_count>0

def test_split_oversized_content_respects_max_tokens():
    content = " ".join(["Python programming"] * 150)

    chunks = split_oversized_content(content)

    assert len(chunks) > 1

    for chunk in chunks:
        assert count_tokens(chunk) <=254

def test_split_oversized_content_preserves_overlap():
    content = " ".join(["Python programming"] * 150)

    chunks = split_oversized_content(content)

    first_chunk_tokens = tokenizer.encode(
        chunks[0],
        add_special_tokens=False
    )

    second_chunk_tokens = tokenizer.encode(
            chunks[1],
            add_special_tokens=False
    )

    assert first_chunk_tokens[-30:] == second_chunk_tokens[:30]

def test_extract_all_class_members():
    content = """
class Calculator:
    VERSION = "1.0"

    @staticmethod
    def add(a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

    class AdvancedCalculator:
        pass
"""

    language = tree_sitter.Language(tree_sitter_python.language())
    parser = tree_sitter.Parser(language)
    tree = parser.parse(content.encode("utf-8"))

    class_node = tree.root_node.named_children[0]

    members = extract_class_members(class_node)

    assert len(members) == 4

    member_types = [member.type for member in members]

    assert "expression_statement" in member_types
    assert "decorated_definition" in member_types
    assert "class_definition" in member_types

def test_chunk_python_file_creates_standalone_function_chunk():

    extracted_file = {
        "path": "calculator.py",
        "content": """
def multiply(a, b):
    return a * b
""",
        "extension": ".py"
    }

    chunks = chunk_python_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) == 1

    chunk = chunks[0]

    assert chunk.repository_name == "test-repo"
    assert chunk.file_path == "calculator.py"
    assert chunk.chunk_type == "function"
    assert chunk.name == "multiply"
    assert chunk.parent_name is None
    assert chunk.chunk_index == 0
    assert "return a * b" in chunk.content

def test_chunk_python_file_splits_oversized_function():

    function_content = (
        "def calculate_total():\n"
        + "\n".join(
            f"    value_{i} = {i}" for i in range(300)
        )
        + "\n    return value_299"
    )

    extracted_file = {
        "path": "calculator.py",
        "content": function_content,
        "extension": ".py"
    }

    chunks = chunk_python_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) > 1

    for chunk in chunks:
        assert count_tokens(chunk.content) <= 254
        assert chunk.name == "calculate_total"
        assert chunk.chunk_type == "function"


def test_chunk_python_file_creates_class_chunk():

    extracted_file = {
        "path": "calculator.py",
        "content": """
class Calculator:
    VERSION = "1.0"

    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
""",
        "extension": ".py"
    }

    chunks = chunk_python_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) == 1

    chunk = chunks[0]

    assert chunk.chunk_type == "class"
    assert chunk.name == "Calculator"
    assert chunk.parent_name is None
    assert chunk.chunk_index == 0
    assert "def add" in chunk.content
    assert "def subtract" in chunk.content
    assert 'VERSION = "1.0"' in chunk.content

def test_oversized_class_extracts_members():
    class_content = (
        "class Calculator:\n"
        "    VERSION = '1.0'\n"
        "    @staticmethod\n"
        "    def description():\n"
        "        return 'Calculator class'\n"
        + "\n".join(
            f"    def method_{i}(self):\n"
            f"        value = {i}\n"
            f"        return value"
            for i in range(100)
        )
    )

    extracted_file = {
        "path": "calculator.py",
        "content": class_content,
        "extension": ".py"
    }

    chunks = chunk_python_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) == 102

    attribute_chunks = [
        chunk for chunk in chunks
        if chunk.chunk_type == "attribute"
    ]

    assert len(attribute_chunks) == 1
    assert attribute_chunks[0].name == "VERSION"
    assert attribute_chunks[0].parent_name == "Calculator"
    assert attribute_chunks[0].content == "VERSION = '1.0'"

def test_extract_attribute_name():

    class_content = (
        "class Calculator:\n"
        "    VERSION = '1.0'\n"
    )

    structures = extract_python_structures(class_content)

    class_structure = next(
        structure
        for structure in structures
        if structure["type"] == "class_definition"
    )

    members = extract_class_members(class_structure["node"])

    attribute_member = next(
        member
        for member in members
        if member.type == "expression_statement"
    )

    attribute_name = extract_attribute_name(attribute_member)

    assert attribute_name == "VERSION"