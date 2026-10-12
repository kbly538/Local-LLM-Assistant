from pathlib import Path

from aiagent.tools.list_directory import list_directory


def test_list_directory_returns_success(tmp_path: Path):
    result = list_directory(
        working_directory=str(tmp_path),
        directory=".",
    )

    assert result.success is True
    assert result.error is None
    assert result.data is not None


def test_list_directory_lists_directory_contents(tmp_path: Path):
    (tmp_path / "hello.txt").write_text("hello")
    (tmp_path / "config.json").write_text("{}")

    result = list_directory(
        working_directory=str(tmp_path),
        directory=".",
    )

    assert result.success is True
    assert result.error is None
    assert result.data is not None
    assert "hello.txt" in result.data
    assert "config.json" in result.data


def test_list_directory_returns_error_for_missing_directory(tmp_path: Path):
    result = list_directory(
        working_directory=str(tmp_path),
        directory="missing",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == 'Directory not found: "missing"'


def test_list_directory_prevents_directory_escape(tmp_path: Path):
    result = list_directory(
        working_directory=str(tmp_path),
        directory="../",
    )

    assert result.success is False
    assert result.data is None
    assert result.error is not None
    assert "outside the permitted working directory" in result.error


def test_list_directory_returns_error_when_path_is_file(tmp_path: Path):
    file_path = tmp_path / "hello.txt"
    file_path.write_text("hello")

    result = list_directory(
        working_directory=str(tmp_path),
        directory="hello.txt",
    )

    assert result.success is False
    assert result.data is None
    assert result.error == 'Path is not a directory: "hello.txt"'


def test_list_directory_prevents_symlink_escape(tmp_path: Path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"

    workspace.mkdir()
    outside.mkdir()

    (outside / "secret.txt").write_text("secret")
    (workspace / "external").symlink_to(
        outside,
        target_is_directory=True,
    )

    result = list_directory(
        working_directory=str(workspace),
        directory="external",
    )

    assert result.success is False
    assert result.data is None
    assert result.error is not None
    assert "outside the permitted working directory" in result.error
