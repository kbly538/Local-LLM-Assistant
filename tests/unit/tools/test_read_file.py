import os
from pathlib import Path

import pytest

import aiagent.tools.read_file as read_file_module
from aiagent.tools.read_file import read_file


def test_read_file_returns_file_content(tmp_path: Path):
    file = tmp_path / "hello.txt"
    file.write_text(
        "hello world",
        encoding="utf-8",
    )

    result = read_file(
        working_directory=str(tmp_path),
        file_path="hello.txt",
    )

    assert result.success is True
    assert result.data == "hello world"
    assert result.error is None


def test_read_file_reads_nested_file(tmp_path: Path):
    package = tmp_path / "package"
    package.mkdir()

    file = package / "main.py"
    file.write_text(
        'print("hello")',
        encoding="utf-8",
    )

    result = read_file(
        working_directory=str(tmp_path),
        file_path="package/main.py",
    )

    assert result.success is True
    assert result.data == 'print("hello")'
    assert result.error is None


def test_read_file_returns_error_for_missing_file(tmp_path: Path):
    result = read_file(
        working_directory=str(tmp_path),
        file_path="missing.txt",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == 'File not found: "missing.txt"'


def test_read_file_returns_error_when_path_is_directory(
    tmp_path: Path,
):
    directory = tmp_path / "documents"
    directory.mkdir()

    result = read_file(
        working_directory=str(tmp_path),
        file_path="documents",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == ('Path is not a regular file: "documents"')


def test_read_file_prevents_directory_escape(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside_file = tmp_path / "secret.txt"
    outside_file.write_text(
        "secret",
        encoding="utf-8",
    )

    result = read_file(
        working_directory=str(workspace),
        file_path="../secret.txt",
    )

    assert result.success is False
    assert result.data is None
    assert result.error is not None
    assert "outside the permitted working directory" in result.error


@pytest.mark.skipif(
    os.name == "nt",
    reason="Symlink creation may require elevated privileges on Windows",
)
def test_read_file_prevents_symlink_escape(tmp_path: Path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"

    workspace.mkdir()
    outside.mkdir()

    secret_file = outside / "secret.txt"
    secret_file.write_text(
        "secret",
        encoding="utf-8",
    )

    symlink = workspace / "external"
    symlink.symlink_to(
        outside,
        target_is_directory=True,
    )

    result = read_file(
        working_directory=str(workspace),
        file_path="external/secret.txt",
    )

    assert result.success is False
    assert result.data is None
    assert result.error is not None
    assert "outside the permitted working directory" in result.error


def test_read_file_supports_unicode(tmp_path: Path):
    file = tmp_path / "message.txt"
    file.write_text(
        "Merhaba dünya 🌍",
        encoding="utf-8",
    )

    result = read_file(
        working_directory=str(tmp_path),
        file_path="message.txt",
    )

    assert result.success is True
    assert result.data == "Merhaba dünya 🌍"
    assert result.error is None


def test_read_file_truncates_large_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        read_file_module,
        "MAX_CHARS",
        5,
    )

    file = tmp_path / "large.txt"
    file.write_text(
        "abcdefghij",
        encoding="utf-8",
    )

    result = read_file(
        working_directory=str(tmp_path),
        file_path="large.txt",
    )

    assert result.success is True
    assert result.data == ('abcde\n[...File "large.txt" truncated at 5 characters]')
    assert result.error is None


def test_read_file_does_not_truncate_at_exact_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        read_file_module,
        "MAX_CHARS",
        5,
    )

    file = tmp_path / "exact.txt"
    file.write_text(
        "abcde",
        encoding="utf-8",
    )

    result = read_file(
        working_directory=str(tmp_path),
        file_path="exact.txt",
    )

    assert result.success is True
    assert result.data == "abcde"
    assert result.error is None
