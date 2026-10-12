import os
import signal
import subprocess


def execute_process(
    process_args: list[str],
    *,
    cwd: str,
    timeout_seconds: int = 30,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        process_args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )

    try:
        stdout, stderr = process.communicate(
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        os.killpg(
            os.getpgid(process.pid),
            signal.SIGKILL,
        )

        stdout, stderr = process.communicate()

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
