#!/usr/bin/env python3
"""
Secure filesystem MCP server using FastMCP.

Usage with uv:
    uv run fileServer.py /path/to/allowed/directory [additional-directories...]
"""

import os
import sys
import base64
import json
from pathlib import Path
from typing import Any, List, Dict, Optional
import mimetypes
import fnmatch
import difflib

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("secure-filesystem-server")

# Global allowed directories
allowed_directories: List[str] = []


# Helper functions
def expand_home(path: str) -> str:
    """Expand ~ to home directory"""
    return os.path.expanduser(path)


def normalize_path(path: str) -> str:
    """Normalize path separators and resolve"""
    return os.path.normpath(path)


def set_allowed_directories(directories: List[str]):
    """Set the global allowed directories"""
    global allowed_directories
    allowed_directories = directories


def validate_path(file_path: str) -> str:
    """Validate that a path is within allowed directories"""
    # Expand and resolve the path
    expanded = expand_home(file_path)
    absolute = os.path.abspath(expanded)
    
    # Resolve symlinks for security
    try:
        resolved = os.path.realpath(absolute)
        normalized = normalize_path(resolved)
    except Exception:
        normalized = normalize_path(absolute)
    
    # Check if path is within allowed directories
    for allowed_dir in allowed_directories:
        if normalized.startswith(allowed_dir):
            return normalized
    
    raise ValueError(f"Access denied: {file_path} is outside allowed directories")


