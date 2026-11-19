"""Tests for pack_skill.py: the .skill packer that reads SKILL.md as UTF-8 and writes forward-slash zip entries."""
import importlib.util
import zipfile
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location("pack_skill", Path(__file__).with_name("pack_skill.py"))
pack_skill = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pack_skill)


def _make_skill(root: Path, frontmatter: str) -> Path:
    skill = root / "demo-skill"
    (skill / "references").mkdir(parents=True)
    (skill / "__pycache__").mkdir()
    # An em-dash and an arrow: the characters that broke the cp1252 reader this script replaces.
    (skill / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n\n# Demo — a → b\n", encoding="utf-8")
    (skill / "references" / "notes.md").write_text("notes\n", encoding="utf-8")
    (skill / "__pycache__" / "x.cpython-312.pyc").write_bytes(b"\x00")
    (skill / "helper.pyc").write_bytes(b"\x00")
    return skill


def test_pack_writes_the_whole_folder_with_forward_slash_entries(tmp_path, capsys):
    skill = _make_skill(tmp_path, "name: demo-skill\ndescription: Packs a demo skill.")
    out = pack_skill.pack(skill, tmp_path / "out")
    assert out == tmp_path / "out" / "demo-skill.skill"
    with zipfile.ZipFile(out) as zf:
        names = sorted(zf.namelist())
        assert names == ["demo-skill/SKILL.md", "demo-skill/references/notes.md"]
        assert "—" in zf.read("demo-skill/SKILL.md").decode("utf-8")
    assert "OK " in capsys.readouterr().out


def test_folded_description_is_joined_before_the_length_check():
    fm = "name: x\ndescription: >\n  first line\n  second line\nargument-hint: <mod>"
    assert pack_skill.folded_description(fm) == "first line second line"


@pytest.mark.parametrize(
    "frontmatter, message",
    [
        ("description: no name here", "no 'name'"),
        ("name: demo-skill", "no 'description'"),
        ("name: demo-skill\ndescription: " + "x" * 1025, "cap is 1024"),
    ],
)
def test_validate_rejects_bad_frontmatter(tmp_path, frontmatter, message):
    skill = _make_skill(tmp_path, frontmatter)
    with pytest.raises(SystemExit) as err:
        pack_skill.validate(skill)
    assert message in str(err.value)


def test_validate_needs_frontmatter_at_the_top(tmp_path):
    skill = tmp_path / "bare"
    skill.mkdir()
    (skill / "SKILL.md").write_text("# no frontmatter\n", encoding="utf-8")
    with pytest.raises(SystemExit) as err:
        pack_skill.validate(skill)
    assert "must start with YAML frontmatter" in str(err.value)


def test_default_output_folder_is_under_output():
    assert pack_skill.DEFAULT_OUT_DIR == pack_skill.REPO / "output" / "skill-packages"
    assert (pack_skill.REPO / "scripts" / "dev" / "pack_skill.py").is_file()
