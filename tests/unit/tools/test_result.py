import pytest

from aiagent.tools.result import Result


def test_ok_creates_successful_result():
    result = Result.ok("ok")

    assert result.success is True
    assert result.data == "ok"
    assert result.error is None


def test_fail_creates_failed_result():
    result = Result.fail("error")

    assert result.success is False
    assert result.data is None
    assert result.error == "error"


def test_successful_result_cannot_contain_error():
    with pytest.raises(
        ValueError,
        match="Successful result cannot contain an error.",
    ):
        Result(
            success=True,
            data="ok",
            error="unexpected error",
        )


def test_failed_result_must_contain_error():
    with pytest.raises(
        ValueError,
        match="Failed result must contain an error.",
    ):
        Result[str](
            success=False,
            data=None,
            error=None,
        )


def test_failed_result_cannot_contain_data():
    with pytest.raises(
        ValueError,
        match="Failed result cannot contain data.",
    ):
        Result(
            success=False,
            data="unexpected data",
            error="error",
        )
