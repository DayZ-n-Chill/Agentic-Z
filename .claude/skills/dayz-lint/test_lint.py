"""Tests for lint.py: one fixture mod per rule, built in tmp_path from a clean mod. No DayZ, no real P:\\."""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_lint_under_test", HERE / "lint.py")
lint = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lint)

CLEAN_CONFIG = """class CfgPatches
{
    class MyMod
    {
        units[] = {"MyMod_Vest"};
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = {"DZ_Data", "DZ_Scripts"};
    };
};
class CfgMods
{
    class MyMod
    {
        type = "mod";
        dependencies[] = {"Game", "World", "Mission"};
        class defs
        {
            class gameScriptModule { value = ""; files[] = {"MyMod/scripts/3_Game"}; };
            class worldScriptModule { value = ""; files[] = {"MyMod/scripts/4_World"}; };
            class missionScriptModule { value = ""; files[] = {"MyMod/scripts/5_Mission"}; };
        };
    };
};
class CfgVehicles
{
    class Vest_Base;
    class MyMod_Vest: Vest_Base
    {
        model = "\\MyMod\\data\\vest.p3d";
        picture = "\\dz\\gear\\vests\\data\\icon.paa";
        hiddenSelections[] = {"camo"};
        hiddenSelectionsTextures[] = {"MyMod\\data\\vest_co.paa"};
        hiddenSelectionsMaterials[] = {"MyMod\\data\\vest.rvmat"};
    };
};
"""
CLEAN_RVMAT = 'class Stage1\n{\n\ttexture = "MyMod\\data\\vest_nohq.paa";\n\tuvSource = "tex";\n};\n'


@pytest.fixture
def p_drive(tmp_path, monkeypatch):
    """A fake P:\\ with vanilla CfgPatches classes and a valid MyMod link."""
    drive = tmp_path / "P"
    (drive / "DZ" / "data").mkdir(parents=True)
    (drive / "DZ" / "data" / "config.cpp").write_text(
        "class CfgPatches { class DZ_Data { units[] = {}; }; class DZ_Data_Bliss { units[] = {}; }; };", encoding="utf-8")
    (drive / "scripts").mkdir()
    (drive / "scripts" / "config.cpp").write_text("class CfgPatches { class DZ_Scripts { units[] = {}; }; };", encoding="utf-8")
    (drive / "MyMod").mkdir()
    return drive


@pytest.fixture
def mod(tmp_path, p_drive, monkeypatch) -> Path:
    """workspace/MyMod/: a clean mod that passes every rule."""
    root = tmp_path / "proj" / "workspace" / "MyMod"
    for sub in ("scripts/3_Game", "scripts/4_World", "scripts/5_Mission", "data"):
        (root / sub).mkdir(parents=True)
        (root / sub / ".gitkeep").write_text("", encoding="utf-8")
    (root / "config.cpp").write_text(CLEAN_CONFIG, encoding="utf-8")
    (root / "$PBOPREFIX$").write_text("MyMod\n", encoding="utf-8")
    (root / "scripts" / "4_World" / "vest.c").write_text("modded class PlayerBase\n{\n}\nclass MyModHelper {}\n", encoding="utf-8")
    for name in ("vest.p3d", "vest_co.paa", "vest_nohq.paa"):
        (root / "data" / name).write_bytes(b"x")
    (root / "data" / "vest.rvmat").write_text(CLEAN_RVMAT, encoding="utf-8")
    monkeypatch.setattr(lint.h, "link_target", lambda p: root if p == p_drive / "MyMod" else None)
    return root


def run(mod: Path, p_drive: Path) -> dict:
    return lint.lint_mod("MyMod", mod, mod.parents[1], p_drive=p_drive)


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new), encoding="utf-8")


def cfg_edit(old: str, new: str) -> Callable[[Path], None]:
    return lambda m: edit(m / "config.cpp", old, new)


def test_clean_mod_passes(mod, p_drive):
    report = run(mod, p_drive)
    assert report["findings"] == []
    assert (report["verdict"], report["errors"], report["warnings"]) == ("PASS", 0, 0)


def write(rel: str, text: str) -> Callable[[Path], None]:
    def go(m: Path) -> None:
        (m / rel).parent.mkdir(parents=True, exist_ok=True)
        (m / rel).write_text(text, encoding="utf-8")
    return go


def remove(rel: str) -> Callable[[Path], None]:
    return lambda m: (m / rel).unlink()


