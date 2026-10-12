import json

import pytest
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
    Function,
)

import aiagent.tools.dispatcher as dispatcher_module
from aiagent.tools.dispatcher import (
    call_function,
    create_tool_message,
    serialize_tool_result,
)
from aiagent.tools.result import Result


def test_serialize_tool_result_serializes_successful_result():
    # arrange
    success_result = Result.ok("success")

    # act
    json_dump_success = serialize_tool_result(success_result)

    # assert
    assert json.loads(json_dump_success) == {
        "success": True,
        "data": "success",
        "error": None,
    }


def test_serialize_tool_result_serializes_failed_result():
    # arrange
    failed_result = Result.fail("error occurred")

    # act
    json_dump_error = serialize_tool_result(failed_result)

    # assert
    assert json.loads(json_dump_error) == {
        "success": False,
        "data": None,
        "error": "error occurred",
    }


def test_create_tool_message_returns_tool_message():

    result = create_tool_message(
        tool_call_id="call-123",
        content="hello",
    )

    assert result == {
        "role": "tool",
        "tool_call_id": "call-123",
        "content": "hello",
    }


def test_call_function_calls_matching_tool(monkeypatch: pytest.MonkeyPatch):
    received_arguments: dict[str, str] = {}

    def fake_tool(
        working_directory: str,
        file_path: str,
    ) -> Result[str]:
        received_arguments["working_directory"] = working_directory
        received_arguments["file_path"] = file_path

        return Result.ok("file content")

    monkeypatch.setitem(
        dispatcher_module.FUNCTION_MAP,
        "read_file",
        fake_tool,
    )

    tool_call = create_tool_call(
        tool_call_id="call-123",
        function_name="read_file",
        arguments={
            "file_path": "hello.txt",
        },
    )

    result = call_function(tool_call)

    assert received_arguments == {
        "working_directory": dispatcher_module.WORKING_DIRECTORY,
        "file_path": "hello.txt",
    }

    assert result["role"] == "tool"
    assert result["tool_call_id"] == "call-123"
    content = result["content"]
    assert isinstance(content, str)
    assert json.loads(content) == {
        "success": True,
        "data": "file content",
        "error": None,
    }


def test_call_function_returns_error_for_unknown_function():
    tool_call = create_tool_call(
        tool_call_id="call-123",
        function_name="unknown_tool",
        arguments={},
    )

    result = call_function(tool_call)

    assert result["role"] == "tool"
    assert result["tool_call_id"] == "call-123"

    content = result["content"]
    assert isinstance(content, str)
    assert content == "Error: Unknown function: 'unknown_tool'."


def test_call_function_returns_error_for_invalid_json():
    tool_call = create_tool_call(
        tool_call_id="call-123",
        function_name="read_file",
        arguments="{invalid json",
    )

    result = call_function(tool_call)

    content = result["content"]
    assert isinstance(content, str)
    assert "Invalid JSON arguments for 'read_file'" in content


def test_call_function_returns_error_when_arguments_are_not_json_object():
    tool_call = create_tool_call(
        tool_call_id="call-123",
        function_name="read_file",
        arguments='["hello.txt"]',
    )

    result = call_function(tool_call)

    content = result["content"]
    assert isinstance(content, str)
    assert content == ("Error: Arguments for 'read_file' must be a JSON object.")


def test_call_function_returns_error_for_missing_required_argument(
    monkeypatch: pytest.MonkeyPatch,
):
    tool_was_called = False

    def fake_tool(
        working_directory: str,
        file_path: str,
    ) -> Result[str]:
        nonlocal tool_was_called
        tool_was_called = True

        return Result.ok("file content")

    monkeypatch.setitem(
        dispatcher_module.FUNCTION_MAP,
        "read_file",
        fake_tool,
    )

    tool_call = create_tool_call(
        tool_call_id="call-123",
        function_name="read_file",
        arguments={},
    )

    result = call_function(tool_call)

    assert result["role"] == "tool"
    assert result["tool_call_id"] == "call-123"

    content = result["content"]
    assert isinstance(content, str)
    assert "Invalid arguments for tool 'read_file'" in content
    assert "missing a required argument: 'file_path'" in content

    assert tool_was_called is False


def test_call_function_returns_error_for_unexpected_argument(
    monkeypatch: pytest.MonkeyPatch,
):

    tool_was_called = False

    def fake_tool(
        working_directory: str,
        file_path: str,
    ) -> Result[str]:
        nonlocal tool_was_called
        tool_was_called = True

        return Result.ok("file content")

    monkeypatch.setitem(
        dispatcher_module.FUNCTION_MAP,
        "read_file",
        fake_tool,
    )

    tool_call = create_tool_call(
        tool_call_id="call-123",
        function_name="read_file",
        arguments={"file_path": "hello.txt", "color": "red"},
    )
    result = call_function(tool_call)

    assert result["role"] == "tool"
    assert result["tool_call_id"] == "call-123"

    content = result["content"]
    assert isinstance(content, str)
    assert "Invalid arguments for tool 'read_file'" in content
    assert "unexpected keyword argument 'color'" in content

    assert tool_was_called is False


