from app.services.chunking.jsx_chunker import extract_jsx_structures, extract_jsx_class_members, process_jsx_function, process_jsx_class, chunk_jsx_file

def test_extract_jsx_arrow_function_component():
    content = """
const Welcome = () => {
    return <h1>Hello</h1>;
};
"""

    structures = extract_jsx_structures(content)

    assert len(structures) == 1
    assert structures[0]["name"] == "Welcome"
    assert structures[0]["type"] == "arrow_function"


def test_extract_jsx_function_component():
    content = """
function Greeting() {
    return <h2>Welcome</h2>;
}
"""

    structures = extract_jsx_structures(content)

    assert len(structures) == 1
    assert structures[0]["name"] == "Greeting"
    assert structures[0]["type"] == "function_declaration"


def test_extract_jsx_class_component():
    content = """
class Dashboard extends React.Component {
    render() {
        return <div>Dashboard</div>;
    }
}
"""

    structures = extract_jsx_structures(content)

    assert len(structures) == 1
    assert structures[0]["name"] == "Dashboard"
    assert structures[0]["type"] == "class_declaration"

def test_extract_jsx_class_members():
    content = """
class Dashboard extends React.Component {
    state = { count: 0 };

    handleClick() {
        return <button>Click</button>;
    }

    render() {
        return <div>{this.state.count}</div>;
    }
}
"""

    structures = extract_jsx_structures(content)
    class_node = structures[0]["node"]

    members = extract_jsx_class_members(class_node)

    assert len(members) == 3
    assert members[0].type == "field_definition"
    assert members[1].type == "method_definition"
    assert members[2].type == "method_definition"

def test_process_jsx_function():
    content = """
const Welcome = () => {
    return <h1>Hello</h1>;
};
"""

    structures = extract_jsx_structures(content)
    structure = structures[0]

    chunks = []

    process_jsx_function(
        function_node=structure["node"],
        function_name=structure["name"],
        repository_name="test-repo",
        file_path="Welcome.jsx",
        chunks=chunks
    )

    assert len(chunks) == 1
    assert chunks[0].name == "Welcome"
    assert chunks[0].chunk_type == "function"
    assert chunks[0].language == "javascript"
    assert "<h1>Hello</h1>" in chunks[0].content
    assert chunks[0].start_line == 2

def test_process_oversized_jsx_function(monkeypatch):
    content = """
const Welcome = () => {
    return <h1>Hello</h1>;
};
"""

    structures = extract_jsx_structures(content)
    structure = structures[0]

    def mock_count_tokens(content):
        return 300

    def mock_split_oversized_content(content, max_tokens, overlap):
        return ["JSX fragment 1", "JSX fragment 2"]

    monkeypatch.setattr(
        "app.services.chunking.jsx_chunker.count_tokens",
        mock_count_tokens
    )

    monkeypatch.setattr(
        "app.services.chunking.jsx_chunker.split_oversized_content",
        mock_split_oversized_content
    )

    chunks = []

    process_jsx_function(
        function_node=structure["node"],
        function_name=structure["name"],
        repository_name="test-repo",
        file_path="Welcome.jsx",
        chunks=chunks
    )

    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    assert chunks[0].content == "JSX fragment 1"
    assert chunks[1].content == "JSX fragment 2"

def test_process_small_jsx_class():
    content = """
class Dashboard extends React.Component {
    render() {
        return <div>Dashboard</div>;
    }
}
"""

    structures = extract_jsx_structures(content)
    structure = structures[0]

    chunks = []

    process_jsx_class(
        class_node=structure["node"],
        class_name=structure["name"],
        repository_name="test-repo",
        file_path="Dashboard.jsx",
        chunks=chunks
    )

    assert len(chunks) == 1
    assert chunks[0].name == "Dashboard"
    assert chunks[0].chunk_type == "class"
    assert "<div>Dashboard</div>" in chunks[0].content

