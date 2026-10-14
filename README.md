# MCP File Server Connector

A Python-based Model Context Protocol (MCP) server that allows an AI assistant to safely interact with files inside a designated workspace. The project demonstrates file operations, workspace sandboxing, automated testing, and cross-session task handoffs using Claude.ai.

## Objectives

- Build and deploy a custom MCP file-server connector.
- Provide structured tools for reading, creating, searching, and editing files.
- Restrict file operations to a designated workspace directory.
- Preserve task context across separate AI conversations using handoff files.
- Test the server using automated tests, MCP Inspector, and a real MCP client.

## Technology Stack

- Python
- MCP Python SDK
- Uvicorn
- MCP Inspector
- Claude.ai
- ngrok for temporary HTTPS tunneling
- `unittest` for automated testing

## Architecture

The system follows this connection flow:

Claude.ai → HTTPS tunnel (ngrok) → Local Python MCP server → Sandboxed workspace

The Python server runs locally and exposes its MCP endpoint through Streamable HTTP. During browser-based demonstrations, ngrok provides a temporary public HTTPS address that Claude.ai can use to connect to the server.

All file operations are intended to remain inside the project's `workspace/` directory.

## Project Structure

```text
mcp-file-server-connector/
├── server.py
├── requirements.txt
├── tests/
│   └── test_server.py
├── workspace/
│   └── .gitkeep
├── .gitignore
└── README.md
```

Runtime files and demonstration artifacts may appear inside `workspace/`. Log files are generated locally and are not intended to be committed.

## Setup

### Prerequisites

- Python installed
- Git
- Node.js and npm, for MCP Inspector
- ngrok, for connecting the local server to Claude.ai

### 1. Clone the repository

```bash
git clone https://github.com/elighnel/mcp-file-server-connector.git
cd mcp-file-server-connector
```

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure transport host validation

The server validates incoming host headers. In `server.py`, update the `allowed_hosts` list to include the hostname of your current ngrok tunnel, along with the existing local development hosts.

The ngrok hostname may change between sessions, depending on your ngrok configuration.

### 5. Start the MCP server

```powershell
python server.py
```

The server listens on `127.0.0.1:8000`. Its MCP endpoint is:

```text
http://127.0.0.1:8000/mcp
```

Keep this terminal running while using the connector.

## Connecting to Claude.ai

1. Start the MCP server.
2. Open a separate terminal and start the tunnel:

   ```powershell
   ngrok http 8000
   ```

3. Copy the HTTPS forwarding address provided by ngrok.
4. Append `/mcp` to the HTTPS address.
5. Add the resulting endpoint as a custom remote MCP connector in Claude.ai, following the connector configuration options available to your account.
6. If the tunnel hostname changes, update `allowed_hosts` in `server.py` and restart the Python server.

The tunnel and server must both remain running while Claude.ai is using the connector.

## Available MCP Tools

| Tool | Purpose |
|---|---|
| `repo_map` | Lists the files and directories in the workspace. |
| `read_file` | Reads a text file from the workspace. |
| `search_files` | Searches workspace files for matching text. |
| `edit_file` | Replaces a unique text passage in an existing file. |
| `write_file` | Creates a new file without intentionally overwriting an existing file. |
| `start_session` | Creates a handoff file describing a new task. |
| `update_project_state` | Creates or updates a section in the saved project state. |
| `save_checkpoint` | Saves task progress and remaining work for a later session. |

## Cross-Session Handoff Demonstration

The handoff tools support continuity between separate AI conversations by saving task information in the workspace.

The demonstration uses these files:

- `handoffs/current_session.md` — records the current session's task.
- `handoffs/project_state.md` — records project decisions and progress.
- `handoffs/checkpoint.md` — records completed work and remaining tasks.

In the first conversation, the AI creates or updates task information using the MCP tools. In a separate conversation, the AI reads the saved files, reviews the previous progress, continues the task, and updates the handoff records.

This demonstrates that context can be transferred through persistent files rather than relying only on the conversation history.

## Testing

### Automated tests

Run the test suite from the project root:

```powershell
python -m unittest discover -s tests -v
```

The current test suite contains 21 tests covering file operations, path validation, error handling, and session handoff behavior.

### MCP Inspector

Start the server in one terminal, then launch MCP Inspector in another:

```powershell
npx @modelcontextprotocol/inspector
```

Open the local Inspector URL shown in the terminal, connect to the server, and verify that the eight tools are available. Use the Inspector to test tool inputs and outputs.

## Security Considerations

- File paths are resolved and validated to prevent operations from escaping the workspace directory.
- File creation refuses to overwrite existing files.
- File editing requires a unique matching passage.
- Handoff and checkpoint tools refuse to overwrite existing handoff records.
- Rejected and completed file operations are logged where applicable.
- Transport host validation helps protect against certain DNS rebinding attacks.

**Important limitation:** Host validation is not authentication. This project does not implement OAuth or another authentication mechanism for its remote MCP endpoint. Anyone who obtains the active public tunnel URL may be able to attempt tool calls. Keep the tunnel active only when needed for testing or demonstration, stop it afterward, and do not place sensitive information in the workspace.

## Limitations

- The remote connection depends on the local Python server and ngrok tunnel remaining active.
- The public ngrok hostname may change and require configuration updates.
- The tools are designed for controlled workspace file operations, not unrestricted access to the computer.
- The project demonstrates cross-session handoffs through saved files; it does not automatically preserve every detail of an AI conversation.

## Evidence and Documentation

Screenshots of the following can be included in the project documentation:

- MCP Inspector displaying the available tools.
- Claude.ai successfully calling the MCP tools.
- A separate conversation reading and updating the handoff files.
- The resulting files inside the local workspace.
- Automated tests passing in the terminal.

## Author

Developed as an academic project demonstrating a custom MCP file-server connector, sandboxed file operations, and cross-session AI task continuity.