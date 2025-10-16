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
```


The server communicates via **stdio**, so it is fully compatible with any MCP-enabled client.

---

## Connecting the Filesystem MCP Server to Claude Desktop (This example is done on Mac)

To connect this Python-based Secure Filesystem MCP Server to **Claude Desktop**, follow these steps:

1. Make sure the server runs correctly on its own:  
   ```bash
   uv run /absolute/path/to/fileServer.py /absolute/path/to/allowed/directory
   ```
2. Open your **Claude MCP configuration file**:
   - Open Claud Desktop
   - Go to Settings
   - Go to Developer
   - Click Edit Config
   - Open claude_desktop_config.json
   - Paste/Add the following configuration:
     ```json
     {
       "mcpServers": {
         "filesystem": {
           "command": "/Users/USERNAME/.local/bin/uv",
             "args": [
               "run",
               "/absolute/path/to/fileServer.py",
               "/absolute/path/to/allowed/directory"
             ]
         }
       }
     }
     ```
4. Save the file.
5. **Fully restart Claude** to reload your updated MCP configuration.
6. Start a new chat — Claude should now automatically detect your MCP filesystem server and list it as an available tool.

**Tip:**  
Use absolute paths and choose directories you’re comfortable granting full read/write access to.

---


## Security Model

- You must specify one or more **allowed directories** at startup.  
- All operations validate and resolve paths (including symlinks) and deny access outside the configured directories.  
- Unauthorized paths return descriptive errors.   

---
