import os
import shutil
import subprocess

from openai.types.chat import ChatCompletionToolUnionParam

from aiagent.tools.result import Result
from aiagent.utils.execute_process import execute_process

SCHEMA_RUN_COMMAND: ChatCompletionToolUnionParam = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": (
            "Runs an allowed command inside the permitted working directory "
            "and returns its stdout, stderr, and exit code."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "Allowed command to execute, such as python, pytest, or ruff."
                    ),
                },
                "args": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": ("Command-line arguments passed to the command."),
                    "default": [],
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
}

ALLOWED_COMMANDS = frozenset(
    {
        "python",
        "pytest",
        "ruff",
    }
)


def run_command(
    working_directory: str,
    command: str,
    args: list[str] | None = None,
) -> Result[str]:
    try:
        abs_wd = os.path.realpath(working_directory)

        if not os.path.isdir(abs_wd):
            return Result.fail(
                f'Error: Working directory "{working_directory}" '
                "does not exist or is not a directory"
            )

        if command not in ALLOWED_COMMANDS:
            return Result.fail(f'Error: Command "{command}" is not permitted')

        executable = shutil.which(command)

        if executable is None:
            return Result.fail(f'Error: Command "{command}" could not be found')

        process_args = [executable]

        if args:
            process_args.extend(args)

        completed_process = execute_process(
            process_args,
            cwd=abs_wd,
            timeout_seconds=30,
        )

        return format_process_result(completed_process)

    except subprocess.TimeoutExpired:
        return Result.fail("Error: Process exceeded the 30-second timeout")

    except OSError as error:
        return Result.fail(f"Error: Could not execute command: {error}")


MAX_OUTPUT_CHARS = 100_000


def truncate_output(
    output: str,
    *,
    label: str,
) -> str:
    if len(output) <= MAX_OUTPUT_CHARS:
        return output

    return (
        output[:MAX_OUTPUT_CHARS]
        + f"\n[...{label} truncated at "
        + f"{MAX_OUTPUT_CHARS} characters]"
    )


def format_process_result(
    process: subprocess.CompletedProcess[str],
) -> Result[str]:
    output = (
        f"Exit code: {process.returncode}\n"
        f"STDOUT:\n{truncate_output(process.stdout or '', label='stdout')}\n"
        f"STDERR:\n{truncate_output(process.stderr or '', label='stderr')}"
    )

    if process.returncode != 0:
        return Result.fail(output)

    return Result.ok(output)
