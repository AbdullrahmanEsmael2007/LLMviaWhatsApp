import os

def list_files(path="."):
    """List all files in the current directory, ignoring hidden files."""
    files = []
    for root, dirs, filenames in os.walk(path):
        # Skip hidden directories like .git
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for filename in filenames:
            if not filename.startswith('.'):
                files.append(os.path.relpath(os.path.join(root, filename), path))
    return "\n".join(files)

def read_file(path):
    """Read the content of a file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"

def write_file(path, content):
    """Write content to a file."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file {path}: {str(e)}"

# Schema definition for OpenAI
TOOLS = [
    {
        "type": "function",
        "name": "list_files",
        "description": "List all files in the project to see the file structure.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to list files from (default is '.')."
                }
            }
        }
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read the content of a specific file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to read."
                }
            },
            "required": ["path"]
        }
    },
    {
        "type": "function",
        "name": "write_file",
        "description": "Write code or text to a file. Overwrites existing content.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to write to."
                },
                "content": {
                    "type": "string",
                    "description": "The full content to write to the file."
                }
            },
            "required": ["path", "content"]
        }
    }
]

def execute_tool(name, args):
    if name == "list_files":
        return list_files(args.get("path", "."))
    elif name == "read_file":
        return read_file(args["path"])
    elif name == "write_file":
        return write_file(args["path"], args["content"])
    return f"Error: Unknown tool '{name}'"
