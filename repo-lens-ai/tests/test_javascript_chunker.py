import tree_sitter
import tree_sitter_javascript

from app.services.chunking.javascript_chunker import extract_javascript_structures, chunk_javascript_file

from app.services.chunking.chunking_utils import count_tokens

def test_extract_javascript_nested_functions():
    source_code = """
        function outerFunction() {

        function innerFunction() {
            return "Hello";
        }

        return innerFunction();
    }
    """

    structures = extract_javascript_structures(source_code)

    function_names = [structure["name"] for structure in structures if structure["type"] == "function_declaration"]

    assert "outerFunction" in function_names
    assert "innerFunction" not in function_names

def test_extract_function_inside_class_method():
    source_code = """
    class Calculator {
        calculate() {
            function helper() {
                return 10;
            }
        }
    }
    """

    structures = extract_javascript_structures(source_code)

    function_names = [
        structure["name"]
        for structure in structures
        if structure["type"] == "function_declaration"
    ]

    assert function_names == []

def test_extract_nested_arrow_functions():

    source_code = """
    const outer = () => {
        const inner = () => {
            return "Hello";
        };

        return inner();
    };
    """

    structures = extract_javascript_structures(source_code)

    function_names = [
        structure["name"]
        for structure in structures
        if structure["type"] == "arrow_function"
    ]

    assert function_names == ["outer"]

def test_class_methods_not_extracted_as_standalone_functions():
    source_code = """
    class Calculator {
        add(a, b) {
            return a + b;
        }
    }
    """

    structures = extract_javascript_structures(source_code)

    function_names = [
        structure["name"]
        for structure in structures
        if structure["type"] in {
            "function_declaration",
            "arrow_function",
            "function_expression"
        }
    ]

    assert function_names == []

def test_chunk_javascript_file_with_small_function():
    extracted_file = {
        "path": "calculator.js",
        "content": """
function calculateTotal(price, quantity) {
    return price * quantity;
}
"""
    }

    chunks = chunk_javascript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) == 1

    assert chunks[0].repository_name == "test-repo"
    assert chunks[0].file_path == "calculator.js"
    assert chunks[0].language == "javascript"
    assert chunks[0].chunk_index == 0
    assert chunks[0].chunk_type == "function"
    assert chunks[0].name == "calculateTotal"
    assert chunks[0].parent_name is None
    assert "return price * quantity" in chunks[0].content

def test_chunk_javascript_file_with_small_class():

    extracted_file = {
        "path": "calculator.js",
        "content": """
class Calculator {
    add(a, b) {
        return a + b;
    }
}
"""
    }

    chunks = chunk_javascript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) == 1

    assert chunks[0].repository_name == "test-repo"
    assert chunks[0].file_path == "calculator.js"
    assert chunks[0].language == "javascript"
    assert chunks[0].chunk_index == 0
    assert chunks[0].chunk_type == "class"
    assert chunks[0].name == "Calculator"
    assert chunks[0].parent_name is None
    assert "add(a, b)" in chunks[0].content

def test_chunk_javascript_file_with_oversized_class():

    large_method = "\n".join(
        f"        const value{i} = {i};"
        for i in range(100)
    )

    source_code = f"""
class LargeCalculator {{
    VERSION = "1.0";

    calculate() {{
{large_method}
        return value99;
    }}
}}
"""

    extracted_file = {
        "path": "calculator.js",
        "content": source_code
    }

    chunks = chunk_javascript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) == 2

    assert chunks[0].chunk_type == "attribute"
    assert chunks[0].name == "VERSION"
    assert chunks[0].parent_name == "LargeCalculator"

    assert chunks[1].chunk_type == "method"
    assert chunks[1].name == "calculate"
    assert chunks[1].parent_name == "LargeCalculator"

    assert [chunk.chunk_index for chunk in chunks] == [0, 1]

def test_chunk_javascript_file_with_oversized_function():

    large_function = "\n".join(
        f"    const value{i} = {i};"
        for i in range(100)
    )

    source_code = f"""
function calculateLargeTotal() {{
{large_function}
    return value99;
}}
"""

    extracted_file = {
        "path": "calculator.js",
        "content": source_code
    }

    chunks = chunk_javascript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) > 1

    assert all(chunk.chunk_type == "function" for chunk in chunks)

    assert all(
        chunk.name == "calculateLargeTotal"
        for chunk in chunks
    )

    assert all(chunk.parent_name is None for chunk in chunks)

    assert [
        chunk.chunk_index for chunk in chunks
    ] == list(range(len(chunks)))