def test_call_function_serializes_failed_tool_result(monkeypatch: pytest.MonkeyPatch):
    tool_was_called = False

    def fake_tool(
        working_directory: str,
        file_path: str,
    ) -> Result[str]:
        nonlocal tool_was_called
        tool_was_called = True

        return Result.fail("generic error message")

    monkeypatch.setitem(
        dispatcher_module.FUNCTION_MAP,
        "read_file",
        fake_tool,
    )

    tool_call = create_tool_call(
        tool_call_id="call-123",
        function_name="read_file",
        arguments={"file_path": "hello.txt"},
    )
    result = call_function(tool_call)

    assert result["role"] == "tool"
    assert result["tool_call_id"] == "call-123"

    content = result["content"]
    assert isinstance(content, str)
    assert json.loads(content) == {
        "success": False,
        "data": None,
        "error": "generic error message",
    }

    assert tool_was_called is True


def test_call_function_returns_error_when_tool_raises_exception(
    monkeypatch: pytest.MonkeyPatch,
):

    tool_was_called = False

    def fake_tool(
        working_directory: str,
        file_path: str,
    ) -> Result[str]:
        nonlocal tool_was_called
        tool_was_called = True
        raise RuntimeError("random exception")

    monkeypatch.setitem(
        dispatcher_module.FUNCTION_MAP,
        "read_file",
        fake_tool,
    )

    tool_call = create_tool_call(
        tool_call_id="call-123",
        function_name="read_file",
        arguments={"file_path": "hello.txt"},
    )

    result = call_function(tool_call)

    assert tool_was_called is True
    assert result["role"] == "tool"
    assert result["tool_call_id"] == "call-123"

    content = result["content"]
    assert isinstance(content, str)
    assert content == ("Error: Tool 'read_file' failed: RuntimeError: random exception")


def test_call_function_treats_empty_argument_string_as_empty_object(
    monkeypatch: pytest.MonkeyPatch,
):
    received_arguments: dict[str, str] = {}

    def fake_tool(
        working_directory: str,
    ) -> Result[str]:
        received_arguments["working_directory"] = working_directory
        return Result.ok("success")

    monkeypatch.setitem(
        dispatcher_module.FUNCTION_MAP,
        "fake_tool",
        fake_tool,
    )

    tool_call = create_tool_call(
        tool_call_id="call-123",
        function_name="fake_tool",
        arguments="",
    )

    result = call_function(tool_call)

    assert received_arguments == {
        "working_directory": dispatcher_module.WORKING_DIRECTORY,
    }

    content = result["content"]
    assert isinstance(content, str)
    assert json.loads(content) == {
        "success": True,
        "data": "success",
        "error": None,
    }


def test_call_function_prints_function_name_in_non_verbose_mode(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    tool_was_called = False

    def fake_tool(
        working_directory: str,
        file_path: str,
    ) -> Result[str]:
        nonlocal tool_was_called
        tool_was_called = True

        return Result.ok("Meaningful context")

    monkeypatch.setitem(
        dispatcher_module.FUNCTION_MAP,
        "read_file",
        fake_tool,
    )

    tool_call = create_tool_call(
        tool_call_id="call-123",
        function_name="read_file",
        arguments={"file_path": "hello.txt"},
    )
    call_function(tool_call, verbose=False)
    captured = capsys.readouterr()
    assert "Calling function: read_file" in captured.out
    assert "'file_path': 'hello.txt'" not in captured.out
    assert (
        f"'working_directory': '{dispatcher_module.WORKING_DIRECTORY}'"
        not in captured.out
    )

    assert tool_was_called is True


def test_call_function_prints_arguments_in_verbose_mode(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    tool_was_called = False

    def fake_tool(
        working_directory: str,
        file_path: str,
    ) -> Result[str]:
        nonlocal tool_was_called
        tool_was_called = True

        return Result.ok("Meaningful context")

    monkeypatch.setitem(
        dispatcher_module.FUNCTION_MAP,
        "read_file",
        fake_tool,
    )

    tool_call = create_tool_call(
        tool_call_id="call-123",
        function_name="read_file",
        arguments={"file_path": "hello.txt"},
    )
    call_function(tool_call, verbose=True)
    captured = capsys.readouterr()
    assert "Calling function: read_file" in captured.out
    assert "'file_path': 'hello.txt'" in captured.out
    assert (
        f"'working_directory': '{dispatcher_module.WORKING_DIRECTORY}'" in captured.out
    )

    assert tool_was_called is True


# HELPERS


# hides OpenAI tool-call object creation
def create_tool_call(
    *,
    tool_call_id: str,
    function_name: str,
    arguments: dict[str, object] | str,
) -> ChatCompletionMessageFunctionToolCall:
    serialized_arguments = (
        arguments if isinstance(arguments, str) else json.dumps(arguments)
    )
    return ChatCompletionMessageFunctionToolCall(
        id=tool_call_id,
        type="function",
        function=Function(
            name=function_name,
            arguments=serialized_arguments,
        ),
    )
