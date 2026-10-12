
from pathlib import Path
from mcp.server import MCPServer
import shutil

mcp = MCPServer("MCP File Server")

WORKSPACE = Path(__file__).parent / "workspace"
WORKSPACE.mkdir(exist_ok=True)

def safe_path(filename: str) -> Path:
    path = (WORKSPACE / filename).resolve()

    if not path.is_relative_to(WORKSPACE.resolve()):
        raise ValueError("Access denied: path must stay inside workspace.")

    return path

@mcp.tool()
def list_files() -> str:
    items = sorted(WORKSPACE.iterdir())

    if not items:
        return "Workspace is empty."

    return "\n".join(
        f"{'[DIR]' if item.is_dir() else '[FILE]'} {item.name}"
        for item in items
    )

@mcp.tool()
def read_file(filename: str) -> str:
    path = safe_path(filename)

    if not path.is_file():
        return f"Error: file not found: {filename}"

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "Error: file is not a readable UTF-8 text file."

@mcp.tool()
def write_file(filename: str, content: str) -> str:
    path = safe_path(filename)

    if path.exists() and path.is_dir():
        return f"Error: '{filename}' is a directory."

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    return f"Successfully wrote file: {filename}"

@mcp.tool()
def create_directory(dirname: str) -> str:
    path = safe_path(dirname)

    if path.exists():
        if path.is_dir():
            return f"Directory already exists: {dirname}"
        return f"Error: a file already exists at '{dirname}'."

    path.mkdir(parents=True, exist_ok=True)
    return f"Successfully created directory: {dirname}"

@mcp.tool()
def delete_file(filename: str) -> str:
    path = safe_path(filename)

    if not path.exists():
        return f"Error: file not found: {filename}"

    if not path.is_file():
        return "Error: this tool only deletes files, not directories."

    path.unlink()
    return f"Successfully deleted file: {filename}"

@mcp.tool()
def rename_file(old_name: str, new_name: str) -> str:
    source = safe_path(old_name)
    destination = safe_path(new_name)

    if not source.exists() or not source.is_file():
        return f"Error: source file not found: {old_name}"

    if destination.exists():
        return f"Error: destination already exists: {new_name}"

    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)

    return f"Successfully renamed '{old_name}' to '{new_name}'."

@mcp.tool()
def search_files(query: str) -> str:
    if not query:
        return "Error: search query cannot be empty."

    matches = []

    for path in WORKSPACE.rglob("*"):
        if not path.is_file():
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for line_number, line in enumerate(content.splitlines(), start=1):
            if query.casefold() in line.casefold():
                relative_path = path.relative_to(WORKSPACE)
                matches.append(
                    f"{relative_path}:{line_number}: {line.strip()}"
                )

    return "\n".join(matches) if matches else "No matches found."

@mcp.tool()
def edit_file(filename: str, old_text: str, new_text: str) -> str:
    path = safe_path(filename)

    if not path.is_file():
        return f"Error: file not found: {filename}"

    if not old_text:
        return "Error: the text to replace cannot be empty."

    content = path.read_text(encoding="utf-8")

    if old_text not in content:
        return "Error: the specified text was not found."

    if content.count(old_text) > 1:
        return "Error: text appears multiple times. Make it more specific."

    updated_content = content.replace(old_text, new_text, 1)
    path.write_text(updated_content, encoding="utf-8")

    return f"Successfully edited file: {filename}"

@mcp.tool()
def touch_file(filename: str) -> str:
    path = safe_path(filename)

    if path.exists():
        return f"Error: '{filename}' already exists."

    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()

    return f"Successfully created empty file: {filename}"

@mcp.tool()
def copy_file(source_name: str, destination_name: str) -> str:
    source = safe_path(source_name)
    destination = safe_path(destination_name)

    if not source.is_file():
        return f"Error: source file not found: {source_name}"

    if destination.exists():
        return f"Error: destination already exists: {destination_name}"

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)

    return f"Successfully copied '{source_name}' to '{destination_name}'."

@mcp.tool()
def get_file_info(filename: str) -> str:
    path = safe_path(filename)

    if not path.is_file():
        return f"Error: file not found: {filename}"

    stats = path.stat()

    return (
        f"File: {path.name}\n"
        f"Size: {stats.st_size} bytes\n"
        f"Last modified: {stats.st_mtime}"
    )