def test_process_oversized_jsx_class(monkeypatch):
    content = """
class Dashboard extends React.Component {
    state = { count: 0 };

    render() {
        return <div>{this.state.count}</div>;
    }
}
"""

    structures = extract_jsx_structures(content)
    structure = structures[0]

    monkeypatch.setattr(
        "app.services.chunking.jsx_chunker.count_tokens",
        lambda content: 300
    )

    chunks = []

    process_jsx_class(
        class_node=structure["node"],
        class_name=structure["name"],
        repository_name="test-repo",
        file_path="Dashboard.jsx",
        chunks=chunks
    )

    assert len(chunks) == 2
    assert chunks[0].chunk_type == "attribute"
    assert chunks[0].name == "state"
    assert chunks[1].chunk_type == "method"
    assert chunks[1].name == "render"
    assert chunks[0].parent_name == "Dashboard"
    assert chunks[1].parent_name == "Dashboard"

def test_chunk_jsx_file_with_function_component():
    extracted_file = {
        "path": "Welcome.jsx",
        "extension": ".jsx",
        "content": """
const Welcome = () => {
    return <h1>Hello</h1>;
};
"""
    }

    chunks = chunk_jsx_file(extracted_file, "test-repo")

    assert len(chunks) == 1
    assert chunks[0].name == "Welcome"
    assert chunks[0].chunk_type == "function"
    assert chunks[0].file_path == "Welcome.jsx"
    assert "<h1>Hello</h1>" in chunks[0].content


def test_chunk_jsx_file_with_class_component():
    extracted_file = {
        "path": "Dashboard.jsx",
        "extension": ".jsx",
        "content": """
class Dashboard extends React.Component {
    render() {
        return <div>Dashboard</div>;
    }
}
"""
    }

    chunks = chunk_jsx_file(extracted_file, "test-repo")

    assert len(chunks) == 1
    assert chunks[0].name == "Dashboard"
    assert chunks[0].chunk_type == "class"
    assert "<div>Dashboard</div>" in chunks[0].content

def test_extract_jsx_nested_function_not_extracted_separately():
    content = """
const Dashboard = () => {
    const handleClick = () => {
        console.log("Clicked");
    };

    return <button onClick={handleClick}>Click</button>;
};
"""

    structures = extract_jsx_structures(content)

    assert len(structures) == 1
    assert structures[0]["name"] == "Dashboard"


def test_extract_named_exported_jsx_component():
    content = """
export const Welcome = () => {
    return <h1>Hello</h1>;
};
"""

    structures = extract_jsx_structures(content)

    assert len(structures) == 1
    assert structures[0]["name"] == "Welcome"
    assert structures[0]["type"] == "arrow_function"
    assert structures[0]["content"].startswith("export const")
    assert structures[0]["source_node"].type == "export_statement"


def test_extract_default_exported_jsx_component():
    content = """
export default function Dashboard() {
    return <div>Dashboard</div>;
}
"""

    structures = extract_jsx_structures(content)

    assert len(structures) == 1
    assert structures[0]["name"] == "Dashboard"
    assert structures[0]["type"] == "function_declaration"
    assert structures[0]["content"].startswith("export default")
    assert structures[0]["source_node"].type == "export_statement"

def test_chunk_jsx_file_preserves_named_export():
    extracted_file = {
        "path": "Welcome.jsx",
        "extension": ".jsx",
        "content": """
export const Welcome = () => {
    return <h1>Hello</h1>;
};
"""
    }

    chunks = chunk_jsx_file(extracted_file, "test-repo")

    assert len(chunks) == 1
    assert chunks[0].content.startswith("export const")
    assert "export const Welcome" in chunks[0].content


def test_chunk_jsx_file_preserves_default_export():
    extracted_file = {
        "path": "Dashboard.jsx",
        "extension": ".jsx",
        "content": """
        export default function Dashboard() {
            return <div>Dashboard</div>;
        }
    """
    }

    chunks = chunk_jsx_file(extracted_file, "test-repo")

    assert len(chunks) == 1
    assert chunks[0].content.startswith("export default")
    assert "function Dashboard" in chunks[0].content