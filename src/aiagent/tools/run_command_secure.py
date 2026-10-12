from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from openai.types.chat import ChatCompletionToolUnionParam

from aiagent.tools.result import Result
from aiagent.utils.execute_process_secure import execute_process

SCHEMA_RUN_COMMAND: ChatCompletionToolUnionParam = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": (
            "Runs an allowed development command in an isolated, "
            "network-disabled container and returns its output."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "enum": ["python", "pytest", "ruff"],
                    "description": "Allowed command to execute.",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Arguments passed to the command.",
                    "default": [],
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
}

SANDBOX_IMAGE = "aiagent-sandbox:latest"
MAX_ARGUMENTS = 128
MAX_ARGUMENT_LENGTH = 4096
DOCKER_INFRASTRUCTURE_EXIT_CODES = frozenset({125, 126, 127})

COMMAND_PREFIXES: dict[str, list[str]] = {
    "python": ["python", "-B"],
    "pytest": ["python", "-B", "-m", "pytest", "-p", "no:cacheprovider"],
    "ruff": ["ruff", "--no-cache"],
}

SNAPSHOT_IGNORE_PATTERNS = (
    ".git",
    ".venv",
    "venv",
    ".env",
    ".env.*",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".coverage",
    "htmlcov",
    "dist",
    "build",
    "node_modules",
    "*.pem",
    "*.key",
    "id_rsa",
    "id_ed25519",
)


def _validate_request(
    command: str,
    args: list[str],
) -> str | None:
    if command not in COMMAND_PREFIXES:
        return f'Error: Command "{command}" is not permitted'

    if len(args) > MAX_ARGUMENTS:
        return f"Error: Too many command arguments; maximum is {MAX_ARGUMENTS}"

    for argument in args:
        if "\x00" in argument:
            return "Error: Command arguments cannot contain null bytes"

        if len(argument) > MAX_ARGUMENT_LENGTH:
            return (
                "Error: Command argument exceeds the maximum length of "
                f"{MAX_ARGUMENT_LENGTH} characters"
            )

    return None


@contextmanager
def _sandbox_snapshot(source: Path) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="aiagent-sandbox-") as temp_dir:
        destination = Path(temp_dir) / "workspace"

        shutil.copytree(
            source,
            destination,
            symlinks=True,
            ignore=shutil.ignore_patterns(*SNAPSHOT_IGNORE_PATTERNS),
        )

        yield destination


def _build_docker_command(
    *,
    snapshot: Path,
    container_name: str,
    command: str,
    args: list[str],
) -> list[str]:
    container_command = [*COMMAND_PREFIXES[command], *args]

    return [
        "docker",
        "run",
        "--name",
        container_name,
        "--rm",
        "--pull=never",
        "--network=none",
        "--memory=512m",
        "--memory-swap=512m",
        "--cpus=1.0",
        "--pids-limit=64",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges=true",
        "--security-opt=seccomp=builtin",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,noexec,size=64m",
        "--shm-size=64m",
        "--ulimit",
        "nofile=256:256",
        "--ulimit",
        "nproc=64:64",
        "--init",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "PYTHONUNBUFFERED=1",
        "--env",
        "HOME=/tmp/home",
        "--env",
        "XDG_CACHE_HOME=/tmp/cache",
        "--env",
        "PYTHONPATH=/workspace/src",
        "--mount",
        f"type=bind,source={snapshot},target=/workspace,readonly",
        "--workdir",
        "/workspace",
        SANDBOX_IMAGE,
        *container_command,
    ]


def _force_remove_container(container_name: str) -> None:
    try:
        subprocess.run(
            ["docker", "rm", "--force", container_name],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def _format_process_result(
    completed_process: subprocess.CompletedProcess[str],
) -> str:
    result_parts: list[str] = []

    if completed_process.returncode != 0:
        result_parts.append(f"Process exited with code {completed_process.returncode}.")

    if completed_process.stdout:
        result_parts.append(f"STDOUT:\n{completed_process.stdout}")

    if completed_process.stderr:
        result_parts.append(f"STDERR:\n{completed_process.stderr}")

    if not result_parts:
        result_parts.append("No output produced")

    return "\n".join(result_parts)


def run_command(
    working_directory: str,
    command: str,
    args: list[str] | None = None,
) -> Result[str]:
    command_args = list(args or [])

    validation_error = _validate_request(command, command_args)
    if validation_error is not None:
        return Result.fail(validation_error)

    workspace = Path(working_directory).resolve()

    if not workspace.is_dir():
        return Result.fail(
            f'Error: Working directory "{working_directory}" '
            "does not exist or is not a directory"
        )

    if shutil.which("docker") is None:
        return Result.fail("Error: Docker CLI could not be found")

    container_name = f"aiagent-{uuid.uuid4().hex}"

    try:
        with _sandbox_snapshot(workspace) as snapshot:
            docker_command = _build_docker_command(
                snapshot=snapshot,
                container_name=container_name,
                command=command,
                args=command_args,
            )

            completed_process = execute_process(
                docker_command,
                cwd=os.fspath(workspace),
                timeout_seconds=30,
                max_output_bytes=100_000,
            )

        if completed_process.returncode in DOCKER_INFRASTRUCTURE_EXIT_CODES:
            return Result.fail(
                "Error: Docker could not start the sandbox command\n"
                + _format_process_result(completed_process)
            )

        return Result.ok(_format_process_result(completed_process))

    except subprocess.TimeoutExpired:
        _force_remove_container(container_name)
        return Result.fail("Error: Process exceeded the 30-second timeout")

    except OSError as error:
        _force_remove_container(container_name)
        return Result.fail(f"Error: Could not execute sandbox command: {error}")

    finally:
        _force_remove_container(container_name)
