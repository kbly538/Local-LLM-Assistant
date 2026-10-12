from __future__ import annotations

import os
import signal
import subprocess
import threading
from dataclasses import dataclass, field
from typing import BinaryIO

_READ_CHUNK_SIZE = 8 * 1024
DEFAULT_MAX_OUTPUT_BYTES = 100_000


@dataclass(slots=True)
class _StreamCapture:
    data: bytearray = field(default_factory=bytearray)
    truncated: bool = False


def _read_stream(
    stream: BinaryIO,
    capture: _StreamCapture,
    *,
    max_bytes: int,
) -> None:
    try:
        while chunk := stream.read(_READ_CHUNK_SIZE):
            remaining = max_bytes - len(capture.data)

            if remaining > 0:
                capture.data.extend(chunk[:remaining])

            if len(chunk) > max(remaining, 0):
                capture.truncated = True
    finally:
        stream.close()


def _render_capture(
    capture: _StreamCapture,
    *,
    label: str,
    max_bytes: int,
) -> str:
    text = bytes(capture.data).decode("utf-8", errors="replace").rstrip()

    if capture.truncated:
        marker = f"[...{label} truncated at {max_bytes} bytes]"
        return f"{text}\n{marker}" if text else marker

    return text


def _start_process(
    process_args: list[str],
    *,
    cwd: str,
) -> subprocess.Popen[bytes]:
    common_kwargs = {
        "cwd": cwd,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "shell": False,
    }

    if os.name == "nt":
        return subprocess.Popen(
            process_args,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            **common_kwargs,
        )

    return subprocess.Popen(
        process_args,
        start_new_session=True,
        **common_kwargs,
    )


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return

    if os.name == "nt":
        try:
            subprocess.run(
                [
                    "taskkill",
                    "/PID",
                    str(process.pid),
                    "/T",
                    "/F",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    if process.poll() is None:
        process.kill()


def execute_process(
    process_args: list[str],
    *,
    cwd: str,
    timeout_seconds: int = 30,
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
) -> subprocess.CompletedProcess[str]:
    process = _start_process(
        process_args,
        cwd=cwd,
    )

    assert process.stdout is not None
    assert process.stderr is not None

    stdout_capture = _StreamCapture()
    stderr_capture = _StreamCapture()

    stdout_thread = threading.Thread(
        target=_read_stream,
        args=(process.stdout, stdout_capture),
        kwargs={"max_bytes": max_output_bytes},
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_read_stream,
        args=(process.stderr, stderr_capture),
        kwargs={"max_bytes": max_output_bytes},
        daemon=True,
    )

    stdout_thread.start()
    stderr_thread.start()

    timed_out = False

    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process_tree(process)

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    stdout_thread.join(timeout=5)
    stderr_thread.join(timeout=5)

    stdout = _render_capture(
        stdout_capture,
        label="STDOUT",
        max_bytes=max_output_bytes,
    )
    stderr = _render_capture(
        stderr_capture,
        label="STDERR",
        max_bytes=max_output_bytes,
    )

    if timed_out:
        raise subprocess.TimeoutExpired(
            cmd=process_args,
            timeout=timeout_seconds,
            output=stdout,
            stderr=stderr,
        )

    return subprocess.CompletedProcess(
        args=process_args,
        returncode=process.returncode,
        stdout=stdout,
        stderr=stderr,
    )
