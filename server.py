import logging
from pathlib import Path
from mcp.server import MCPServer
import uvicorn
from mcp.server.transport_security import TransportSecuritySettings

mcp = MCPServer("MCP File Server")

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE = (BASE_DIR / "workspace").resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(BASE_DIR / "mcp_file_server.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    force=True,
)

logger = logging.getLogger("mcp_file_server")

def safe_path(filename: str) -> Path:
    if not filename or not filename.strip():
        raise ValueError("Filename cannot be empty.")

    try:
        path = (WORKSPACE / filename).resolve()

        if not path.is_relative_to(WORKSPACE):
            raise ValueError(
                "Access denied: path must stay inside workspace."
            )

        return path

    except (OSError, RuntimeError) as exc:
        raise ValueError(
            "Access denied: invalid or unsafe file path."
        ) from exc

#1
@mcp.tool()
def read_file(filename: str) -> str:
    try:
        path = safe_path(filename)
    except ValueError as exc:
        logger.warning("Rejected read request: %s", exc)
        return f"Error: {exc}"

    try:
        if not path.is_file():
            return f"Error: file not found: {filename}"

        content = path.read_text(encoding="utf-8")
        logger.info("Read file: %s", path.relative_to(WORKSPACE))
        return content

    except UnicodeDecodeError:
        return "Error: file is not a readable UTF-8 text file."
    except OSError as exc:
        logger.exception("Failed to read file: %s", filename)
        return f"Error: could not read file: {exc}"

