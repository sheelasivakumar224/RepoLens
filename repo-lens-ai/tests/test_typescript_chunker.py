from app.services.chunking.typescript_chunker import extract_typescript_structures, extract_typescript_class_members, process_typescript_class_attribute, process_typescript_class_method, process_typescript_class_members, chunk_typescript_file, process_typescript_function

def test_extract_typescript_interface():
    content = """
        interface User {
            name: string;
            age: number;
        }
    """

    structures = extract_typescript_structures(content)

    assert len(structures) == 1
    assert structures[0]["type"] == "interface"
    assert structures[0]["name"] == "User"

def test_extract_typescript_type_alias():
    content = """
    type UserID = string | umber;
    """

    structures = extract_typescript_structures(content)

    assert len(structures) == 1
    assert structures[0]["type"] == "type"
    assert structures[0]["name"] == "UserID"

def test_extract_typescript_function():
    content = """
    function greet(name: string): string {
        return `Hello ${name}`;
    }
    """

    structures = extract_typescript_structures(content)
    
    assert len(structures) == 1
    assert structures[0]["type"] == "function"
    assert structures[0]["name"] == "greet"

def test_extract_typescript_arrow_function():
    content = """
    const calculate = (a: number, b: number): number => {
        return a + b;
    };
    """
    structures = extract_typescript_structures(content)

    assert len(structures) == 1
    assert structures[0]["type"] == "function"
    assert structures[0]["name"] == "calculate"

def test_extract_typescript_class():
    content = """
    class Calculator {
        version: string = "1.0";

        add(a: number, b: number): number {
            return a + b;
        }
    }
    """

    structures = extract_typescript_structures(content)

    assert len(structures) == 1
    assert structures[0]["type"] == "class"
    assert structures[0]["name"] == "Calculator"

def test_extract_typescript_class_attribute():
    content = """
    class Calculator{
        version: string = "1.0";
    }
    """

    structures = extract_typescript_structures(content)
    class_node = structures[0]["node"]

    members = extract_typescript_class_members(class_node)

    assert len(members) == 1
    assert members[0]["type"] == "attribute"
    assert members[0]["name"] == "version"

def test_extract_typescript_class_method():
    content = """
        class Calculator {
            add(a: number, b: number): number {
                return a + b;
            }
        }
    """

    structures = extract_typescript_structures(content)
    class_node = structures[0]["node"]

    members = extract_typescript_class_members(class_node)

    assert len(members) == 1
    assert members[0]["type"] == "method"
    assert members[0]["name"] == "add"

