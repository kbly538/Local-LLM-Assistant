from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Result[T]:
    success: bool
    data: T | None = None
    error: str | None = None

    @classmethod
    def ok(cls, data: T) -> Result[T]:
        return cls(
            success=True,
            data=data,
            error=None,
        )

    @classmethod
    def fail(cls, error: str) -> Result[T]:
        return cls(
            success=False,
            data=None,
            error=error,
        )

    def __post_init__(self) -> None:
        if self.success:
            if self.error is not None:
                raise ValueError("Successful result cannot contain an error.")
        else:
            if self.error is None:
                raise ValueError("Failed result must contain an error.")

            if self.data is not None:
                raise ValueError("Failed result cannot contain data.")
