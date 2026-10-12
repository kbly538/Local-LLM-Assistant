import os
from pathlib import Path

import pytest

import aiagent.tools.write_file as write_file_module
from aiagent.tools.write_file import write_file


# Fundamentals
def test_write_file_creates_file(tmp_path: Path):
    target_file = tmp_path / "hello.txt"

    result = write_file(
        working_directory=str(tmp_path),
        file_path="hello.txt",
        content="Hello world!",
    )

    assert target_file.exists()
    assert target_file.is_file()
    assert target_file.read_text(encoding="utf-8") == "Hello world!"
    assert result.data == ('Successfully wrote to "hello.txt" (12 characters written)')


def test_write_file_creates_missing_parent_directories(tmp_path: Path):
    result = write_file(
        working_directory=str(tmp_path),
        file_path="package/generated/output.txt",
        content="generated content",
    )

    target_file = tmp_path / "package" / "generated" / "output.txt"

    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") == "generated content"
    assert result.data == (
        'Successfully wrote to "package/generated/output.txt" (17 characters written)'
    )


def test_write_file_overwrites_existing_file(tmp_path: Path):
    target_file = tmp_path / "config.txt"
    target_file.write_text(
        "old content",
        encoding="utf-8",
    )

    result = write_file(
        working_directory=str(tmp_path),
        file_path="config.txt",
        content="new",
    )

    assert target_file.read_text(encoding="utf-8") == "new"
    assert result.data == ('Successfully wrote to "config.txt" (3 characters written)')


def test_write_file_supports_unicode(tmp_path: Path):
    content = "Merhaba dünya 🌍"

    result = write_file(
        working_directory=str(tmp_path),
        file_path="message.txt",
        content=content,
    )

    target_file = tmp_path / "message.txt"

    assert target_file.read_text(encoding="utf-8") == content
    assert result.data == (
        f'Successfully wrote to "message.txt" ({len(content)} characters written)'
    )


def test_write_file_writes_empty_content(tmp_path: Path):
    result = write_file(
        working_directory=str(tmp_path),
        file_path="empty.txt",
        content="",
    )

    target_file = tmp_path / "empty.txt"

    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") == ""
    assert result.data == ('Successfully wrote to "empty.txt" (0 characters written)')


# Security
def test_write_file_prevents_directory_escape(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = write_file(
        working_directory=str(workspace),
        file_path="../secret.txt",
        content="secret",
    )

    outside_file = tmp_path / "secret.txt"

    assert not outside_file.exists()
    assert result.success is False
    assert result.data is None
    assert result.error is not None
    assert result.error.startswith('Error: Permission denied for "../secret.txt":')
    assert "outside the permitted working directory" in result.error


@pytest.mark.skipif(
    os.name == "nt",
    reason="Symlink creation may require elevated privileges on Windows.",
)
def test_write_file_prevents_symlink_escape(tmp_path: Path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"

    workspace.mkdir()
    outside.mkdir()

    symlink = workspace / "external"
    symlink.symlink_to(
        outside,
        target_is_directory=True,
    )

    result = write_file(
        working_directory=str(workspace),
        file_path="external/secret.txt",
        content="secret",
    )

    assert not (outside / "secret.txt").exists()
    assert result.success is False
    assert result.data is None
    assert result.error is not None
    assert result.error.startswith(
        'Error: Permission denied for "external/secret.txt":'
    )
    assert "outside the permitted working directory" in result.error


def test_write_file_returns_error_when_target_is_directory(
    tmp_path: Path,
):
    directory = tmp_path / "documents"
    directory.mkdir()

    result = write_file(
        working_directory=str(tmp_path),
        file_path="documents",
        content="hello",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == (
        'Error: Cannot write to "documents" because it is a directory'
    )


# Error management
def test_write_file_returns_permission_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    def raise_permission_error(
        self: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        raise PermissionError("access denied")

    monkeypatch.setattr(
        Path,
        "write_text",
        raise_permission_error,
    )

    result = write_file(
        working_directory=str(tmp_path),
        file_path="hello.txt",
        content="hello",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == ('Error: Permission denied for "hello.txt": access denied')


def test_write_file_returns_os_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    def raise_os_error(
        self: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        raise OSError("disk failure")

    monkeypatch.setattr(
        Path,
        "write_text",
        raise_os_error,
    )

    result = write_file(
        working_directory=str(tmp_path),
        file_path="hello.txt",
        content="hello",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == ('Error: Could not write "hello.txt": disk failure')


def test_write_file_returns_invalid_path_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    def raise_value_error(
        *,
        working_directory: Path,
        requested_path: str,
    ) -> Path:
        raise ValueError("invalid path")

    monkeypatch.setattr(
        write_file_module,
        "resolve_safe_path",
        raise_value_error,
    )

    result = write_file(
        working_directory=str(tmp_path),
        file_path="hello.txt",
        content="hello",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == ('Error: Invalid path "hello.txt": invalid path')
