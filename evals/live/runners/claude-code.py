from __future__ import annotations

"""Reference adapter from the live-eval runner contract to Claude Code.

Set PACKCTL_LIVE_EVAL_MODEL and PACKCTL_LIVE_EVAL_EFFORT before invoking it.
The adapter deliberately has no defaults: every live result must record the
model and effort that produced it.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


_EFFORT_LEVELS = {"low", "medium", "high", "xhigh", "max"}
_INPUT_FIELDS = {"prompt", "workspace", "skill_mounted", "run_index"}


def _claude_command(
    executable: str,
    *,
    model: str,
    effort: str,
    prompt: str,
) -> list[str]:
    return [
        executable,
        "-p",
        prompt,
        "--bare",
        "--model",
        model,
        "--effort",
        effort,
        "--settings",
        "{}",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--output-format",
        "json",
    ]


def _validate_input(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != _INPUT_FIELDS:
        raise ValueError("invalid runner input fields")
    if not isinstance(value["prompt"], str) or not value["prompt"].strip():
        raise ValueError("prompt must be non-empty text")
    if not isinstance(value["workspace"], str) or not value["workspace"]:
        raise ValueError("workspace must be text")
    if not isinstance(value["skill_mounted"], bool):
        raise ValueError("skill_mounted must be boolean")
    if (
        isinstance(value["run_index"], bool)
        or not isinstance(value["run_index"], int)
        or value["run_index"] < 0
    ):
        raise ValueError("run_index must be a non-negative integer")
    return value


def _answer_from_result(value: object) -> str:
    if not isinstance(value, dict) or not isinstance(value.get("result"), str):
        raise ValueError("Claude Code JSON output lacks a text result")
    return value["result"]


def main() -> int:
    try:
        payload = _validate_input(json.load(sys.stdin))
        model = os.environ.get("PACKCTL_LIVE_EVAL_MODEL", "").strip()
        effort = os.environ.get("PACKCTL_LIVE_EVAL_EFFORT", "").strip()
        if not model:
            raise ValueError("PACKCTL_LIVE_EVAL_MODEL is required")
        if effort not in _EFFORT_LEVELS:
            raise ValueError(
                "PACKCTL_LIVE_EVAL_EFFORT must be low, medium, high, xhigh, or max"
            )
        workspace = Path(str(payload["workspace"])).resolve()
        if not workspace.is_dir():
            raise ValueError("workspace does not exist")
        command = _claude_command(
            "claude",
            model=model,
            effort=effort,
            prompt=str(payload["prompt"]),
        )
        completed = subprocess.run(
            command,
            cwd=workspace,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"Claude Code exited with {completed.returncode}")
        claude_result = json.loads(completed.stdout)
        output = {
            "answer": _answer_from_result(claude_result),
            "model": model,
            "meta": {
                "effort": effort,
                "claude_result": claude_result,
            },
        }
        sys.stdout.write(json.dumps(output, ensure_ascii=False, sort_keys=True) + "\n")
        return 0
    except (OSError, UnicodeError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        sys.stderr.write(f"claude-code adapter error: {type(error).__name__}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