# (rule, severity, change to the clean mod, file, line or None)
CASES = [
    ("config-missing", "error", remove("config.cpp"), "workspace/MyMod/config.cpp", None),
    ("config-syntax", "error", cfg_edit('weapons[] = {};', 'weapons[] = {}'), "workspace/MyMod/config.cpp", 6),
    ("config-syntax", "error", cfg_edit("        };\n    };\n};\nclass CfgVehicles", "        };\n    };\nclass CfgVehicles"),
     "workspace/MyMod/config.cpp", 11),
    ("cfgpatches-missing", "error", cfg_edit("class CfgPatches", "class CfgPatchez"), "workspace/MyMod/config.cpp", None),
    ("cfgpatches-empty", "error",
     cfg_edit('    class MyMod\n    {\n        units[] = {"MyMod_Vest"};\n        weapons[] = {};\n        requiredVersion = 0.1;\n'
              '        requiredAddons[] = {"DZ_Data", "DZ_Scripts"};\n    };\n', ""),
     "workspace/MyMod/config.cpp", 1),
    ("cfgpatches-field-missing", "warning", cfg_edit('        units[] = {"MyMod_Vest"};\n', ""), "workspace/MyMod/config.cpp", 3),
    ("cfgpatches-field", "error", cfg_edit("weapons[] = {};", 'weapons = "";'), "workspace/MyMod/config.cpp", 6),
    ("cfgpatches-field-missing", "warning", cfg_edit('        weapons[] = {};\n', ""), "workspace/MyMod/config.cpp", 3),
    ("required-addons-missing", "error", cfg_edit('        requiredAddons[] = {"DZ_Data", "DZ_Scripts"};\n', ""), "workspace/MyMod/config.cpp", 3),
    ("required-addon-name", "error", cfg_edit('"DZ_Scripts"', '"@CF"'), "workspace/MyMod/config.cpp", 8),
    ("required-addon-name", "error", cfg_edit('"DZ_Scripts"', '"DZ\\gear\\vests"'), "workspace/MyMod/config.cpp", 8),
    ("required-addon-name", "error", cfg_edit('"DZ_Scripts"', '"MyMod"'), "workspace/MyMod/config.cpp", 8),
    ("required-addon-name", "error", cfg_edit('"DZ_Scripts"', '"DZ_Dta"'), "workspace/MyMod/config.cpp", 8),
    ("required-addon-duplicate", "warning", cfg_edit('"DZ_Scripts"', '"dz_data"'), "workspace/MyMod/config.cpp", 8),
    ("pboprefix-missing", "error", remove("$PBOPREFIX$"), "workspace/MyMod/$PBOPREFIX$", None),
    ("pboprefix-mismatch", "error", write("$PBOPREFIX$", "mymod\\data"), "workspace/MyMod/$PBOPREFIX$", 1),
    # What Windows PowerShell 5.1 writes for `echo MyMod > $PBOPREFIX$`: UTF-16 with a byte-order mark.
    ("pboprefix-encoding", "error", lambda m: (m / "$PBOPREFIX$").write_bytes("MyMod\r\n".encode("utf-16")),
     "workspace/MyMod/$PBOPREFIX$", 1),
    ("pboprefix-encoding", "error", lambda m: (m / "$PBOPREFIX$").write_bytes(b"MyM\xf6d\r\n"), "workspace/MyMod/$PBOPREFIX$", 1),
    ("script-module-path", "error", cfg_edit('"MyMod/scripts/5_Mission"', '"OtherMod/scripts/5_Mission"'), "workspace/MyMod/config.cpp", 21),
    ("script-module-path", "error", cfg_edit('"MyMod/scripts/5_Mission"', '"MyMod/scripts/5_Misson"'), "workspace/MyMod/config.cpp", 21),
    ("script-module-layer", "error", cfg_edit('{"MyMod/scripts/3_Game"}', '{"MyMod/scripts/4_World"}'), "workspace/MyMod/config.cpp", 19),
    ("script-module-unlisted", "warning", cfg_edit('            class worldScriptModule { value = ""; files[] = {"MyMod/scripts/4_World"}; };\n', ""),
     "workspace/MyMod/config.cpp", 11),
    ("modded-class-extends", "error", write("scripts/4_World/vest.c", "class A {}\nmodded class PlayerBase extends PlayerBase\n{\n}\n"),
     "workspace/MyMod/scripts/4_World/vest.c", 2),
    ("modded-class-extends", "error", write("scripts/4_World/vest.c", "modded class PlayerBase: PlayerBase {}\n"),
     "workspace/MyMod/scripts/4_World/vest.c", 1),
    ("modded-class-extends", "error", write("scripts/4_World/vest.c", "class A {}\nmodded class PlayerBase\n\textends ManBase\n{\n}\n"),
     "workspace/MyMod/scripts/4_World/vest.c", 2),
    ("modded-class-extends", "error", write("scripts/4_World/vest.c", "modded class PlayerBase /* base */\n: ManBase\n{\n}\n"),
     "workspace/MyMod/scripts/4_World/vest.c", 1),
    ("script-suffix", "warning", write("scripts/4_World/helper.c.txt", "class X {}\n"), "workspace/MyMod/scripts/4_World/helper.c.txt", None),
    ("missing-model", "error", remove("data/vest.p3d"), "workspace/MyMod/config.cpp", 30),
    ("missing-texture", "error", remove("data/vest_co.paa"), "workspace/MyMod/config.cpp", 33),
    ("missing-texture", "error", remove("data/vest.rvmat"), "workspace/MyMod/config.cpp", 34),
    ("missing-texture", "error", remove("data/vest_nohq.paa"), "workspace/MyMod/data/vest.rvmat", 3),
    ("missing-file", "error", cfg_edit('hiddenSelections[] = {"camo"};', 'hiddenSelections[] = {"camo"};\n        ui = "MyMod\\gui\\vest.layout";'),
     "workspace/MyMod/config.cpp", 33),
    ("absolute-path", "error", cfg_edit('"\\MyMod\\data\\vest.p3d"', '"P:\\MyMod\\data\\vest.p3d"'), "workspace/MyMod/config.cpp", 30),
    ("absolute-path", "error", cfg_edit('"\\MyMod\\data\\vest.p3d"', '"workspace\\MyMod\\data\\vest.p3d"'), "workspace/MyMod/config.cpp", 30),
    ("texture-format", "error", cfg_edit('"MyMod\\data\\vest_co.paa"', '"MyMod\\data\\vest_co.png"'), "workspace/MyMod/config.cpp", 33),
    ("texture-suffix", "warning", lambda m: (cfg_edit("vest_co.paa", "vest.paa")(m), (m / "data" / "vest.paa").write_bytes(b"x")),
     "workspace/MyMod/config.cpp", 33),
    ("rvmat-syntax", "error", write("data/vest.rvmat", 'class Stage1 { texture = "MyMod\\data\\vest_nohq.paa; };\n'),
     "workspace/MyMod/data/vest.rvmat", 1),
]