def test_process_typescript_class_attribute():
    content = """
    class Calculator {
        version: string = "1.0";
    }
    """

    structures = extract_typescript_structures(content)
    class_node = structures[0]["node"]

    members = extract_typescript_class_members(class_node)
    attribute = members[0]["node"]

    chunks = []

    process_typescript_class_attribute(
        member=attribute,
        class_name="Calculator",
        repository_name="test-repo",
        file_path="calculator.ts",
        chunks=chunks
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "attribute"
    assert chunks[0].name == "version"
    assert chunks[0].parent_name == "Calculator"
    assert chunks[0].language == "typescript"
    assert "version: string" in chunks[0].content

def test_process_typescript_class_method():
    content = """
        class Calculator {
            add(a: number, b: number): number {
                return a + b;
            }
        }
    """

    structures = extract_typescript_structures(content)
    class_node = structures[0]["node"]

    members = extract_typescript_class_members(class_node)
    method = members[0]["node"]

    chunks = []

    process_typescript_class_method(
        method,
        class_name="Calculator",
        repository_name="test-repo",
        file_path="calculator.ts",
        chunks=chunks
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "method"
    assert chunks[0].name == "add"
    assert chunks[0].parent_name == "Calculator"
    assert chunks[0].language == "typescript"
    assert "a: number" in chunks[0].content
    assert "return a + b" in chunks[0].content

def test_process_typescript_class_members():
    content = """
    class Calculator {
        version: string = "1.0";

        add(a: number, b: number): number {
            return a + b;
        }
    }
    """

    structures = extract_typescript_structures(content)
    class_node = structures[0]["node"]

    chunks = []

    process_typescript_class_members(
        class_node=class_node,
        class_name="Calculator",
        repository_name="test-repo",
        file_path="calculator.ts",
        chunks=chunks
    )

    assert len(chunks) == 2
    
    assert chunks[0].chunk_type == "attribute"
    assert chunks[0].name == "version"

    assert chunks[1].chunk_type == "method"
    assert chunks[1].name == "add"

    assert all(chunk.parent_name == "Calculator" for chunk in chunks)
    assert all(chunk.language == "typescript" for chunk in chunks)

def test_chunk_typescript_file_with_small_class():
    extracted_file = {
            "path": "calculator.ts",
            "content": """
    class Calculator {
        version: string = "1.0";

        add(a: number, b: number): number {
            return a + b;
        }
    }
    """
    }

    chunks = chunk_typescript_file(extracted_file, "test-repo")

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "class"
    assert chunks[0].name == "Calculator"
    assert chunks[0].parent_name is None
    assert "version: string" in chunks[0].content
    assert "add(a: number" in chunks[0].content

def test_chunk_typescript_file_with_oversized_class():
    methods = "\n".join(
        f"""
        method_{i}(value: number): number {{
            return value + {i};
        }}
        """
        for i in range(30)
    )

    content = f"""
class Calculator {{
    version: string = "1.0";
    {methods}
}}
"""

    extracted_file = {
        "path": "calculator.ts",
        "content": content
    }

    chunks = chunk_typescript_file(extracted_file, "test-repo")

    assert len(chunks) > 1
    assert any(chunk.chunk_type == "attribute" for chunk in chunks)
    assert any(chunk.chunk_type == "method" for chunk in chunks)
    assert all(chunk.parent_name == "Calculator" for chunk in chunks)

def test_process_typescript_function():
    content = """
function greet(name: string): string {
    return `Hello ${name}`;
}
"""
    structures = extract_typescript_structures(content)
    function = structures[0]

    chunks = []

    process_typescript_function(
        node=function["node"],
        function_name=function["name"],
        repository_name="test-repo",
        file_path="greet.ts",
        chunks=chunks
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "function"
    assert chunks[0].name == "greet"
    assert chunks[0].parent_name is None
    assert chunks[0].language == "typescript"
    assert "name: string" in chunks[0].content

def test_process_typescript_arrow_function():
    content = """
const calculate = (a: number, b: number): number => {
    return a + b;
};
"""
    structures = extract_typescript_structures(content)
    function = structures[0]

    chunks = []

    process_typescript_function(
        node=function["node"],
        function_name=function["name"],
        repository_name="test-repo",
        file_path="calculator.ts",
        chunks=chunks
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "function"
    assert chunks[0].name == "calculate"
    assert chunks[0].parent_name is None
    assert chunks[0].language == "typescript"
    assert "a: number" in chunks[0].content


def test_chunk_typescript_file_with_small_function():
    extracted_file = {
        "path": "src/greet.ts",
        "content": """
function greet(name: string): string {
    return `Hello ${name}`;
}
"""
    }

    chunks = chunk_typescript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "function"
    assert chunks[0].name == "greet"
    assert chunks[0].parent_name is None
    assert chunks[0].language == "typescript"
    assert "name: string" in chunks[0].content


def test_chunk_typescript_file_with_small_arrow_function():
    extracted_file = {
        "path": "src/calculate.ts",
        "content": """
const calculate = (a: number, b: number): number => {
    return a + b;
};
"""
    }

    chunks = chunk_typescript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "function"
    assert chunks[0].name == "calculate"
    assert chunks[0].parent_name is None
    assert chunks[0].language == "typescript"
    assert "a: number" in chunks[0].content

def test_chunk_typescript_file_with_oversized_function():
    function_body = "    const value = 1;\n" * 100

    extracted_file = {
        "path": "calculator.ts",
        "content": (
            "function calculate(): number {\n"
            f"{function_body}"
            "    return value;\n"
            "}"
        )
    }

    chunks = chunk_typescript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) > 1

    for chunk in chunks:
        assert chunk.chunk_type == "function"
        assert chunk.name == "calculate"
        assert chunk.parent_name is None
        assert chunk.language == "typescript"
        assert chunk.content.strip() != ""

    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))

def test_extract_exported_typescript_interface():
    content = """
export interface User {
    name: string;
    age: number;
}
"""

    structures = extract_typescript_structures(content)

    assert len(structures) == 1
    assert structures[0]["type"] == "interface"
    assert structures[0]["name"] == "User"
    assert structures[0]["node"].type == "interface_declaration"
    assert structures[0]["source_node"].type == "export_statement"
    assert "export interface User" in structures[0]["source_node"].text.decode("utf-8")

def test_extract_exported_typescript_type_alias():
    content = """
export type UserID = string | number;
"""

    structures = extract_typescript_structures(content)

    assert len(structures) == 1
    assert structures[0]["type"] == "type"
    assert structures[0]["name"] == "UserID"
    assert structures[0]["node"].type == "type_alias_declaration"
    assert structures[0]["source_node"].type == "export_statement"
    assert "export type UserID" in structures[0]["source_node"].text.decode("utf-8")

def test_extract_exported_typescript_function():
    content = """
export function greet(name: string): string {
    return `Hello ${name}`;
}
"""

    structures = extract_typescript_structures(content)

    assert len(structures) == 1
    assert structures[0]["type"] == "function"
    assert structures[0]["name"] == "greet"
    assert structures[0]["node"].type == "function_declaration"
    assert structures[0]["source_node"].type == "export_statement"
    assert "export function greet" in structures[0]["source_node"].text.decode("utf-8")

def test_extract_exported_typescript_arrow_function():
    content = """
export const calculate = (a: number, b: number): number => {
    return a + b;
};
"""

    structures = extract_typescript_structures(content)

    assert len(structures) == 1
    assert structures[0]["type"] == "function"
    assert structures[0]["name"] == "calculate"
    assert structures[0]["node"].type == "lexical_declaration"
    assert structures[0]["source_node"].type == "export_statement"
    assert "export const calculate" in structures[0]["source_node"].text.decode("utf-8")

def test_extract_exported_typescript_class():
    content = """
export class Calculator {
    add(a: number, b: number): number {
        return a + b;
    }
}
"""

    structures = extract_typescript_structures(content)

    assert len(structures) == 1
    assert structures[0]["type"] == "class"
    assert structures[0]["name"] == "Calculator"
    assert structures[0]["node"].type == "class_declaration"
    assert structures[0]["source_node"].type == "export_statement"
    assert "export class Calculator" in structures[0]["source_node"].text.decode("utf-8")

def test_chunk_typescript_file_with_exported_interface():
    extracted_file = {
        "path": "user.ts",
        "content": """
export interface User {
    name: string;
    age: number;
}
"""
    }

    chunks = chunk_typescript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "interface"
    assert chunks[0].name == "User"
    assert chunks[0].content.strip().startswith("export interface User")

def test_chunk_typescript_file_with_exported_type_alias():
    extracted_file = {
        "path": "user.ts",
        "content": """
export type UserID = string | number;
"""
    }

    chunks = chunk_typescript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "type"
    assert chunks[0].name == "UserID"
    assert chunks[0].content.strip().startswith("export type UserID")

def test_chunk_typescript_file_with_exported_function():
    extracted_file = {
        "path": "greetings.ts",
        "content": """
export function greet(name: string): string {
    return `Hello ${name}`;
}
"""
    }

    chunks = chunk_typescript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "function"
    assert chunks[0].name == "greet"
    assert chunks[0].parent_name is None
    assert chunks[0].content.strip().startswith("export function greet")

def test_chunk_typescript_file_with_exported_arrow_function():
    extracted_file = {
        "path": "calculator.ts",
        "content": """
export const calculate = (a: number, b: number): number => {
    return a + b;
};
"""
    }

    chunks = chunk_typescript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "function"
    assert chunks[0].name == "calculate"
    assert chunks[0].parent_name is None
    assert chunks[0].content.strip().startswith("export const calculate")

def test_chunk_typescript_file_with_exported_class():
    extracted_file = {
        "path": "calculator.ts",
        "content": """
export class Calculator {
    add(a: number, b: number): number {
        return a + b;
    }
}
"""
    }

    chunks = chunk_typescript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "class"
    assert chunks[0].name == "Calculator"
    assert chunks[0].content.strip().startswith("export class Calculator")

def test_chunk_typescript_file_with_oversized_exported_class():
    methods = "\n".join(
        f"""
        method_{i}(value: number): number {{
            return value + {i};
        }}
        """
        for i in range(30)
    )

    content = f"""
export class Calculator {{
    version: string = "1.0";
    {methods}
}}
"""

    extracted_file = {
        "path": "calculator.ts",
        "content": content
    }

    chunks = chunk_typescript_file(extracted_file, "test-repo")

    assert len(chunks) > 1
    assert any(chunk.chunk_type == "attribute" for chunk in chunks)
    assert any(chunk.chunk_type == "method" for chunk in chunks)
    assert all(chunk.parent_name == "Calculator" for chunk in chunks)
    assert all(chunk.language == "typescript" for chunk in chunks)
    assert all(
        chunk.content.strip() in content
        for chunk in chunks
    )

def test_extract_tsx_arrow_function():
    content = """
    interface UserProps {
        name: string;
    }

    const UserCard = ({ name }: UserProps) => {
        return <div>Hello, {name}</div>;
    };
    """

    structures = extract_typescript_structures(
        content=content,
        file_path="UserCard.tsx"
    )

    function_names = [
        structure["name"]
        for structure in structures
        if structure["type"] == "function"
    ]

    assert function_names == ["UserCard"]

def test_chunk_tsx_file_with_arrow_function():
    content = """
    interface UserProps {
        name: string;
    }

    const UserCard = ({ name }: UserProps) => {
        return <div>Hello, {name}</div>;
    };
    """

    extracted_file = {
        "content": content,
        "path": "UserCard.tsx"
    }

    chunks = chunk_typescript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    function_chunks = [
        chunk for chunk in chunks
        if chunk.chunk_type == "function"
    ]

    assert len(function_chunks) == 1
    assert function_chunks[0].name == "UserCard"
    assert function_chunks[0].file_path == "UserCard.tsx"
    assert "return <div>Hello, {name}</div>" in function_chunks[0].content

def test_extract_tsx_class():
    content = """
    class UserCard extends React.Component {
        render() {
            return <div>Hello</div>;
        }
    }
    """

    structures = extract_typescript_structures(
        content=content,
        file_path="UserCard.tsx"
    )

    class_names = [
        structure["name"]
        for structure in structures
        if structure["type"] == "class"
    ]

    assert class_names == ["UserCard"]

def test_chunk_tsx_file_with_class():
    content = """
    class UserCard extends React.Component {
        render() {
            return <div>Hello</div>;
        }
    }
    """

    extracted_file = {
        "content": content,
        "path": "UserCard.tsx"
    }

    chunks = chunk_typescript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "class"
    assert chunks[0].name == "UserCard"
    assert chunks[0].file_path == "UserCard.tsx"
    assert "return <div>Hello</div>" in chunks[0].content

def test_chunk_tsx_file_with_exported_arrow_function():
    content = """
    export const UserCard = () => {
        return <div>Hello</div>;
    };
    """

    extracted_file = {
        "content": content,
        "path": "UserCard.tsx"
    }

    chunks = chunk_typescript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) == 1
    assert chunks[0].name == "UserCard"
    assert chunks[0].chunk_type == "function"
    assert "export const UserCard" in chunks[0].content
    assert "return <div>Hello</div>" in chunks[0].content

