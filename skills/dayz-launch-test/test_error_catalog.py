"""Static checks for the recurring error catalog (references/error-catalog.md) and the
files that cite its E numbers: the catalog holds E01 to E35 once each, every E number
those files name is in it, and they are English with no machine-specific paths.

Run with: py -m pytest skills/dayz-launch-test/test_error_catalog.py
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parent.parent
CATALOG = SKILLS_DIR / "dayz-launch-test" / "references" / "error-catalog.md"
EXPECTED = {f"E{n:02d}" for n in range(1, 36)}
CITING = [
    CATALOG,
    SKILLS_DIR / "dayz-launch-test" / "references" / "debug-protocol.md",
    SKILLS_DIR / "dayz-launch-test" / "references" / "test-loop.md",
    SKILLS_DIR / "dayz-launch-test" / "references" / "audit-escalation.md",
    SKILLS_DIR / "dayz-build-pbo" / "references" / "file-checklists.md",
    SKILLS_DIR / "dayz-scope-mod" / "references" / "implementation-protocol.md",
    SKILLS_DIR / "dayz-scope-mod" / "references" / "pre-implementation-grill.md",
]
SPANISH_RE = re.compile(r"\b(?:Úsala|cuando|según|Ejes|Plantilla|Reglas|Referencia cruzada|Mantenimiento|Caso real)\b")
MACHINE_PATH_RE = re.compile(r"[A-Za-z]:\\Users\\|/home/\w+|<vault>|<claude-home>")


def test_catalog_holds_each_error_once():
    rows = re.findall(r"^\| (E\d\d) \|", CATALOG.read_text(encoding="utf-8"), re.MULTILINE)
    assert len(rows) == len(set(rows)), "an error id appears in more than one catalog row"
    assert set(rows) == EXPECTED


@pytest.mark.parametrize("path", CITING, ids=lambda p: p.name)
def test_cited_errors_are_catalogued(path):
    used = {f"E{n}" for n in re.findall(r"\bE(\d\d)\b", path.read_text(encoding="utf-8"))}
    assert not sorted(used - EXPECTED), f"{path.name} names errors missing from the catalog"


@pytest.mark.parametrize("path", CITING, ids=lambda p: p.name)
def test_files_are_english_and_have_no_machine_paths(path):
    text = path.read_text(encoding="utf-8")
    assert not SPANISH_RE.search(text), f"{path.name} still holds Spanish text"
    assert not MACHINE_PATH_RE.search(text), f"{path.name} holds a machine-specific path"