@mcp.tool()
def repo_map() -> str:
    entries = []

    for path in sorted(WORKSPACE.rglob("*")):
        relative = path.relative_to(WORKSPACE)
        depth = len(relative.parts) - 1
        prefix = "    " * depth
        label = "[DIR]" if path.is_dir() else "[FILE]"
        entries.append(f"{prefix}{label} {path.name}")

    if not entries:
        return "Workspace is empty."

    return "\n".join(entries)

@mcp.tool()
def start_session(task: str) -> str:
    if not task.strip():
        return "Error: task description cannot be empty."

    handoff_dir = safe_path("handoffs")
    handoff_dir.mkdir(parents=True, exist_ok=True)

    handoff_file = handoff_dir / "current_session.md"

    handoff_file.write_text(
        "# New Agent Session\n\n"
        f"## Task\n{task.strip()}\n\n"
        "## Instructions\n"
        "- Review the project files before making changes.\n"
        "- Check existing decisions and progress notes if available.\n"
        "- Avoid overwriting existing work without reviewing it first.\n",
        encoding="utf-8",
    )

    return f"Session handoff created at: {handoff_file.relative_to(WORKSPACE)}"

@mcp.tool()
def update_project_state(section: str, content: str) -> str:
    if not section.strip() or not content.strip():
        return "Error: section and content cannot be empty."

    state_file = safe_path("handoffs/project_state.md")
    state_file.parent.mkdir(parents=True, exist_ok=True)

    if state_file.exists():
        existing = state_file.read_text(encoding="utf-8")
    else:
        existing = "# Project State\n"

    heading = f"## {section.strip()}"
    parts = existing.split(heading)

    if len(parts) > 1:
        before = parts[0]
        after = parts[1].split("\n## ", 1)
        remainder = f"\n## {after[1]}" if len(after) > 1 else ""
        updated = f"{before}{heading}\n{content.strip()}{remainder}"
    else:
        updated = existing.rstrip() + f"\n\n{heading}\n{content.strip()}\n"

    state_file.write_text(updated, encoding="utf-8")
    return "Project state updated successfully."

@mcp.tool()
def log_plan(task: str, steps: str) -> str:
    if not task.strip() or not steps.strip():
        return "Error: task and steps cannot be empty."

    plan_file = safe_path("handoffs/task_plan.md")
    plan_file.parent.mkdir(parents=True, exist_ok=True)

    plan_file.write_text(
        "# Task Plan\n\n"
        f"## Task\n{task.strip()}\n\n"
        f"## Steps\n{steps.strip()}\n",
        encoding="utf-8",
    )

    return "Task plan saved to handoffs/task_plan.md."

@mcp.tool()
def save_checkpoint(task: str, completed: str, remaining: str) -> str:
    if not task.strip():
        return "Error: task cannot be empty."

    checkpoint_file = safe_path("handoffs/checkpoint.md")
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

    checkpoint_file.write_text(
        "# Session Checkpoint\n\n"
        f"## Current Task\n{task.strip()}\n\n"
        f"## Completed\n{completed.strip() or 'Nothing recorded yet.'}\n\n"
        f"## Remaining\n{remaining.strip() or 'Nothing recorded.'}\n",
        encoding="utf-8",
    )

    return "Checkpoint saved to handoffs/checkpoint.md."

@mcp.tool()
def record_decision(decision: str, reason: str) -> str:
    if not decision.strip() or not reason.strip():
        return "Error: decision and reason cannot be empty."

    decision_file = safe_path("handoffs/decisions.md")
    decision_file.parent.mkdir(parents=True, exist_ok=True)

    if decision_file.exists():
        existing = decision_file.read_text(encoding="utf-8")
    else:
        existing = "# Project Decisions\n"

    entry = (
        f"\n## {decision.strip()}\n"
        f"**Reason:** {reason.strip()}\n"
    )

    decision_file.write_text(existing.rstrip() + "\n" + entry, encoding="utf-8")

    return "Decision recorded in handoffs/decisions.md."

if __name__ == "__main__":
    mcp.run(transport="streamable-http")