@pytest.mark.parametrize("rule,severity,change,file,line", CASES, ids=[f"{c[0]}-{i}" for i, c in enumerate(CASES)])
def test_each_rule_fires_on_its_fixture(mod, p_drive, rule, severity, change, file, line):
    change(mod)
    report = run(mod, p_drive)
    hits = [f for f in report["findings"] if f["rule"] == rule]
    assert hits, report["findings"]
    f = hits[0]
    assert (f["severity"], f["file"], f["line"]) == (severity, file, line), f
    assert f["text"] == f"[lint:{rule}] {f['message']}"
    assert f["triage"]["status"] == "known" and f["triage"]["id"] == f"lint-{rule}"
    assert report["verdict"] == ("FAIL" if severity == "error" else "PASS")


def test_every_rule_has_a_fixture_and_a_catalog_entry():
    assert {c[0] for c in CASES} | {"p-link", "p-not-mounted"} == set(lint.RULES)
    known = {e["id"]: e for e in json.loads(lint.triage.KNOWN_ERRORS.read_text(encoding="utf-8"))}
    for rule in lint.RULES:
        entry = known[f"lint-{rule}"]
        assert entry["scope"] == "lint"
        assert re.search(entry["pattern"], f"[lint:{rule}] message")


@pytest.mark.parametrize("source", [
    "// modded class Foo extends Foo\nmodded class PlayerBase\n{\n}\n",
    "/* modded class Foo extends Foo\nmodded class Bar extends Bar */\nmodded class PlayerBase\n{\n}\n",
    "modded class PlayerBase // modded class Foo extends Foo\n{\n}\n",
])
def test_commented_out_modded_extends_is_not_reported(mod, p_drive, source):
    (mod / "scripts" / "4_World" / "vest.c").write_text(source, encoding="utf-8")
    report = run(mod, p_drive)
    assert report["findings"] == [] and report["verdict"] == "PASS"


