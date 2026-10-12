import os
from pathlib import Path

import pytest

from aiagent.utils.resolve_safe_path import resolve_safe_path


def test_resolve_safe_path_returns_file_path(tmp_path: Path):
    file_path = tmp_path / "hello.txt"
    file_path.write_text("hello")

    result = resolve_safe_path(
        working_directory=tmp_path,
        requested_path="hello.txt",
    )

    assert result == file_path.resolve()


def test_resolve_safe_path_returns_working_directory(tmp_path: Path):
    result = resolve_safe_path(
        working_directory=tmp_path,
        requested_path=".",
    )

    assert result == tmp_path.resolve()


def test_resolve_safe_path_rejects_directory_escape(tmp_path: Path):
    with pytest.raises(PermissionError):
        resolve_safe_path(
            working_directory=tmp_path,
            requested_path="../",
        )


def test_resolve_safe_path_returns_nested_path(tmp_path: Path):
    nested = tmp_path / "src"
    nested.mkdir()

    result = resolve_safe_path(
        working_directory=tmp_path,
        requested_path="src",
    )

    assert result == nested.resolve()


@pytest.mark.skipif(
    os.name == "nt",
    reason="Symlink creation requires special permissions on Windows.",
)
def test_resolve_safe_path_rejects_symlink_escape(tmp_path: Path):
    outside = tmp_path.parent / "outside"
    outside.mkdir()

    link = tmp_path / "link"
    link.symlink_to(outside)

    with pytest.raises(PermissionError):
        resolve_safe_path(
            working_directory=tmp_path,
            requested_path="link",
        )


def test_resolve_safe_path_accepts_string_working_directory(tmp_path: Path):
    result = resolve_safe_path(
        working_directory=str(tmp_path),
        requested_path=".",
    )

    assert result == tmp_path.resolve()
