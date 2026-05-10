from __future__ import annotations

import subprocess


def run_cmd(cmd: str, timeout: int = 30) -> tuple[str, int]:
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return str(exc), 1
    return result.stdout.strip(), result.returncode
