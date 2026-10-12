import inspect
import json
import logging
from collections.abc import Callable
from typing import cast

from openai.types.chat import (
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionToolMessageParam,
    ChatCompletionToolUnionParam,
)

from aiagent.config import WORKING_DIRECTORY
from aiagent.tools.list_directory import (
    SCHEMA_LIST_DIRECTORY,
    list_directory,
)
from aiagent.tools.read_file import (
    SCHEMA_READ_FILE,
    read_file,
)
from aiagent.tools.result import Result
from aiagent.tools.run_command import (
    SCHEMA_RUN_COMMAND,
    run_command,
)
from aiagent.tools.validate_html import (
    SCHEMA_VALUDATE_HTML,
    validate_html,
)
from aiagent.tools.write_file import (
    SCHEMA_WRITE_FILE,
    write_file,
)

logger = logging.getLogger(__name__)

available_functions: list[ChatCompletionToolUnionParam] = [
    SCHEMA_LIST_DIRECTORY,
    SCHEMA_READ_FILE,
    SCHEMA_WRITE_FILE,
    SCHEMA_RUN_COMMAND,
    SCHEMA_VALUDATE_HTML,
]


FUNCTION_MAP: dict[str, Callable[..., Result[str]]] = {
    "get_file_content": read_file,
    "get_files_info": list_directory,
    "write_file": write_file,
    "run_command": run_command,
    "validate_html": validate_html,
}


def serialize_tool_result(result: Result[str]) -> str:

    return json.dumps(
        {
            "success": result.success,
            "data": result.data,
            "error": result.error,
        },
        ensure_ascii=False,
    )


def create_tool_message(
    tool_call_id: str,
    content: str,
) -> ChatCompletionToolMessageParam:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    }


def call_function(
    tool_call: ChatCompletionMessageFunctionToolCall,
    verbose: bool = False,
) -> ChatCompletionToolMessageParam:
    function_name = tool_call.function.name

    decoded_arguments: object

    try:
        decoded_arguments = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError as error:
        return create_tool_message(
            tool_call.id,
            (f"Error: Invalid JSON arguments for '{function_name}': {error}"),
        )

    if not isinstance(decoded_arguments, dict):
        return create_tool_message(
            tool_call.id,
            (f"Error: Arguments for '{function_name}' must be a JSON object."),
        )

    raw_arguments = cast(
        dict[object, object],
        decoded_arguments,
    )

    function_args: dict[str, object] = {}

    for key, value in raw_arguments.items():
        if not isinstance(key, str):
            return create_tool_message(
                tool_call.id,
                (f"Error: Argument names for '{function_name}' must be strings."),
            )

        function_args[key] = value

    function_to_call = FUNCTION_MAP.get(function_name)

    if function_to_call is None:
        return create_tool_message(
            tool_call.id,
            f"Error: Unknown function: '{function_name}'.",
        )

    function_args["working_directory"] = WORKING_DIRECTORY

    if verbose:
        print(f" - Calling function: {function_name}({function_args})")
    else:
        print(f" - Calling function: {function_name}")

    signature = inspect.signature(function_to_call)

    try:
        signature.bind(**function_args)
    except TypeError as error:
        return create_tool_message(
            tool_call.id,
            (f"Error: Invalid arguments for tool '{function_name}': {error}"),
        )

    try:
        result = function_to_call(**function_args)
    except Exception as error:
        logger.exception(
            "Tool '%s' execution failed",
            function_name,
        )

        return create_tool_message(
            tool_call.id,
            (f"Error: Tool '{function_name}' failed: {type(error).__name__}: {error}"),
        )

    return create_tool_message(
        tool_call.id,
        serialize_tool_result(result),
    )
