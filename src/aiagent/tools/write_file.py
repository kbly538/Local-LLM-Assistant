from pathlib import Path

from openai.types.chat import ChatCompletionToolUnionParam

from aiagent.tools.result import Result
from aiagent.utils.resolve_safe_path import resolve_safe_path

SCHEMA_WRITE_FILE: ChatCompletionToolUnionParam = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": (
            "Writes text content to a file inside the permitted working "
            "directory. Creates missing parent directories and overwrites "
            "the file if it already exists."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": (
                        "Path of the file to write, relative to the working "
                        "directory. Example: 'pkg/output.txt'"
                    ),
                },
                "content": {
                    "type": "string",
                    "description": "Text content to write to the file.",
                },
            },
            "required": ["file_path", "content"],
            "additionalProperties": False,
        },
    },
}


def write_file(
    working_directory: str,
    file_path: str,
    content: str,
) -> Result[str]:
    try:
        target_file = resolve_safe_path(
            working_directory=Path(working_directory),
            requested_path=file_path,
        )

        if target_file.is_dir():
            return Result.fail(
                f'Error: Cannot write to "{file_path}" because it is a directory'
            )

        target_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        written = target_file.write_text(
            content,
            encoding="utf-8",
        )

    except PermissionError as error:
        return Result.fail(f'Error: Permission denied for "{file_path}": {error}')

    except OSError as error:
        return Result.fail(f'Error: Could not write "{file_path}": {error}')

    except ValueError as error:
        return Result.fail(f'Error: Invalid path "{file_path}": {error}')

    return Result.ok(
        f'Successfully wrote to "{file_path}" ({written} characters written)'
    )
