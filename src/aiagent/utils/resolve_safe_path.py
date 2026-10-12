from pathlib import Path


def resolve_safe_path(
    working_directory: str | Path,
    requested_path: str | Path,
) -> Path:
    root = Path(working_directory).resolve()
    target = (root / requested_path).resolve()

    if not target.is_relative_to(root):
        raise PermissionError("Path is outside the permitted working directory")

    return target
