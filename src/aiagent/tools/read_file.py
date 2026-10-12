from pathlib import Path

from openai.types.chat import ChatCompletionToolUnionParam

from aiagent.config import MAX_CHARS
from aiagent.tools.result import Result
from aiagent.utils.resolve_safe_path import resolve_safe_path

SCHEMA_READ_FILE: ChatCompletionToolUnionParam = {
    "type": "function",
    "function": {
        "name": "get_file_content",
        "description": (
            "Reads and returns the content of a file located inside "
            "the permitted working directory."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": (
                        "Path of the file to read, relative to the "
                        "working directory. Example: 'pkg/main.py'"
                    ),
                },
            },
            "required": ["file_path"],
            "additionalProperties": False,
        },
    },
}


def read_file(
    working_directory: str | Path,
    file_path: str | Path,
) -> Result[str]:
    try:
        target_file = resolve_safe_path(
            working_directory=working_directory,
            requested_path=file_path,
        )

        if not target_file.exists():
            return Result(
                success=False,
                data=None,
                error=f'File not found: "{file_path}"',
            )

        if not target_file.is_file():
            return Result(
                success=False,
                data=None,
                error=f'Path is not a regular file: "{file_path}"',
            )

        with target_file.open(
            mode="r",
            encoding="utf-8",
        ) as file:
            content = file.read(MAX_CHARS)

            if file.read(1):
                content += (
                    f'\n[...File "{file_path}" truncated at {MAX_CHARS} characters]'
                )

        return Result(
            success=True,
            data=content,
            error=None,
        )

    except PermissionError as error:
        return Result(
            success=False,
            data=None,
            error=str(error),
        )

    except UnicodeDecodeError:
        return Result(
            success=False,
            data=None,
            error=f'File is not valid UTF-8 text: "{file_path}"',
        )

    except OSError as error:
        return Result(
            success=False,
            data=None,
            error=f'Could not read file "{file_path}": {error}',
        )


if __name__ == "__main__":
    result = read_file(
        working_directory="calculator",
        file_path="main.py",
    )

    print(result)