def test_modded_extends_after_a_block_comment_keeps_its_line_number(mod, p_drive):
    (mod / "scripts" / "4_World" / "vest.c").write_text("/* one\ntwo\n*/\nmodded class PlayerBase extends PlayerBase {}\n", encoding="utf-8")
    [f] = run(mod, p_drive)["findings"]
    assert (f["rule"], f["line"]) == ("modded-class-extends", 4)


def test_modded_extends_on_the_next_line_names_the_whole_clause(mod, p_drive):
    (mod / "scripts" / "4_World" / "vest.c").write_text("modded class PlayerBase\nextends ManBase\n{\n}\n", encoding="utf-8")
    [f] = run(mod, p_drive)["findings"]
    assert (f["rule"], f["line"]) == ("modded-class-extends", 1)
    assert f["message"].startswith("modded class PlayerBase extends ManBase: ")


def test_extends_on_a_later_plain_class_is_not_a_modded_extends(mod, p_drive):
    (mod / "scripts" / "4_World" / "vest.c").write_text(
        "modded class PlayerBase\n{\n}\nclass MyModVest extends Clothing\n{\n}\nmodded class Extendsable\n{\n}\n", encoding="utf-8")
    assert run(mod, p_drive)["findings"] == []


@pytest.mark.parametrize("source", [
    # A "/*" in one string and a "*/" in a later one are not a comment between them.
    'string a = "MyMod/scripts/*";\nmodded class PlayerBase extends PlayerBase {}\nstring b = "*/";\n',
    # An escaped quote does not end the string, so the "/*" after it is still inside it.
    'string a = "say \\"/*";\nmodded class PlayerBase extends PlayerBase {}\nstring b = "*/";\n',
    # A "//" in a string is not a line comment.
    'string a = "http://x"; string c = "/*";\nmodded class PlayerBase extends PlayerBase {}\nstring b = "*/";\n',
])
def test_comment_markers_inside_strings_do_not_hide_a_modded_extends(mod, p_drive, source):
    (mod / "scripts" / "4_World" / "vest.c").write_text(source, encoding="utf-8")
    [f] = run(mod, p_drive)["findings"]
    assert (f["rule"], f["line"]) == ("modded-class-extends", 2)


def test_strip_comments_keeps_strings_and_line_numbers():
    text = 'a = "x//y"; // gone\nb = "/*"; /* gone\nstill gone */ c = "*/";\n'
    assert lint.strip_comments(text, backslash_escapes=True) == 'a = "x//y"; \nb = "/*"; \n c = "*/";\n'


def test_patch_names_ignores_comment_markers_inside_config_strings():
    # Config strings have no backslash escapes: "dir\" ends at its second quote.
    text = ('class CfgPatches { class A { x[] = {"a/*"}; }; class B { y[] = {"*/"}; };\n'
            'class C { p = "dir\\"; /* class Fake {}; */ }; };')
    assert lint.patch_names(text) == {"a", "b", "c"}


def test_utf16_prefix_still_runs_every_other_check_and_says_how_to_fix(mod, p_drive, monkeypatch, capsys):
    (mod / "$PBOPREFIX$").write_bytes("MyMod\r\n".encode("utf-16"))
    (mod / "data" / "vest.p3d").unlink()
    report = run(mod, p_drive)
    rules = {f["rule"] for f in report["findings"]}
    assert rules == {"pboprefix-encoding", "missing-model"}, report["findings"]
    [f] = [f for f in report["findings"] if f["rule"] == "pboprefix-encoding"]
    assert f["message"].startswith("$PBOPREFIX$ is UTF-16 text")
    assert "plain ASCII or UTF-8" in f["triage"]["fix"] and "workspace/MyMod/$PBOPREFIX$" in f["triage"]["fix"]
    monkeypatch.setattr(lint, "P_DRIVE", p_drive)
    assert lint.main(["--mod-dir", str(mod)]) == 1  # a FAIL verdict, not the old exit-2 crash
    assert capsys.readouterr().out.splitlines()[0] == "FAIL"


def test_lint_entries_never_match_log_lines():
    known = lint.triage.load_known()
    for line in ("[FAIL] workspace\\MyMod\\$PBOPREFIX$ is 'Other', expected 'MyMod'.", "SCRIPT    (E): NULL pointer to instance"):
        assert not lint.triage.match_line(line, known)["id"].startswith("lint-")


def test_triage_fills_mod_name_into_fix(mod, p_drive):
    (mod / "$PBOPREFIX$").unlink()
    [f] = run(mod, p_drive)["findings"]
    assert f["triage"]["owner_agent"] == "dayz-orchestrator"
    assert "/dayz-add-scaffold MyMod" in f["triage"]["fix"]


