import pathlib
import subprocess
from importlib import import_module
from typing import Never

import pytest

from aiagent.tools.run_command import (
    MAX_OUTPUT_CHARS,
    format_process_result,
    run_command,
)

run_command_module = import_module("aiagent.tools.run_command")


def test_run_command_executes_python_file_successfully(tmp_path: pathlib.Path):
    script = tmp_path / "hello.py"
    script.write_text('print("hello world")', encoding="utf-8")

    result = run_command(
        working_directory=str(tmp_path),
        command="python",
        args=["hello.py"],
    )

    assert result.success is True
    assert result.data is not None
    assert "Exit code: 0" in result.data
    assert "STDOUT:\nhello world" in result.data
    assert result.error is None


def test_run_command_passes_arguments_to_python_file(tmp_path: pathlib.Path):
    script = tmp_path / "args.py"
    script.write_text(
        'import sys\nprint("|".join(sys.argv[1:]))',
        encoding="utf-8",
    )

    result = run_command(
        working_directory=str(tmp_path),
        command="python",
        args=["args.py", "first", "second value"],
    )

    assert result.success is True
    assert result.data is not None
    assert "first|second value" in result.data


def test_run_command_returns_stdout(tmp_path: pathlib.Path):
    script = tmp_path / "stdout.py"
    script.write_text(
        'print("line 1")\nprint("line 2")',
        encoding="utf-8",
    )

    result = run_command(
        working_directory=str(tmp_path),
        command="python",
        args=["stdout.py"],
    )

    assert result.success is True
    assert result.data is not None
    assert "STDOUT:\nline 1\nline 2" in result.data


def test_run_command_returns_stderr(tmp_path: pathlib.Path):
    script = tmp_path / "stderr.py"
    script.write_text(
        'import sys\nprint("warning", file=sys.stderr)',
        encoding="utf-8",
    )

    result = run_command(
        working_directory=str(tmp_path),
        command="python",
        args=["stderr.py"],
    )

    assert result.success is True
    assert result.data is not None
    assert "STDERR:\nwarning" in result.data


def test_run_command_returns_exit_code_when_process_fails(
    tmp_path: pathlib.Path,
):
    script = tmp_path / "failure.py"
    script.write_text(
        'import sys\nprint("broken", file=sys.stderr)\nsys.exit(7)',
        encoding="utf-8",
    )

    result = run_command(
        working_directory=str(tmp_path),
        command="python",
        args=["failure.py"],
    )

    assert result.success is False
    assert result.data is None
    assert result.error is not None
    assert "Exit code: 7" in result.error
    assert "broken" in result.error


def test_run_command_returns_no_output(
    tmp_path: pathlib.Path,
):
    script = tmp_path / "silent.py"
    script.write_text("pass", encoding="utf-8")

    result = run_command(
        working_directory=str(tmp_path),
        command="python",
        args=["silent.py"],
    )

    assert result.success is True
    assert result.data is not None
    assert "Exit code: 0" in result.data
    assert "STDOUT:\n\nSTDERR:\n" in result.data


def test_run_command_rejects_missing_file(
    tmp_path: pathlib.Path,
):
    result = run_command(
        working_directory=str(tmp_path),
        command="python",
        args=["missing.py"],
    )

    assert result.success is False
    assert result.error is not None
    assert "missing.py" in result.error
    assert "Exit code:" in result.error


def test_run_command_rejects_directory_path(
    tmp_path: pathlib.Path,
):
    directory = tmp_path / "package.py"
    directory.mkdir()

    result = run_command(
        working_directory=str(tmp_path),
        command="python",
        args=["package.py"],
    )

    assert result.success is False
    assert result.error is not None
    assert "package.py" in result.error


def test_run_command_rejects_disallowed_command(
    tmp_path: pathlib.Path,
):
    result = run_command(
        working_directory=str(tmp_path),
        command="bash",
    )

    assert result.success is False
    assert result.error == 'Error: Command "bash" is not permitted'


@pytest.mark.xfail(
    strict=True,
    reason="Current implementation does not prevent workspace escape",
)
def test_run_command_prevents_directory_escape(
    tmp_path: pathlib.Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside_script = tmp_path / "outside.py"
    outside_script.write_text(
        'print("secret")',
        encoding="utf-8",
    )

    result = run_command(
        working_directory=str(workspace),
        command="python",
        args=["../outside.py"],
    )

    assert result.success is False


@pytest.mark.xfail(
    strict=True,
    reason="Current implementation does not prevent symlink escape",
)
def test_run_command_prevents_symlink_escape(
    tmp_path: pathlib.Path,
):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"

    workspace.mkdir()
    outside.mkdir()

    outside_script = outside / "secret.py"
    outside_script.write_text(
        'print("secret")',
        encoding="utf-8",
    )

    symlink = workspace / "linked.py"
    symlink.symlink_to(outside_script)

    result = run_command(
        working_directory=str(workspace),
        command="python",
        args=["linked.py"],
    )

    assert result.success is False


def test_run_command_returns_timeout_error(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
):
    def raise_timeout(
        *args: object,
        **kwargs: object,
    ) -> Never:
        raise subprocess.TimeoutExpired(
            cmd=["python"],
            timeout=30,
        )

    monkeypatch.setattr(
        run_command_module,
        "execute_process",
        raise_timeout,
    )

    result = run_command(
        working_directory=str(tmp_path),
        command="python",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == "Error: Process exceeded the 30-second timeout"


def test_run_command_returns_os_error(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
):
    def raise_os_error(
        *args: object,
        **kwargs: object,
    ) -> Never:
        raise OSError("permission denied")

    monkeypatch.setattr(
        run_command_module,
        "execute_process",
        raise_os_error,
    )

    result = run_command(
        working_directory=str(tmp_path),
        command="python",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == ("Error: Could not execute command: permission denied")


def test_run_command_rejects_invalid_working_directory(
    tmp_path: pathlib.Path,
):
    result = run_command(
        working_directory=str(tmp_path / "missing"),
        command="python",
    )

    assert result.success is False
    assert result.error is not None
    assert "does not exist" in result.error


def test_run_command_truncates_large_output():
    process = subprocess.CompletedProcess(
        args=["python"],
        returncode=0,
        stdout="a" * (MAX_OUTPUT_CHARS + 1),
        stderr="",
    )

    result = format_process_result(process)

    assert result.success is True
    assert result.data is not None
    assert "stdout truncated" in result.data
