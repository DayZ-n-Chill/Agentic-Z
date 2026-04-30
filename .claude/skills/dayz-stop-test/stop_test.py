"""dayz-stop-test: Kill any running DayZDiag_x64.exe processes.

Counterpart to /dayz-launch-test. Force-kills the diag server and/or client by
image name. Does NOT gate on /dayz-preflight — this skill is the documented
exception (per L2 conventions): stop is an emergency escape that must work
even when the environment is half-broken.

See SKILL.md for full usage.
"""
from __future__ import annotations

import subprocess
import sys

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "

IMAGE_NAME = "DayZDiag_x64.exe"


def main() -> int:
    # taskkill /IM <image> /F — force-terminate all matching processes
    result = subprocess.run(
        ["taskkill", "/IM", IMAGE_NAME, "/F"],
        capture_output=True,
        text=True,
    )

    # taskkill prints "SUCCESS: ..." per process to stdout, or
    # "ERROR: The process \"<image>\" not found." to stderr (rc 128).
    if result.returncode == 0:
        # Count how many SUCCESS lines we got — taskkill emits one per kill.
        killed = sum(1 for line in result.stdout.splitlines() if line.startswith("SUCCESS:"))
        word = "process" if killed == 1 else "processes"
        print(f"{OK} Stopped {killed} {IMAGE_NAME} {word}.")
        return 0

    # rc 128 specifically means "no matching process" — that's not an error
    # for our purposes (the desired end state — no diag running — is reached).
    if "not found" in (result.stderr or "").lower():
        print(f"{OK} No {IMAGE_NAME} processes running.")
        return 0

    # Anything else is a real failure (permission denied, taskkill missing, etc.)
    print(f"{FAIL} taskkill failed (rc={result.returncode}):", file=sys.stderr)
    if result.stdout.strip():
        print(result.stdout, file=sys.stderr)
    if result.stderr.strip():
        print(result.stderr, file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
