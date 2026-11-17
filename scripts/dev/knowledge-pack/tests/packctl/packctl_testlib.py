from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

# The folder that holds the packctl package.
TOOLING_ROOT = Path(__file__).resolve().parents[2]
# The Agentic-Z repository root.
REPO_ROOT = TOOLING_ROOT.parents[2]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


@pytest.fixture
def repo_factory(tmp_path: Path):
    """Build a small git repository under tmp_path and return its root."""

    def factory(
        files: dict[str, str] | None = None,
        *,
        initialize_git: bool = True,
    ) -> Path:
        root = tmp_path / "repo"
        root.mkdir()
        initial = {
            "LICENSE": "Fixture license\n",
            "README.md": "# Fixture\n",
        }
        initial.update(files or {})
        for relative, content in initial.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")

        if initialize_git:
            run_git(root, "init", "-q")
            run_git(root, "config", "user.email", "fixture@example.invalid")
            run_git(root, "config", "user.name", "Fixture")
            run_git(root, "add", ".")
            run_git(root, "commit", "-qm", "fixture")
        return root

    return factory
