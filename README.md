# Local LLM Assistant

Local AI coding agent in Python that uses Ollama to interact with language models and execute development related tasks through a modular tool system.

*I built this project to explore how AI coding agents work beyond simple text generation, focusing on tool calling, file operations, error handling, and testable Python code.*

## Features

**Local LLM Integration**
- Connects to Ollama through an OpenAI compatible API (with a somewhat hacky solution due to incompatabilities between libraries.).
- Uses a locally hosted language model instead of cloud.
- Supports interactive conversations through a commandline interface.

**Multi-Step Tool Calling**
- Allows the model to request tool execution and use the results in subsequent responses.
- Maintains conversation history during the session.
- Limits agent execution to a maximum number of iterations to prevent endless tool calling loops.

**Modular Tool System**

The agent currently provides five tools:

| Tool | Description |
|---|---|
| `get_files_info` | List files and directories |
| `get_file_content` | Read text files |
| `write_file` | Create or overwrite files |
| `run_command` | Execute selected development commands |
| `validate_html` | Perform basic HTML structure and content checks |

Each tool has a defined function schema and is registered through a central dispatcher.

**Error Handling and Validation**
- Parses tool arguments and checks function signatures before execution.
- Uses a shared result structure to represent successful and failed operations.
- Handles invalid arguments, unknown tools, and execution errors.
- Applies path checks and execution limits to selected operations.

**Testing and Code Quality**
- pytest for automated testing.
- Ruff for linting and formatting.
- Pyright for static type checking.
- Type annotations and modular Python components.

## Architecture

The application follows a tool calling workflow:

1. The user submits a request through the CLI.
2. The request is sent to the local language model.
3. The model either generates a response or requests a tool call.
4. The dispatcher identifies and executes the requested tool.
5. The tool result is returned to the model.
6. The process continues until the model responds or the iteration limit is reached.

The tool dispatcher is responsible for resolving tool names, parsing arguments, handling execution errors, and serializing results.

## Tech Stack

- **Language:** Python 3.12+
- **LLM Runtime:** Ollama
- **Model:** Configurable in source; I used `ornith:9b`
- **API Client:** OpenAI Python SDK (Ollama-compatible endpoint)
- **Dependency Management:** uv
- **Testing:** pytest
- **Linting & Formatting:** Ruff
- **Type Checking:** Pyright

## Getting Started

### Requirements

- Python 3.12+
- uv
- Ollama
- A locally installed model supporting tool calling

### Installation

Clone the repository:

`git clone https://github.com/kbly538/Local-LLM-Assistant.git`

Enter the project directory:

`cd Local-LLM-Assistant`

Install dependencies:

`uv sync`

Ensure Ollama is running and the model specified in `src/aiagent/config.py` is available.

Create the agent working directory:

`mkdir -p agent_space`

### Running the Agent

Start an interactive session:

`uv run qb-agent`

Or pass a prompt directly:

`uv run qb-agent "List the files in the working directory"`

Enable verbose output:

`uv run qb-agent --verbose`

## Development

Run the test suite:

`uv run pytest`

Check linting:

`uv run ruff check .`

Check formatting:

`uv run ruff format --check .`

Run static type checking:

`uv run pyright`

## Security Considerations

This is an experimental local coding agent, not a production-ready execution sandbox.

File tools use workspace path checks to restrict their intended access scope. Command execution uses an allowlist and timeout, but these controls do not provide complete process isolation.

The agent should only be used with trusted files in an appropriate development environment.

## Planned Improvements

- Introduce immutable result objects with stricter validation.
- Add file content search with bounded results.
- Improve context window and conversation history management.
- Strengthen command execution isolation.
- Expand unit and integration test coverage.

## Project Status

Personal learning project under active development, focused on understanding agent architecture, local inference, tool orchestration, and reliable software development practices.