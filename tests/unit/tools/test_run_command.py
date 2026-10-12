"""
relative path
→ güvenli mutlak path
→ dosya doğrulaması
→ Python komutu oluşturma
→ subprocess çalıştırma
→ stdout/stderr/exit code biçimlendirme
→ hata dönüşü
"""

import pathlib
import subprocess
from typing import Never

import pytest

import aiagent.tools.run_command as run_command_module
from aiagent.tools.run_command import run_command


def test_run_command_executes_python_file_successfully(tmp_path: pathlib.Path):
    script = tmp_path / "hello.py"
    script.write_text(
        'print("hello world")',
        encoding="utf-8",
    )

    result = run_command(
        working_directory=str(tmp_path),
        command="hello.py",
    )

    assert result.success is True
    assert result.data == "STDOUT:\nhello world"
    assert result.error is None


def test_run_command_passes_arguments_to_python_file(tmp_path: pathlib.Path):
    script = tmp_path / "args.py"
    script.write_text(
        'import sys\nprint("|".join(sys.argv[1:]))',
        encoding="utf-8",
    )

    result = run_command(
        working_directory=str(tmp_path),
        command="args.py",
        args=["first", "second value"],
    )

    assert result.success is True
    assert result.data == "STDOUT:\nfirst|second value"
    assert result.error is None


def test_run_command_returns_stdout(tmp_path: pathlib.Path):
    script = tmp_path / "stdout.py"
    script.write_text('print("line 1")\nprint("line 2")', encoding="utf-8")

    result = run_command(
        working_directory=str(tmp_path),
        command="stdout.py",
    )

    assert result.success is True
    assert result.data == "STDOUT:\nline 1\nline 2"
    assert result.error is None


def test_run_command_returns_stderr(tmp_path: pathlib.Path):
    script = tmp_path / "stderr.py"
    script.write_text('import sys\nprint("warning", file=sys.stderr)', encoding="utf-8")

    result = run_command(
        working_directory=str(tmp_path),
        command="stderr.py",
    )

    assert result.success is True
    assert result.data == "STDERR:\nwarning"
    assert result.error is None


def test_run_command_returns_exit_code_when_process_fails(tmp_path: pathlib.Path):
    script = tmp_path / "failure.py"
    script.write_text(
        'import sys\nprint("broken", file=sys.stderr)\nsys.exit(7)',
        encoding="utf-8",
    )

    result = run_command(
        working_directory=str(tmp_path),
        command="failure.py",
    )

    assert result.success is True
    assert result.data == ("Process exited with code 7.\nSTDERR:\nbroken")
    assert result.error is None


def test_run_command_returns_no_output_message_when_process_produces_no_output(
    tmp_path: pathlib.Path,
):
    script = tmp_path / "silent.py"
    script.write_text(
        "pass",
        encoding="utf-8",
    )

    result = run_command(
        working_directory=str(tmp_path),
        command="silent.py",
    )

    assert result.success is True
    assert result.data == "No output produced"
    assert result.error is None


def test_run_command_rejects_missing_file(
    tmp_path: pathlib.Path,
):
    result = run_command(
        working_directory=str(tmp_path),
        command="missing.py",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == (
        'Error: "missing.py" does not exist or is not a regular file'
    )


def test_run_command_rejects_directory_path(
    tmp_path: pathlib.Path,
):
    directory = tmp_path / "package.py"
    directory.mkdir()

    result = run_command(
        working_directory=str(tmp_path),
        command="package.py",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == (
        'Error: "package.py" does not exist or is not a regular file'
    )


def test_run_command_rejects_non_python_file(
    tmp_path: pathlib.Path,
):
    file = tmp_path / "notes.txt"
    file.write_text(
        "hello",
        encoding="utf-8",
    )

    result = run_command(
        working_directory=str(tmp_path),
        command="notes.txt",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == ('Error: "notes.txt" is not a x file')


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
        command="../outside.py",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == (
        'Error: Cannot execute "../outside.py" as it is outside '
        "the permitted working directory"
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
        command="linked.py",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == (
        'Error: Cannot execute "linked.py" as it is outside '
        "the permitted working directory"
    )


def test_run_command_returns_timeout_error(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
):
    script = tmp_path / "slow.py"
    script.write_text(
        "pass",
        encoding="utf-8",
    )

    def raise_timeout(
        *args: object,
        **kwargs: object,
    ) -> Never:
        raise subprocess.TimeoutExpired(
            cmd=["fake-command"],
            timeout=30,
        )

    monkeypatch.setattr(
        run_command_module.subprocess,
        "run",
        raise_timeout,
    )

    result = run_command(
        working_directory=str(tmp_path),
        command="slow.py",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == ("Error: Process exceeded the 30-second timeout")


def test_run_command_returns_os_error(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
):
    script = tmp_path / "hello.py"
    script.write_text(
        'print("hello")',
        encoding="utf-8",
    )

    def raise_os_error(
        *args: object,
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        raise OSError("permission denied")

    monkeypatch.setattr(
        run_command_module.subprocess,
        "run",
        raise_os_error,
    )

    result = run_command(
        working_directory=str(tmp_path),
        command="hello.py",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == ("Error: Could not execute Python file: permission denied")
