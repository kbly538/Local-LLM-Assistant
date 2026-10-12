import os

from openai.types.chat import ChatCompletionToolUnionParam

from aiagent.tools.result import Result
from aiagent.utils.resolve_safe_path import resolve_safe_path

MAX_DIRECTORY_ENTRIES = 500


SCHEMA_LIST_DIRECTORY: ChatCompletionToolUnionParam = {
    "type": "function",
    "function": {
        "name": "get_files_info",
        "description": (
            "Lists files in a specified directory relative to the working "
            "directory, providing file size and directory status"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": (
                        "Directory path to list files from, relative to the "
                        "working directory. Defaults to the working directory."
                    ),
                },
            },
            "additionalProperties": False,
        },
    },
}


def list_directory(
    working_directory: str,
    directory: str = ".",
) -> Result[str]:
    try:
        target_dir = resolve_safe_path(
            working_directory,
            directory,
        )

        if not target_dir.exists():
            return Result(
                success=False,
                error=(f'Directory not found: "{safe_text(directory)}"'),
            )

        if not target_dir.is_dir():
            return Result(
                success=False,
                error=(f'Path is not a directory: "{safe_text(directory)}"'),
            )

        results: list[str] = [f'Results for directory "{safe_text(directory)}":\n']

        with os.scandir(target_dir) as entries:
            for index, entry in enumerate(entries):
                if index >= MAX_DIRECTORY_ENTRIES:
                    results.append(
                        f"... listing truncated after {MAX_DIRECTORY_ENTRIES} entries\n"
                    )
                    break

                try:
                    stat = entry.stat(
                        follow_symlinks=False,
                    )

                    results.append(
                        f"- {safe_text(entry.name)}: "
                        f"file_size={stat.st_size} bytes, "
                        "is_dir="
                        f"{entry.is_dir(follow_symlinks=False)}\n"
                    )

                except OSError as error:
                    results.append(
                        f"- {safe_text(entry.name)}: "
                        "Error reading metadata: "
                        f"{safe_text(str(error))}\n"
                    )

        return Result(
            success=True,
            data="".join(results),
        )

    except PermissionError as error:
        return Result(
            success=False,
            error=safe_text(str(error)),
        )

    except OSError as error:
        return Result(
            success=False,
            error=(f"Could not list the requested directory: {safe_text(str(error))}"),
        )


def safe_text(value: str) -> str:
    # TODO: Move this sanitization to the central ToolResult serializer.
    return value.encode(
        "utf-8",
        errors="backslashreplace",
    ).decode("utf-8")