# --- the P:\ link --------------------------------------------------------------

def test_link_missing_is_an_error(mod, p_drive):
    (p_drive / "MyMod").rmdir()
    [f] = run(mod, p_drive)["findings"]
    assert (f["rule"], f["severity"]) == ("p-link", "error")
    assert f["triage"]["fix"] == "Run /dayz-add-scaffold MyMod --piece junction."


def test_link_fix_outside_workspace_points_at_import_not_add_scaffold(mod, tmp_path, p_drive, monkeypatch, capsys):
    # /dayz-add-scaffold --piece junction only works on workspace\<Mod>\, so it must not be the hint here.
    outside = tmp_path / "repos" / "MyMod"
    shutil.copytree(mod, outside)
    (p_drive / "MyMod").rmdir()
    monkeypatch.setattr(lint, "P_DRIVE", p_drive)
    monkeypatch.setattr(lint, "cached_workspace", lambda: tmp_path / "proj" / "workspace")
    assert lint.main(["--mod-dir", str(outside), "--json"]) == 1
    data = json.loads(capsys.readouterr().out.partition("\n")[2])
    [fix] = [f["triage"]["fix"] for f in data["findings"] if f["rule"] == "p-link"]
    assert "/dayz-add-scaffold" not in fix
    assert f'/dayz-import-mod --source "{outside}"' in fix
    assert f'mklink /J "{p_drive / "MyMod"}" "{outside}"' in fix


def test_link_fix_for_workspace_mod_via_mod_dir_keeps_add_scaffold(mod, p_drive, monkeypatch, capsys):
    (p_drive / "MyMod").rmdir()
    monkeypatch.setattr(lint, "P_DRIVE", p_drive)
    monkeypatch.setattr(lint, "cached_workspace", lambda: mod.parent)
    assert lint.main(["--mod-dir", str(mod), "--json"]) == 1
    data = json.loads(capsys.readouterr().out.partition("\n")[2])
    [f] = data["findings"]
    assert f["triage"]["fix"] == "Run /dayz-add-scaffold MyMod --piece junction."


def test_script_module_path_fix_names_the_linted_folder(mod, p_drive):
    edit(mod / "config.cpp", '"MyMod/scripts/5_Mission"', '"MyMod/scripts/5_Misson"')
    [f] = [f for f in run(mod, p_drive)["findings"] if f["rule"] == "script-module-path"]
    assert f["triage"]["fix"].endswith("make sure that folder exists under workspace/MyMod/.")


def test_script_module_path_fix_outside_workspace_names_the_mod_dir(mod, tmp_path, p_drive, monkeypatch, capsys):
    # A --mod-dir folder outside workspace\ must not be told to fix workspace/<Mod>/.
    outside = tmp_path / "repos" / "MyMod"
    shutil.copytree(mod, outside)
    edit(outside / "config.cpp", '"MyMod/scripts/5_Mission"', '"MyMod/scripts/5_Misson"')
    monkeypatch.setattr(lint, "P_DRIVE", p_drive)
    monkeypatch.setattr(lint, "cached_workspace", lambda: tmp_path / "proj" / "workspace")
    monkeypatch.chdir(tmp_path)
    assert lint.main(["--mod-dir", str(outside), "--json"]) == 1
    data = json.loads(capsys.readouterr().out.partition("\n")[2])
    [fix] = [f["triage"]["fix"] for f in data["findings"] if f["rule"] == "script-module-path"]
    assert "workspace/" not in fix
    assert fix == "Point files[] at MyMod/scripts/<layer> and make sure that folder exists under repos/MyMod/."


def test_no_cached_project_means_not_a_workspace_mod(mod, monkeypatch):
    monkeypatch.setattr(lint, "cached_workspace", lambda: None)
    assert not lint.is_workspace_mod(mod, "MyMod")


def test_link_that_is_a_real_folder_is_an_error(mod, p_drive, monkeypatch):
    monkeypatch.setattr(lint.h, "link_target", lambda p: None)
    [f] = run(mod, p_drive)["findings"]
    assert f["rule"] == "p-link" and "real folder" in f["message"]


def test_link_pointing_elsewhere_is_an_error(mod, p_drive, monkeypatch, tmp_path):
    monkeypatch.setattr(lint.h, "link_target", lambda p: tmp_path / "elsewhere")
    [f] = run(mod, p_drive)["findings"]
    assert f["rule"] == "p-link" and "points at" in f["message"]


