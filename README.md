# Secure Filesystem MCP Server (Python)

A Python re-implementation of the **Secure Filesystem MCP Server** from the official
[Model Context Protocol (MCP)](https://github.com/modelcontextprotocol) project.

This version ports the original TypeScript/Node server to **Python** using **FastMCP**,
preserving the same core functionality (file read/write/edit/move/search, directory listing
with sizes, metadata, JSON tree views) and enforcing strict **allowed directories** security.

---

## What’s in this repo?

- **Feature parity** with the original filesystem server:
  - `read_text_file` (with `head`/`tail`)
  - `read_media_file` (Base64 + MIME)
  - `write_file`, `edit_file` (diff preview), `move_file`
  - `create_directory`, `list_directory`, `list_directory_with_sizes`
  - `directory_tree` (JSON), `search_files`, `get_file_info`
  - `list_allowed_directories`
- **Python-native** implementation using `FastMCP`
- **Security-first** path validation against configured allowed directories
- Minimal dependencies, runs over **stdio** for easy MCP client integration

---

## Why rewrite it in Python?

- Provide a **Python-native MCP server** for teams/environments that prefer Python
- Demonstrate a clean **port from the official TypeScript server** to FastMCP
- Reduce runtime/dependency footprint (no Node.js required)

---

## Quick start

```bash
# Recommended: uv
uv run fileServer.py /path/to/allowed/dir [more/dirs...]

# Or plain Python
python3 fileServer.py /path/to/allowed/dir [more/dirs...]

The server communicates via **stdio**, so it is fully compatible with any MCP-enabled client.

---

## Example Tools

- `read_text_file(path, head=None, tail=None)`: Read text file contents with optional head/tail line limits  
- `read_media_file(path)`: Read media file, return MIME type and Base64  
- `write_file(path, content)`: Overwrite or create a new file  
- `edit_file(path, edits, dry_run=False)`: Apply text edits, show git-style diff  
- `create_directory(path)`: Create directory (recursively)  
- `list_directory(path)`: List files and directories  
- `list_directory_with_sizes(path, sort_by="name"|"size")`: List files with size info  
- `directory_tree(path, exclude_patterns=None)`: Recursive JSON directory tree  
- `search_files(path, pattern, exclude_patterns=None)`: Find files by glob pattern  
- `get_file_info(path)`: Detailed file metadata  
- `list_allowed_directories()`: Show configured accessible directories  

---

## Security Model

- You must specify one or more **allowed directories** at startup.  
- All operations validate and resolve paths (including symlinks) and deny access outside the configured directories.  
- Unauthorized paths return descriptive errors.   

---
