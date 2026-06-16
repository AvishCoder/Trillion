import os
import json
import httpx

ALLOWED_DIR = os.path.expanduser("~")


async def web_search(query: str, max_results: int = 5) -> str:
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            body = r.get("body", "")
            href = r.get("href", "")
            lines.append(f"{i}. {title}\n   {body}\n   {href}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Web search failed: {e}"


async def read_file(file_path: str) -> str:
    abs_path = os.path.abspath(os.path.join(os.getcwd(), file_path))
    if not os.path.exists(abs_path):
        return f"File not found: {file_path}"
    if os.path.getsize(abs_path) > 100_000:
        return "File too large (over 100KB)."
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


async def write_file(file_path: str, content: str) -> str:
    abs_path = os.path.abspath(os.path.join(os.getcwd(), file_path))
    if not abs_path.startswith(os.getcwd()):
        return "Cannot write outside the project directory."
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    try:
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Written to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"


async def list_files(directory: str = ".") -> str:
    abs_path = os.path.abspath(os.path.join(os.getcwd(), directory))
    if not abs_path.startswith(os.getcwd()):
        return "Cannot list files outside the project directory."
    if not os.path.isdir(abs_path):
        return f"Directory not found: {directory}"
    try:
        files = os.listdir(abs_path)
        result = []
        for f in sorted(files):
            full = os.path.join(abs_path, f)
            label = "📁" if os.path.isdir(full) else "📄"
            result.append(f"{label} {f}")
        return "\n".join(result) if result else "(empty directory)"
    except Exception as e:
        return f"Error listing files: {e}"


TOOL_REGISTRY = {
    "web_search": {
        "definition": {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for current information, news, research, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum results to return (1-10)",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        "function": web_search,
    },
    "read_file": {
        "definition": {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file in the project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file (relative to project root)",
                        },
                    },
                    "required": ["file_path"],
                },
            },
        },
        "function": read_file,
    },
    "write_file": {
        "definition": {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write content to a file in the project. Creates directories if needed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file (relative to project root)",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file",
                        },
                    },
                    "required": ["file_path", "content"],
                },
            },
        },
        "function": write_file,
    },
    "list_files": {
        "definition": {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories in a project directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Directory path (relative to project root, default: .)",
                            "default": ".",
                        },
                    },
                },
            },
        },
        "function": list_files,
    },
}


def get_tool_definitions():
    return [t["definition"] for t in TOOL_REGISTRY.values()]


async def execute_tool(tool_name: str, args: dict) -> str:
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        return f"Unknown tool: {tool_name}"
    return await tool["function"](**args)