def test_chunk_tsx_file_with_exported_class():
    content = """
    export class UserCard extends React.Component {
        render() {
            return <div>Hello</div>;
        }
    }
    """

    extracted_file = {
        "content": content,
        "path": "UserCard.tsx"
    }

    chunks = chunk_typescript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) == 1
    assert chunks[0].name == "UserCard"
    assert chunks[0].chunk_type == "class"
    assert "export class UserCard" in chunks[0].content
    assert "return <div>Hello</div>" in chunks[0].content

def test_extract_multiple_tsx_structures():
    content = """
    interface UserProps {
        name: string;
    }

    type UserRole = "admin" | "user";

    function getGreeting(name: string) {
        return `Hello ${name}`;
    }

    export const UserCard = ({ name }: UserProps) => {
        return <div>{getGreeting(name)}</div>;
    };
    """

    structures = extract_typescript_structures(
        content=content,
        file_path="UserCard.tsx"
    )

    structure_names = [
        (structure["type"], structure["name"])
        for structure in structures
    ]

    assert structure_names == [
        ("interface", "UserProps"),
        ("type", "UserRole"),
        ("function", "getGreeting"),
        ("function", "UserCard")
    ]

def test_chunk_oversized_tsx_arrow_function():
    methods = "\n".join(
        f"const value{i} = {i};"
        for i in range(100)
    )

    content = f"""
    export const UserCard = () => {{
        {methods}
        return <div>Hello</div>;
    }};
    """

    extracted_file = {
        "content": content,
        "path": "UserCard.tsx"
    }

    chunks = chunk_typescript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) > 1
    assert all(chunk.chunk_type == "function" for chunk in chunks)
    assert all(chunk.name == "UserCard" for chunk in chunks)
    assert all(chunk.language == "typescript" for chunk in chunks)

def test_chunk_oversized_tsx_class():
    methods = "\n".join(
        f"method{i}() {{ return {i}; }}"
        for i in range(30)
    )

    content = f"""
    export class UserCard extends React.Component {{
        {methods}

        render() {{
            return <div>Hello</div>;
        }}
    }}
    """

    extracted_file = {
        "content": content,
        "path": "UserCard.tsx"
    }

    chunks = chunk_typescript_file(
        extracted_file=extracted_file,
        repository_name="test-repo"
    )

    assert len(chunks) > 1
    assert all(chunk.parent_name == "UserCard" for chunk in chunks)
    assert all(chunk.language == "typescript" for chunk in chunks)
    assert any(
        "return <div>Hello</div>" in chunk.content
        for chunk in chunks
    )

def test_extract_tsx_nested_arrow_function():
    content = """
    export const UserCard = () => {
        const getGreeting = () => "Hello";

        return <div>{getGreeting()}</div>;
    };
    """

    structures = extract_typescript_structures(
        content=content,
        file_path="UserCard.tsx"
    )

    function_names = [
        structure["name"]
        for structure in structures
        if structure["type"] == "function"
    ]

    assert function_names == ["UserCard"]