#2
@mcp.tool()
def write_file(filename: str, content: str) -> str:
    try:
        path = safe_path(filename)
    except ValueError as exc:
        logger.warning("Rejected write request: %s", exc)
        return f"Error: {exc}"

    try:
        if path.exists():
            if path.is_dir():
                return f"Error: '{filename}' is a directory."

            return (
                f"Error: '{filename}' already exists. "
                "Use edit_file() to modify an existing file."
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        logger.info("Created file: %s", path.relative_to(WORKSPACE))
        return f"Successfully wrote file: {filename}"

    except OSError as exc:
        logger.exception("Failed to write file: %s", filename)
        return f"Error: could not write file: {exc}"

#3
@mcp.tool()
def search_files(query: str) -> str:
    if not query or not query.strip():
        return "Error: search query cannot be empty."

    matches = []

    try:
        for path in WORKSPACE.rglob("*"):
            if not path.is_file():
                continue

            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                logger.warning("Skipped unreadable file: %s", path)
                continue

            for line_number, line in enumerate(content.splitlines(), start=1):
                if query.casefold() in line.casefold():
                    relative_path = path.relative_to(WORKSPACE)
                    matches.append(
                        f"{relative_path}:{line_number}: {line.strip()}"
                    )

        logger.info("File search completed.")
        return "\n".join(matches) if matches else "No matches found."

    except OSError as exc:
        logger.exception("File search failed")
        return f"Error: could not search workspace: {exc}"

#4

@mcp.tool()
def edit_file(filename: str, old_text: str, new_text: str) -> str:
    try:
        path = safe_path(filename)
    except ValueError as exc:
        logger.warning("Rejected edit request: %s", exc)
        return f"Error: {exc}"

    try:
        if not path.is_file():
            return f"Error: file not found: {filename}"

        if not old_text:
            return "Error: the text to replace cannot be empty."

        content = path.read_text(encoding="utf-8")

        occurrences = content.count(old_text)

        if occurrences == 0:
            return "Error: the specified text was not found."

        if occurrences > 1:
            return "Error: text appears multiple times. Make it more specific."

        updated_content = content.replace(old_text, new_text, 1)
        path.write_text(updated_content, encoding="utf-8")

        logger.info("Edited file: %s", path.relative_to(WORKSPACE))
        return f"Successfully edited file: {filename}"

    except UnicodeDecodeError:
        return "Error: file is not a readable UTF-8 text file."
    except (OSError, RuntimeError) as exc:
        logger.exception("Failed to edit file: %s", filename)
        return f"Error: could not edit file: {exc}"

#5
@mcp.tool()
def repo_map() -> str:
    entries = []

    try:
        for path in sorted(WORKSPACE.rglob("*")):
            relative = path.relative_to(WORKSPACE)
            depth = len(relative.parts) - 1
            prefix = "    " * depth
            label = "[DIR]" if path.is_dir() else "[FILE]"
            entries.append(f"{prefix}{label} {path.name}")

        if not entries:
            return "Workspace is empty."

        logger.info("Workspace map generated.")
        return "\n".join(entries)

    except OSError as exc:
        logger.exception("Failed to generate workspace map")
        return f"Error: could not map workspace: {exc}"

#6
@mcp.tool()
def start_session(task: str) -> str:
    if not task.strip():
        return "Error: task description cannot be empty."

    try:
        handoff_dir = safe_path("handoffs")
        handoff_dir.mkdir(parents=True, exist_ok=True)

        handoff_file = safe_path("handoffs/current_session.md")

        if handoff_file.exists():
            return (
                "Error: a session handoff already exists. "
                "Review or rename it before starting another session."
            )

        handoff_file.write_text(
            "# New Agent Session\n\n"
            f"## Task\n{task.strip()}\n\n"
            "## Instructions\n"
            "- Review the project files before making changes.\n"
            "- Check existing decisions and progress notes if available.\n"
            "- Avoid overwriting existing work without reviewing it first.\n",
            encoding="utf-8",
        )

        logger.info("Created session handoff: %s",
                    handoff_file.relative_to(WORKSPACE))
        return (
            "Session handoff created at: "
            f"{handoff_file.relative_to(WORKSPACE)}"
        )

    except (OSError, ValueError) as exc:
        logger.exception("Failed to create session handoff")
        return f"Error: could not create session handoff: {exc}"

#7
@mcp.tool()
def update_project_state(section: str, content: str) -> str:
    if not section.strip() or not content.strip():
        return "Error: section and content cannot be empty."

    try:
        state_file = safe_path("handoffs/project_state.md")
        state_file.parent.mkdir(parents=True, exist_ok=True)

        if state_file.exists():
            existing = state_file.read_text(encoding="utf-8")
        else:
            existing = "# Project State\n"

        section_name = section.strip()
        heading = f"## {section_name}"
        lines = existing.splitlines()

        heading_index = None

        for index, line in enumerate(lines):
            if line.strip() == heading:
                heading_index = index
                break

        if heading_index is not None:
            end_index = len(lines)

            for index in range(heading_index + 1, len(lines)):
                if lines[index].startswith("## "):
                    end_index = index
                    break

            updated_lines = (
                lines[:heading_index + 1]
                + [content.strip()]
                + lines[end_index:]
            )
        else:
            updated_lines = (
                lines
                + ([""] if lines else [])
                + [heading, content.strip()]
            )

        updated = "\n".join(updated_lines).rstrip() + "\n"
        state_file.write_text(updated, encoding="utf-8")

        logger.info("Updated project state section: %s", section_name)
        return "Project state updated successfully."

    except (OSError, ValueError) as exc:
        logger.exception("Failed to update project state")
        return f"Error: could not update project state: {exc}"

#8
@mcp.tool()
def save_checkpoint(task: str, completed: str, remaining: str) -> str:
    if not task.strip():
        return "Error: task cannot be empty."

    try:
        checkpoint_file = safe_path("handoffs/checkpoint.md")
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

        if checkpoint_file.exists():
            return (
                "Error: a checkpoint already exists. "
                "Review or rename it before saving another."
            )

        checkpoint_file.write_text(
            "# Session Checkpoint\n\n"
            f"## Current Task\n{task.strip()}\n\n"
            f"## Completed\n{completed.strip() or 'Nothing recorded yet.'}\n\n"
            f"## Remaining\n{remaining.strip() or 'Nothing recorded.'}\n",
            encoding="utf-8",
        )

        logger.info("Created checkpoint: %s",
                    checkpoint_file.relative_to(WORKSPACE))
        return "Checkpoint saved to handoffs/checkpoint.md."

    except (OSError, ValueError) as exc:
        logger.exception("Failed to save checkpoint")
        return f"Error: could not save checkpoint: {exc}"

if __name__ == "__main__":
    security = TransportSecuritySettings(
        allowed_hosts=[
            "basis-gangway-silica.ngrok-free.dev",
            "localhost:*",
            "127.0.0.1:*",
        ],
    )
    app = mcp.streamable_http_app(transport_security=security)
    uvicorn.run(app, host="127.0.0.1", port=8000)