def _junction(link: Path, target: Path) -> None:
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)


def test_imported_mod_linted_by_mod_dir_through_real_junctions_passes(mod, tmp_path, p_drive, monkeypatch, capsys):
    # /dayz-import-mod layout: workspace\MyMod is a junction to the outside source, and
    # P:\MyMod is a junction to workspace\MyMod. --mod-dir resolves to the source folder.
    source = tmp_path / "repos" / "MyMod"
    shutil.copytree(mod, source)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _junction(workspace / "MyMod", source)
    (p_drive / "MyMod").rmdir()
    _junction(p_drive / "MyMod", workspace / "MyMod")
    monkeypatch.setattr(lint.h, "link_target", lint.h._preflight().link_target)  # the real resolver, not the fixture's
    monkeypatch.setattr(lint, "P_DRIVE", p_drive)
    monkeypatch.setattr(lint, "cached_workspace", lambda: workspace)
    assert lint.main(["--mod-dir", str(workspace / "MyMod"), "--json"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "PASS", out
    # A real link to some other folder is still an error.
    other = tmp_path / "other"
    other.mkdir()
    (p_drive / "MyMod").rmdir()  # removes the junction only, never its target
    _junction(p_drive / "MyMod", other)
    assert lint.main(["--mod-dir", str(workspace / "MyMod")]) == 1
    assert "points at" in capsys.readouterr().out


def test_unmounted_p_drive_is_only_a_warning_and_skips_vanilla_names(mod, tmp_path):
    edit(mod / "config.cpp", '"DZ_Scripts"', '"DZ_Dta"')
    report = run(mod, tmp_path / "no-P")
    assert [(f["rule"], f["severity"]) for f in report["findings"]] == [("p-not-mounted", "warning")]
    assert report["verdict"] == "PASS"
    assert report["findings"][0]["triage"]["owner_agent"] == "user"


def test_check_link_false_skips_the_link(mod, p_drive):
    (p_drive / "MyMod").rmdir()
    assert lint.lint_mod("MyMod", mod, check_link=False, p_drive=p_drive)["findings"] == []


# --- other behaviour -----------------------------------------------------------

def test_syntax_error_skips_structure_rules(mod, p_drive):
    edit(mod / "config.cpp", "class CfgPatches", "class CfgPatchez")
    edit(mod / "config.cpp", 'weapons[] = {};', 'weapons[] = {}')
    assert {f["rule"] for f in run(mod, p_drive)["findings"]} == {"config-syntax"}


def test_payload_only_bundle_passes_with_a_note(mod, p_drive):
    (mod / "config.cpp").unlink()
    (mod / "Addons").mkdir()
    (mod / "Addons" / "payload.pbo").write_bytes(b"x")
    report = run(mod, p_drive)
    assert report["verdict"] == "PASS" and report["findings"] == []
    assert report["note"].startswith("payload-only bundle")


def test_vanilla_and_other_mod_paths_are_not_checked(mod, p_drive):
    edit(mod / "config.cpp", '"MyMod\\data\\vest_co.paa"', '"DZ\\gear\\vests\\data\\missing_co.paa"')
    edit(mod / "config.cpp", '"MyMod\\data\\vest.rvmat"', '"OtherMod\\data\\other.rvmat"')
    assert run(mod, p_drive)["findings"] == []


def test_nested_script_module_folder_counts_as_listed(mod, p_drive):
    edit(mod / "config.cpp", '{"MyMod/scripts/4_World"}', '{"MyMod/scripts/4_World/MyMod"}')
    (mod / "scripts" / "4_World" / "MyMod").mkdir()
    assert run(mod, p_drive)["findings"] == []


def test_empty_script_folder_needs_no_module(mod, p_drive):
    edit(mod / "config.cpp", '            class missionScriptModule { value = ""; files[] = {"MyMod/scripts/5_Mission"}; };\n', "")
    assert run(mod, p_drive)["findings"] == []


def test_patch_class_without_units_or_weapons_passes_with_warnings(mod, p_drive):
    # Vanilla P:\DZ\data\aiconfigs\config.cpp: class DZ_data_aiconfigs {}; loads with no arrays at all.
    edit(mod / "config.cpp", '        units[] = {"MyMod_Vest"};\n        weapons[] = {};\n', "")
    report = run(mod, p_drive)
    assert report["verdict"] == "PASS" and report["errors"] == 0
    assert [(f["rule"], f["severity"], f["line"]) for f in report["findings"]] == [("cfgpatches-field-missing", "warning", 3)] * 2


def test_patch_class_without_required_addons_fails(mod, p_drive):
    edit(mod / "config.cpp",
         '        units[] = {"MyMod_Vest"};\n        weapons[] = {};\n        requiredVersion = 0.1;\n'
         '        requiredAddons[] = {"DZ_Data", "DZ_Scripts"};\n', "")
    report = run(mod, p_drive)
    assert (report["verdict"], report["errors"], report["warnings"]) == ("FAIL", 1, 2)
    assert [(f["rule"], f["severity"]) for f in report["findings"]] == [
        ("required-addons-missing", "error"), ("cfgpatches-field-missing", "warning"), ("cfgpatches-field-missing", "warning")]


def test_unlisted_script_folder_is_only_a_warning(mod, p_drive):
    edit(mod / "config.cpp", '            class worldScriptModule { value = ""; files[] = {"MyMod/scripts/4_World"}; };\n', "")
    report = run(mod, p_drive)
    assert (report["verdict"], report["errors"]) == ("PASS", 0)
    assert [f["rule"] for f in report["findings"]] == ["script-module-unlisted"]


def test_patch_names_reads_only_cfgpatches_children():
    text = "// class CfgPatches { class Fake {}; };\nclass CfgPatches { class A { x[] = {}; }; class B: A {}; };\nclass CfgVehicles { class C {}; };"
    assert lint.patch_names(text) == {"a", "b"}


def test_missing_mod_folder_raises(tmp_path):
    with pytest.raises(lint.LintError):
        lint.lint_mod("Nope", tmp_path / "Nope")


# --- CLI -------------------------------------------------------------------------

def test_cli_text_and_json(mod, p_drive, monkeypatch, capsys):
    monkeypatch.setattr(lint, "P_DRIVE", p_drive)
    edit(mod / "config.cpp", 'units[] = {"MyMod_Vest"};', 'units = "MyMod_Vest";')
    assert lint.main(["--mod-dir", str(mod)]) == 1
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "FAIL"
    assert any(line.endswith("config.cpp:5  error cfgpatches-field: CfgPatches class MyMod: units must be an array, units[] = {...};.")
               for line in out)
    assert any(line.startswith("    -> dayz-config-specialist: ") for line in out)
    assert lint.main(["--mod-dir", str(mod), "--json"]) == 1
    first, _, rest = capsys.readouterr().out.partition("\n")
    data = json.loads(rest)
    assert (first, data["verdict"], data["errors"]) == ("FAIL", "FAIL", 1)


def test_cli_uses_the_cached_project(mod, p_drive, monkeypatch, capsys):
    monkeypatch.setattr(lint, "P_DRIVE", p_drive)
    monkeypatch.setattr(lint.h, "resolve_project_dir", lambda: mod.parents[1])
    assert lint.main(["MyMod"]) == 0
    assert capsys.readouterr().out.splitlines()[0] == "PASS"


def test_cli_errors_exit_2(tmp_path, monkeypatch, capsys):
    assert lint.main([]) == 2
    assert lint.main(["--mod-dir", str(tmp_path / "missing")]) == 2
    def refuse():
        raise SystemExit(2)
    monkeypatch.setattr(lint.h, "resolve_project_dir", refuse)
    assert lint.main(["MyMod"]) == 2
    assert "ERROR" in capsys.readouterr().out


def test_no_cached_project_prints_the_verdict_first(monkeypatch, capsys):
    # resolve_project_dir prints its reason on stderr before exiting; that must not come before the verdict.
    def no_cache():
        print("[FAIL] No project cached.", file=sys.stderr)
        print("       Run /dayz-init to set up your DayZ environment and project.", file=sys.stderr)
        raise SystemExit(2)
    monkeypatch.setattr(lint.h, "resolve_project_dir", no_cache)
    assert lint.main(["MyMod"]) == 2
    out, err = capsys.readouterr()
    assert err == ""
    lines = out.splitlines()
    assert lines[0] == "ERROR"
    assert "No project cached. Run /dayz-init" in lines[1] and "--mod-dir" in lines[1]


@pytest.mark.parametrize("argv", [[], ["--bogus"], ["MyMod", "extra"]])
def test_bad_arguments_print_the_verdict_first(argv, capsys):
    assert lint.main(argv) == 2
    out, err = capsys.readouterr()
    assert err == ""
    lines = out.splitlines()
    assert lines[0] == "ERROR" and "usage:" in lines[1]


def test_bad_arguments_with_json_print_an_error_object(capsys):
    assert lint.main(["--bogus", "--json"]) == 2
    first, _, rest = capsys.readouterr().out.partition("\n")
    data = json.loads(rest)
    assert first == "ERROR" and data["verdict"] == "ERROR" and "--bogus" in data["error"]


def test_help_still_exits_0(capsys):
    assert lint.main(["--help"]) == 0


@pytest.mark.parametrize("name", ["..", "..\\Other", "a/b", "P:Mod"])
def test_mod_name_that_is_a_path_is_refused(name, monkeypatch, capsys):
    monkeypatch.setattr(lint.h, "resolve_project_dir", lambda: pytest.fail("resolved the project for a bad name"))
    assert lint.main([name]) == 2
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "ERROR" and "--mod-dir" in lines[1]


def test_messages_print_paths_with_single_backslashes(mod, p_drive):
    # repr() doubled every backslash: 'P:\\MyMod\\data\\vest.p3d'.
    edit(mod / "config.cpp", '"\\MyMod\\data\\vest.p3d"', '"P:\\MyMod\\data\\vest.p3d"')
    write("$PBOPREFIX$", "My\\Mod")(mod)
    report = run(mod, p_drive)
    messages = {f["rule"]: f["message"] for f in report["findings"]}
    assert messages["absolute-path"].startswith("'P:\\MyMod\\data\\vest.p3d' is a disk path")
    assert messages["pboprefix-mismatch"].startswith("$PBOPREFIX$ is 'My\\Mod', expected 'MyMod'")
    assert all("\\\\" not in f["message"] for f in report["findings"])


def test_png_reference_is_reported_once(mod, p_drive):
    # The .png does not exist either, but packing it to .paa is the one fix; no second missing-file error.
    edit(mod / "config.cpp", '"MyMod\\data\\vest_co.paa"', '"MyMod\\data\\vest_co.png"')
    report = run(mod, p_drive)
    assert [(f["rule"], f["line"]) for f in report["findings"]] == [("texture-format", 33)]
    assert report["errors"] == 1


def test_fixes_name_the_linted_folder_outside_workspace(mod, tmp_path, p_drive, monkeypatch, capsys):
    outside = tmp_path / "repos" / "MyMod"
    shutil.copytree(mod, outside)
    (outside / "data" / "vest.p3d").unlink()
    (outside / "$PBOPREFIX$").unlink()
    monkeypatch.setattr(lint, "P_DRIVE", p_drive)
    monkeypatch.setattr(lint, "cached_workspace", lambda: tmp_path / "proj" / "workspace")
    monkeypatch.chdir(tmp_path)
    assert lint.main(["--mod-dir", str(outside), "--json"]) == 1
    fixes = {f["rule"]: f["triage"]["fix"] for f in json.loads(capsys.readouterr().out.partition("\n")[2])["findings"]}
    assert "workspace/" not in fixes["missing-model"] and "repos/MyMod/" in fixes["missing-model"]
    assert fixes["pboprefix-missing"] == "Create repos/MyMod/$PBOPREFIX$ holding the single line MyMod."


def test_config_missing_fix_outside_workspace_does_not_name_add_scaffold(mod, tmp_path, p_drive, monkeypatch, capsys):
    outside = tmp_path / "repos" / "MyMod"
    shutil.copytree(mod, outside)
    (outside / "config.cpp").unlink()
    monkeypatch.setattr(lint, "P_DRIVE", p_drive)
    monkeypatch.setattr(lint, "cached_workspace", lambda: tmp_path / "proj" / "workspace")
    monkeypatch.chdir(tmp_path)
    assert lint.main(["--mod-dir", str(outside), "--json"]) == 1
    [f] = json.loads(capsys.readouterr().out.partition("\n")[2])["findings"]
    assert f["rule"] == "config-missing"
    assert "/dayz-add-scaffold" not in f["triage"]["fix"] and "repos/MyMod/Addons/" in f["triage"]["fix"]


def test_workspace_fixes_keep_the_workspace_path(mod, p_drive):
    (mod / "data" / "vest.p3d").unlink()
    [f] = run(mod, p_drive)["findings"]
    assert "add the .p3d under workspace/MyMod/" in f["triage"]["fix"]


def test_script_runs_standalone(mod):
    r = subprocess.run([sys.executable, str(HERE / "lint.py"), "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and "--mod-dir" in r.stdout