def format_size(size: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def read_file_content(file_path: str) -> str:
    """Read file content as text"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Try with different encoding
        with open(file_path, 'r', encoding='latin-1') as f:
            return f.read()


def write_file_content(file_path: str, content: str):
    """Write content to file"""
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def read_file_as_base64(file_path: str) -> str:
    """Read file and encode as base64"""
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def get_file_stats(file_path: str) -> Dict[str, Any]:
    """Get file statistics"""
    stats = os.stat(file_path)
    return {
        'size': format_size(stats.st_size),
        'created': stats.st_ctime,
        'modified': stats.st_mtime,
        'accessed': stats.st_atime,
        'isDirectory': os.path.isdir(file_path),
        'isFile': os.path.isfile(file_path),
        'permissions': oct(stats.st_mode)[-3:],
    }


def tail_file(file_path: str, num_lines: int) -> str:
    """Read last N lines of a file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        return ''.join(lines[-num_lines:])


def head_file(file_path: str, num_lines: int) -> str:
    """Read first N lines of a file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = []
        for i, line in enumerate(f):
            if i >= num_lines:
                break
            lines.append(line)
        return ''.join(lines)


def search_files(directory: str, pattern: str, exclude_patterns: Optional[List[str]] = None) -> List[str]:
    """Search for files matching a pattern"""
    if exclude_patterns is None:
        exclude_patterns = []
    
    matches = []
    for root, dirs, files in os.walk(directory):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pat) for pat in exclude_patterns)]
        
        for filename in files:
            if fnmatch.fnmatch(filename, pattern):
                full_path = os.path.join(root, filename)
                if not any(fnmatch.fnmatch(full_path, pat) for pat in exclude_patterns):
                    matches.append(full_path)
    
    return matches


def apply_file_edits(file_path: str, edits: List[Dict[str, str]], dry_run: bool = False) -> str:
    """Apply edits to a file and return diff"""
    content = read_file_content(file_path)
    
    new_content = content
    for edit in edits:
        old_text = edit['oldText']
        new_text = edit['newText']
        
        if old_text not in new_content:
            raise ValueError(f"Text to replace not found: {old_text[:50]}...")
        
        # Check if old_text appears multiple times
        if new_content.count(old_text) > 1:
            raise ValueError(f"Text appears multiple times in file: {old_text[:50]}...")
        
        new_content = new_content.replace(old_text, new_text, 1)
    
    if not dry_run:
        write_file_content(file_path, new_content)
    
    # Generate simple diff
    diff_lines = []
    diff_lines.append(f"--- {file_path}")
    diff_lines.append(f"+++ {file_path}")
    
    old_lines = content.splitlines()
    new_lines = new_content.splitlines()
    
    diff = difflib.unified_diff(old_lines, new_lines, lineterm='')
    diff_lines.extend(diff)
    
    return '\n'.join(diff_lines)


def build_directory_tree(directory: str, exclude_patterns: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Build a tree structure of directory contents"""
    if exclude_patterns is None:
        exclude_patterns = []
    
    result = []
    
    try:
        entries = os.listdir(directory)
    except PermissionError:
        return result
    
    for entry in sorted(entries):
        entry_path = os.path.join(directory, entry)
        
        # Check if should be excluded
        should_exclude = any(fnmatch.fnmatch(entry, pat) for pat in exclude_patterns)
        if should_exclude:
            continue
        
        if os.path.isdir(entry_path):
            tree_entry = {
                'name': entry,
                'type': 'directory',
                'children': build_directory_tree(entry_path, exclude_patterns)
            }
        else:
            tree_entry = {
                'name': entry,
                'type': 'file'
            }
        
        result.append(tree_entry)
    
    return result


# Tool definitions using FastMCP decorators

@mcp.tool()
def read_text_file(path: str, tail: Optional[int] = None, head: Optional[int] = None) -> str:
    """Read the complete contents of a file from the file system as text.
    
    Args:
        path: Path to the file to read
        tail: If provided, returns only the last N lines of the file
        head: If provided, returns only the first N lines of the file
    """
    if head and tail:
        raise ValueError("Cannot specify both head and tail parameters")
    
    valid_path = validate_path(path)
    
    if tail:
        return tail_file(valid_path, tail)
    elif head:
        return head_file(valid_path, head)
    else:
        return read_file_content(valid_path)


@mcp.tool()
def read_media_file(path: str) -> str:
    """Read an image or audio file. Returns the base64 encoded data and MIME type.
    
    Args:
        path: Path to the media file
    """
    valid_path = validate_path(path)
    
    # Get MIME type
    mime_type, _ = mimetypes.guess_type(valid_path)
    if not mime_type:
        mime_type = "application/octet-stream"
    
    data = read_file_as_base64(valid_path)
    
    return f"MIME Type: {mime_type}\n\nBase64 Data (first 100 chars):\n{data[:100]}...\n\nFull length: {len(data)} characters"


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Create a new file or completely overwrite an existing file with new content.
    
    Args:
        path: Path where the file should be written
        content: Content to write to the file
    """
    valid_path = validate_path(path)
    write_file_content(valid_path, content)
    return f"Successfully wrote to {path}"


@mcp.tool()
def edit_file(path: str, edits: List[Dict[str, str]], dry_run: bool = False) -> str:
    """Make line-based edits to a text file. Returns a git-style diff.
    
    Args:
        path: Path to the file to edit
        edits: List of edit operations, each with 'oldText' and 'newText'
        dry_run: If True, preview changes without applying them
    """
    valid_path = validate_path(path)
    return apply_file_edits(valid_path, edits, dry_run)


@mcp.tool()
def create_directory(path: str) -> str:
    """Create a new directory or ensure a directory exists.
    
    Args:
        path: Path of the directory to create
    """
    valid_path = validate_path(path)
    os.makedirs(valid_path, exist_ok=True)
    return f"Successfully created directory {path}"


@mcp.tool()
def list_directory(path: str) -> str:
    """Get a detailed listing of all files and directories in a specified path.
    
    Args:
        path: Path to the directory to list
    """
    valid_path = validate_path(path)
    
    entries = os.listdir(valid_path)
    formatted = []
    for entry in sorted(entries):
        entry_path = os.path.join(valid_path, entry)
        prefix = "[DIR]" if os.path.isdir(entry_path) else "[FILE]"
        formatted.append(f"{prefix} {entry}")
    
    return "\n".join(formatted)


@mcp.tool()
def list_directory_with_sizes(path: str, sort_by: str = "name") -> str:
    """Get a detailed listing of files and directories with sizes.
    
    Args:
        path: Path to the directory to list
        sort_by: Sort by 'name' or 'size' (default: name)
    """
    valid_path = validate_path(path)
    
    entries = os.listdir(valid_path)
    detailed_entries = []
    
    for entry in entries:
        entry_path = os.path.join(valid_path, entry)
        try:
            stats = os.stat(entry_path)
            detailed_entries.append({
                'name': entry,
                'is_directory': os.path.isdir(entry_path),
                'size': stats.st_size,
            })
        except Exception:
            detailed_entries.append({
                'name': entry,
                'is_directory': os.path.isdir(entry_path),
                'size': 0,
            })
    
    # Sort entries
    if sort_by == 'size':
        detailed_entries.sort(key=lambda x: x['size'], reverse=True)
    else:
        detailed_entries.sort(key=lambda x: x['name'])
    
    # Format output
    formatted = []
    for entry in detailed_entries:
        prefix = "[DIR]" if entry['is_directory'] else "[FILE]"
        size_str = "" if entry['is_directory'] else format_size(entry['size']).rjust(10)
        formatted.append(f"{prefix} {entry['name'].ljust(30)} {size_str}")
    
    # Add summary
    total_files = sum(1 for e in detailed_entries if not e['is_directory'])
    total_dirs = sum(1 for e in detailed_entries if e['is_directory'])
    total_size = sum(e['size'] for e in detailed_entries if not e['is_directory'])
    
    formatted.append("")
    formatted.append(f"Total: {total_files} files, {total_dirs} directories")
    formatted.append(f"Combined size: {format_size(total_size)}")
    
    return "\n".join(formatted)


@mcp.tool()
def directory_tree(path: str, exclude_patterns: Optional[List[str]] = None) -> str:
    """Get a recursive tree view of files and directories as a JSON structure.
    
    Args:
        path: Root path for the tree
        exclude_patterns: Patterns to exclude from the tree
    """
    valid_path = validate_path(path)
    
    if exclude_patterns is None:
        exclude_patterns = []
    
    tree_data = build_directory_tree(valid_path, exclude_patterns)
    return json.dumps(tree_data, indent=2)


@mcp.tool()
def move_file(source: str, destination: str) -> str:
    """Move or rename files and directories.
    
    Args:
        source: Source path
        destination: Destination path
    """
    valid_source = validate_path(source)
    valid_dest = validate_path(destination)
    
    os.rename(valid_source, valid_dest)
    return f"Successfully moved {source} to {destination}"


@mcp.tool()
def search_files(path: str, pattern: str, exclude_patterns: Optional[List[str]] = None) -> str:
    """Recursively search for files matching a pattern.
    
    Args:
        path: Directory to search in
        pattern: Glob pattern to match files
        exclude_patterns: Patterns to exclude from search
    """
    valid_path = validate_path(path)
    
    if exclude_patterns is None:
        exclude_patterns = []
    
    results = search_files(valid_path, pattern, exclude_patterns)
    
    if results:
        return "\n".join(results)
    else:
        return "No matches found"


@mcp.tool()
def get_file_info(path: str) -> str:
    """Retrieve detailed metadata about a file or directory.
    
    Args:
        path: Path to the file or directory
    """
    valid_path = validate_path(path)
    info = get_file_stats(valid_path)
    return "\n".join(f"{k}: {v}" for k, v in info.items())


@mcp.tool()
def list_allowed_directories() -> str:
    """Returns the list of directories that this server is allowed to access."""
    if not allowed_directories:
        return "No allowed directories configured"
    return "Allowed directories:\n" + "\n".join(allowed_directories)


def main():
    """Main entry point"""
    # Parse command line arguments
    args = sys.argv[1:]
    
    if len(args) == 0:
        print("Usage: fileServer.py [allowed-directory] [additional-directories...]", file=sys.stderr)
        print("Note: At least one directory must be provided for the server to operate.", file=sys.stderr)
        sys.exit(1)
    
    # Process allowed directories from command line
    initial_dirs = []
    for directory in args:
        expanded = expand_home(directory)
        absolute = os.path.abspath(expanded)
        
        try:
            resolved = os.path.realpath(absolute)
            normalized = normalize_path(resolved)
            
            # Validate directory exists
            if not os.path.isdir(normalized):
                print(f"Error: {normalized} is not a directory", file=sys.stderr)
                sys.exit(1)
            
            initial_dirs.append(normalized)
        except Exception as e:
            print(f"Error accessing directory {directory}: {e}", file=sys.stderr)
            sys.exit(1)
    
    set_allowed_directories(initial_dirs)
    
    print(f"Secure MCP Filesystem Server starting with {len(allowed_directories)} allowed directories", file=sys.stderr)
    
    # Run the server
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()
