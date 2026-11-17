"""Checks for the task-observer skill: frontmatter, the reference table against the files in
references/, and the shell snippets the skill tells the agent to run (frontmatter scan and id
assignment), which are run as written against a throwaway log. The snippet tests skip when no
working bash is on PATH.

Run with: py -m pytest skills/task-observer
"""
from __future__ import annotations

import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent
SKILL = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
REFERENCES = sorted((SKILL_DIR / "references").glob("*.md"))
LOG = Path("skill-observations") / "observation-log"


def _frontmatter() -> dict[str, str]:
    block = SKILL.split("---", 2)[1]
    out = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            out[key.strip()] = value.strip().strip('"')
    return out


def test_frontmatter_names_the_folder_and_describes_the_skill():
    front = _frontmatter()
    assert front["name"] == SKILL_DIR.name
    # The skill's own delivery gate (references/skill-authoring.md) caps a description at 1024 characters.
    assert 0 < len(front["description"].replace('\\"', '"')) <= 1024


def test_skill_has_the_path_note():
    assert "<!-- skill-dir-note -->" in SKILL


def test_every_reference_the_skill_names_exists():
    named = set(re.findall(r"`references/([\w.-]+\.md)`", SKILL))
    assert named, "SKILL.md must name its reference files"
    missing = sorted(name for name in named if not (SKILL_DIR / "references" / name).is_file())
    assert not missing, f"SKILL.md names missing reference files: {missing}"


def test_every_reference_file_is_in_the_reference_table():
    table = SKILL.split("## Reference files", 1)[1].split("\n## ", 1)[0]
    listed = set(re.findall(r"`references/([\w.-]+\.md)`", table))
    unlisted = sorted(p.name for p in REFERENCES if p.name not in listed)
    assert not unlisted, f"reference files missing from the table in SKILL.md: {unlisted}"


def test_each_reference_file_opens_with_a_title_and_what_it_covers():
    for path in REFERENCES:
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[0].startswith("# "), f"{path.name} must open with a title"
        assert lines[1] == "" and lines[2].strip(), f"{path.name} must say what it covers under the title"


def test_scripts_the_bundle_does_not_ship_are_not_called_by_path():
    # migrate-log.py and validate-skill-bundle.py are named as upstream helpers; nothing may tell the
    # agent to run them from a scripts/ folder this skill does not have.
    for path in [SKILL_DIR / "SKILL.md", *REFERENCES]:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"scripts/[\w-]+\.py", text), f"{path.name} calls a script that is not bundled"


# --- the shell snippets, run as written -----------------------------------------------------------

def _bash() -> str | None:
    exe = shutil.which("bash")
    if not exe:
        return None
    try:
        probe = subprocess.run([exe, "-c", "echo ok"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return exe if probe.returncode == 0 and probe.stdout.strip() == "ok" else None


BASH = _bash()
needs_bash = pytest.mark.skipif(BASH is None, reason="no working bash on PATH")


def _snippet(source: Path, first_words: str, must_contain: str) -> str:
    """The first ```bash block in source that starts with first_words and holds must_contain."""
    for body in re.findall(r"^[ ]*```bash\n(.*?)^[ ]*```", source.read_text(encoding="utf-8"), re.S | re.M):
        body = textwrap.dedent(body)
        if body.startswith(first_words) and must_contain in body:
            return body
    raise AssertionError(f"no bash snippet with {must_contain!r} in {source.name}")


SCAN_SOURCES = [SKILL_DIR / "SKILL.md", SKILL_DIR / "references" / "observation-log.md"]


def _run(snippet: str, cwd: Path) -> subprocess.CompletedProcess:
    script = cwd / "snippet.sh"
    script.write_bytes(snippet.encode("utf-8"))
    return subprocess.run([BASH, "snippet.sh"], cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=60)


def _observation(folder: Path, name: str, header: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(f"---\n{header}\n---\n\n**Issue:** x\n".encode("utf-8"))


@needs_bash
@pytest.mark.parametrize("source", SCAN_SOURCES, ids=lambda p: p.name)
def test_scan_prints_the_frontmatter_and_exits_zero_on_a_healthy_log(source, tmp_path):
    _observation(tmp_path / LOG, "0001-first.md", "id: 1\ntitle: First\nstatus: open")
    result = _run(_snippet(source, "d=skill-observations/observation-log", "parsed=0"), tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "title: First" in result.stdout
    assert "**Issue:**" not in result.stdout, "the scan must read the frontmatter only"


@needs_bash
@pytest.mark.parametrize("source", SCAN_SOURCES, ids=lambda p: p.name)
def test_scan_exits_zero_when_there_is_no_log_yet(source, tmp_path):
    result = _run(_snippet(source, "d=skill-observations/observation-log", "parsed=0"), tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


@needs_bash
@pytest.mark.parametrize("source", SCAN_SOURCES, ids=lambda p: p.name)
def test_scan_fails_loudly_when_files_exist_but_no_header_parses(source, tmp_path):
    (tmp_path / LOG).mkdir(parents=True)
    (tmp_path / LOG / "0001-first.md").write_bytes(b"no frontmatter here\n")
    result = _run(_snippet(source, "d=skill-observations/observation-log", "parsed=0"), tmp_path)
    assert result.returncode == 1
    assert "SCAN COMMAND BROKEN" in result.stdout


@needs_bash
@pytest.mark.parametrize("source", SCAN_SOURCES, ids=lambda p: p.name)
def test_next_id_is_one_above_the_active_files_the_archive_and_the_floor(source, tmp_path):
    snippet = _snippet(source, "d=skill-observations/observation-log", ".id-floor")
    _observation(tmp_path / LOG, "0001-first.md", "id: 1\nstatus: open")
    _observation(tmp_path / LOG / "archive", "0007-seventh.md", "id: 7\nstatus: actioned")
    floor = tmp_path / LOG / "archive" / ".id-floor"

    assert _run(snippet, tmp_path).returncode == 0
    assert floor.read_text(encoding="utf-8").strip() == "8"

    # With every file gone the counter still never drops below the floor.
    (tmp_path / LOG / "0001-first.md").unlink()
    (tmp_path / LOG / "archive" / "0007-seventh.md").unlink()
    assert _run(snippet, tmp_path).returncode == 0
    assert floor.read_text(encoding="utf-8").strip() == "9"


@needs_bash
@pytest.mark.parametrize("source", SCAN_SOURCES, ids=lambda p: p.name)
def test_next_id_refuses_a_non_empty_log_with_no_ids(source, tmp_path):
    (tmp_path / LOG / "archive").mkdir(parents=True)
    (tmp_path / LOG / "note.md").write_bytes(b"---\nstatus: open\n---\n")
    result = _run(_snippet(source, "d=skill-observations/observation-log", ".id-floor"), tmp_path)
    assert result.returncode == 1
    assert "ID COMMAND BROKEN" in result.stdout
    assert not (tmp_path / LOG / "archive" / ".id-floor").exists()
