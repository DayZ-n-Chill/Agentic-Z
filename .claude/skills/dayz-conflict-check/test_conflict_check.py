"""Tests for conflict_check.py: fixture mods built in tmp_path with planted collisions. No DayZ, no real P:\\."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_conflict_check_under_test", HERE / "conflict_check.py")
cc = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cc  # its dataclass looks the module up by name
_spec.loader.exec_module(cc)

OUR_CONFIG = """class CfgPatches
{
    class MyVest
    {
        units[] = {"MyVest_Plate"};
        weapons[] = {};
        requiredAddons[] = {"DZ_Data"};
    };
};
class CfgVehicles
{
    class Clothing;
    class MyVest_Plate: Clothing
    {
        scope = 2;
    };
};
"""

OUR_SCRIPT = """modded class PlayerBase
{
};
class MyVest_Helper
{
};
"""


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_mod(root: Path, prefix: str = "MyVest", config: str = OUR_CONFIG, script: str = OUR_SCRIPT) -> Path:
    write(root / "$PBOPREFIX$", prefix + "\n")
    write(root / "config.cpp", config)
    write(root / "scripts" / "4_World" / "MyVest.c", script)
    write(root / "data" / "plate_co.paa", "x")
    return root


def make_pbo(path: Path, prefix: str, files: dict[str, bytes]) -> Path:
    """A real PBO: a Vers entry with the prefix, one entry per file, the end entry, then the data."""
    head = b"\0" + struct.pack("<5I", cc.VERS, 0, 0, 0, 0) + b"prefix\0" + prefix.encode() + b"\0\0"
    for name, data in files.items():
        head += name.encode() + b"\0" + struct.pack("<5I", 0, len(data), 0, 0, len(data))
    head += b"\0" + struct.pack("<5I", 0, 0, 0, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(head + b"".join(files.values()) + b"\0" * 21)
    return path


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A mods folder with CF and COT as PBOs and an Expansion part with an unpacked addon; an empty vanilla P:."""
    mods = tmp_path / "Mods"
    make_pbo(mods / "@CF" / "Addons" / "scripts.pbo", "JM\\CF\\Scripts",
             {"config.bin": b"raP", "4_World\\Entities\\PlayerBase.c": b"modded class PlayerBase {};"})
    make_pbo(mods / "@Community-Online-Tools" / "Addons" / "gui.pbo", "JM\\COT\\GUI",
             {"config.bin": b"raP", "layouts\\menu.layout": b"FrameWidgetClass x {}"})
    exp = mods / "@DayZ-Expansion-Core" / "Addons" / "core"
    write(exp / "$PBOPREFIX$", "DayZExpansion\\Core\n")
    write(exp / "config.cpp", """class CfgPatches { class DayZExpansion_Core { units[] = {}; weapons[] = {}; requiredAddons[] = {}; }; };
class CfgVehicles { class Inventory_Base; class ExpansionBox: Inventory_Base { scope = 2; }; };
""")
    write(exp / "scripts" / "Expansion.c", "class ExpansionHelper\n{\n};\n")
    p_drive = tmp_path / "P"
    (p_drive / "DZ").mkdir(parents=True)
    monkeypatch.setattr(cc, "P_DRIVE", p_drive)
    return tmp_path


def check(world: Path, mod_dir: Path, against=None) -> dict:
    targets = cc.resolve_targets(against or [], False, world / "Mods", mod_dir.name)
    return cc.check_mod(mod_dir.name, mod_dir, targets, world, world / "P")


def rules(report: dict) -> list[str]:
    return [f["rule"] for f in report["findings"]]


# --- clean -------------------------------------------------------------------

def test_clean_mod_against_packed_mods_is_partial_not_pass(world):
    # CF and COT are PBOs: their classes were never compared, so a clean result is not a PASS.
    report = check(world, make_mod(world / "workspace" / "MyVest", script="class MyVest_Helper\n{\n};\n"))
    assert report["verdict"] == "PARTIAL"
    assert report["findings"] == []
    assert [s["mod"] for s in report["scanned"]] == ["@CF", "@Community-Online-Tools", "@DayZ-Expansion-Core"]
    assert report["header_only"] == ["@CF", "@Community-Online-Tools"]
    assert "PBO headers only" in report["note"] and "--ingame" in report["note"]


def test_clean_mod_against_unpacked_mods_passes(world):
    report = check(world, make_mod(world / "workspace" / "MyVest", script="class MyVest_Helper\n{\n};\n"),
                   against=["DayZ-Expansion-Core"])
    assert report["verdict"] == "PASS"
    assert report["header_only"] == [] and "note" not in report


# --- planted collisions -------------------------------------------------------

def test_same_prefix_is_an_error(world):
    report = check(world, make_mod(world / "workspace" / "MyVest", prefix="JM\\CF\\Scripts"))
    f = next(f for f in report["findings"] if f["rule"] == "prefix-same")
    assert f["severity"] == "error" and f["mod"] == "@CF"
    assert f["other"] == "@CF/Addons/scripts.pbo"
    assert report["verdict"] == "FAIL"


def test_nested_prefix_warns_and_shared_path_fails(world):
    mod = make_mod(world / "workspace" / "MyVest", prefix="JM\\CF", script="class MyVest_Helper\n{\n};\n")
    write(mod / "Scripts" / "4_World" / "Entities" / "PlayerBase.c", "class MyVest_Other\n{\n};\n")
    report = check(world, mod)
    assert "prefix-nested" in rules(report)
    path = next(f for f in report["findings"] if f["rule"] == "path-collision")
    assert path["severity"] == "error"
    assert "jm\\cf\\scripts\\4_world\\entities\\playerbase.c" in path["message"]
    assert path["other"].endswith("scripts.pbo > 4_World\\Entities\\PlayerBase.c")


def test_cfgpatches_collision(world):
    config = OUR_CONFIG.replace("class MyVest\n", "class DayZExpansion_Core\n")
    report = check(world, make_mod(world / "workspace" / "MyVest", config=config))
    f = next(f for f in report["findings"] if f["rule"] == "cfgpatches-collision")
    assert f["severity"] == "error" and f["where"] == "workspace/MyVest/config.cpp:3"
    assert f["other"] == "@DayZ-Expansion-Core/Addons/core/config.cpp:1"


def test_config_class_collision_and_override(world):
    config = OUR_CONFIG.replace("MyVest_Plate: Clothing", "ExpansionBox: Clothing")
    report = check(world, make_mod(world / "workspace" / "MyVest", config=config))
    assert "class-collision" in rules(report)
    required = config.replace('{"DZ_Data"}', '{"DZ_Data", "DayZExpansion_Core"}')
    report = check(world, make_mod(world / "workspace" / "MyVest", config=required))
    assert "class-override" in rules(report) and "class-collision" not in rules(report)
    assert report["verdict"] == "PARTIAL"  # warnings only, and CF and COT are header-only


def test_vanilla_class_both_change_is_a_warning(world):
    write(world / "P" / "DZ" / "gear" / "config.cpp", "class CfgVehicles { class Inventory_Base; class ExpansionBox: Inventory_Base {}; };")
    config = OUR_CONFIG.replace("MyVest_Plate: Clothing", "ExpansionBox: Clothing")
    report = check(world, make_mod(world / "workspace" / "MyVest", config=config, script="class MyVest_Helper\n{\n};\n"))
    assert rules(report) == ["vanilla-class-overlap"]
    assert report["findings"][0]["severity"] == "warning"


@pytest.fixture
def vanilla_world(world):
    """The world fixture with a populated P:\\DZ, shaped like the real files: PlateCarrierVest in
    CfgVehicles (P:\\DZ\\characters\\vests\\config.cpp:18 and :24) and Mosin9130 in cfgWeapons
    (P:\\DZ\\weapons\\firearms\\mosin9130\\config.cpp:28 and :300), plus an unpacked mod defining both."""
    write(world / "P" / "DZ" / "characters" / "vests" / "config.cpp",
          "class CfgPatches { class DZ_Characters_Vests { requiredAddons[] = {}; }; };\n"
          "class CfgVehicles\n{\n\tclass Clothing;\n\tclass PlateCarrierVest: Clothing\n\t{\n\t};\n};\n")
    write(world / "P" / "DZ" / "weapons" / "firearms" / "mosin9130" / "config.cpp",
          "class cfgWeapons\n{\n\tclass Mosin9130_Base;\n\tclass Mosin9130: Mosin9130_Base\n\t{\n\t};\n};\n")
    write(world / "Theirs" / "$PBOPREFIX$", "Theirs\n")
    write(world / "Theirs" / "config.cpp",
          "class CfgPatches { class Theirs_P { requiredAddons[] = {}; }; };\n"
          "class CfgVehicles { class Clothing; class PlateCarrierVest: Clothing {}; };\n"
          "class CfgAmmo { class Bullet_Base; class Mosin9130: Bullet_Base {}; };\n")
    return world


VANILLA_SHAPED_CONFIG = OUR_CONFIG.replace("MyVest_Plate: Clothing", "PlateCarrierVest: Clothing") + \
    "class CfgAmmo\n{\n    class Bullet_Base;\n    class Mosin9130: Bullet_Base\n    {\n    };\n};\n"


def test_vanilla_lookup_is_keyed_by_section(vanilla_world):
    # Mosin9130 is vanilla only in cfgWeapons, so two mods defining it in CfgAmmo really collide.
    mod = make_mod(vanilla_world / "workspace" / "MyVest", config=VANILLA_SHAPED_CONFIG, script="class MyVest_Helper\n{\n};\n")
    report = check(vanilla_world, mod, against=[str(vanilla_world / "Theirs")])
    found = {(f["rule"], f["message"].split()[0]) for f in report["findings"]}
    assert found == {("vanilla-class-overlap", "PlateCarrierVest"), ("class-collision", "Mosin9130")}
    assert report["verdict"] == "FAIL" and "note" not in report


def test_vanilla_scan_says_so_on_stderr_and_keeps_stdout_clean(vanilla_world, capsys):
    mod = make_mod(vanilla_world / "workspace" / "MyVest", config=VANILLA_SHAPED_CONFIG, script="class MyVest_Helper\n{\n};\n")
    rc = cc.main(["--mod-dir", str(mod), "--against", str(vanilla_world / "Theirs"), "--json"])
    out, err = capsys.readouterr()
    assert rc == 1 and out.startswith("FAIL\n")
    json.loads(out.partition("\n")[2])
    assert "reading vanilla config classes from" in err


def test_vanilla_scan_of_a_large_config_stays_fast(world):
    # P:\DZ\sounds\hpp\config.cpp is about 10 MB with about 19,000 classes in its Cfg sections.
    # Counting lines from the file start for every class made that one file take over a minute.
    body = "\t\tsamples[] = {{\"DZ\\\\sounds\\\\x\", 1}};\n\t\tvolume = 1;\n" * 10
    classes = "".join(f"\tclass Shader_{i}\n\t{{\n{body}\t}};\n" for i in range(20000))
    text = f"class CfgSoundShaders\n{{\n{classes}}};\n"
    assert len(text) > 8_000_000
    write(world / "P" / "DZ" / "sounds" / "hpp" / "config.cpp", text)
    vanilla = cc.Vanilla(world / "P")
    start = time.perf_counter()
    assert vanilla.config_class("CfgSoundShaders", "Shader_19999")
    assert not vanilla.config_class("CfgVehicles", "Shader_19999")
    assert time.perf_counter() - start < 10
    facts = cc.Facts("v")
    cc.scan_config(text, "big", facts)
    lines = text.splitlines()
    _, where = facts.classes[("cfgsoundshaders", "shader_19999")]
    assert lines[int(where.rsplit(":", 1)[1]) - 1] == "\tclass Shader_19999"


def test_script_class_collision(world):
    report = check(world, make_mod(world / "workspace" / "MyVest", script="class ExpansionHelper\n{\n};\n"))
    f = next(f for f in report["findings"] if f["rule"] == "script-class-collision")
    assert f["where"] == "workspace/MyVest/scripts/4_World/MyVest.c:1"
    assert f["other"] == "@DayZ-Expansion-Core/Addons/core/scripts/Expansion.c:1"


def test_modded_class_overlap_in_unpacked_mod(world):
    write(world / "Mods" / "@DayZ-Expansion-Core" / "Addons" / "core" / "scripts" / "Player.c", "modded class PlayerBase\n{\n};\n")
    report = check(world, make_mod(world / "workspace" / "MyVest"))
    f = next(f for f in report["findings"] if f["rule"] == "modded-class-overlap")
    assert f["severity"] == "warning" and f["mod"] == "@DayZ-Expansion-Core"


def test_script_file_name_in_pbo_header_is_a_likely_overlap(world):
    report = check(world, make_mod(world / "workspace" / "MyVest"))
    f = next(f for f in report["findings"] if f["rule"] == "script-name-match")
    assert f["mod"] == "@CF" and "4_World\\Entities\\PlayerBase.c" in f["message"]
    assert report["verdict"] == "PARTIAL"  # a warning, and CF's classes were not compared


def test_comments_and_strings_are_not_declarations(world):
    script = '// class ExpansionHelper\n/* modded class PlayerBase */\nstring s = "class ExpansionHelper";\n'
    config = OUR_CONFIG + '// class CfgPatches { class DayZExpansion_Core {}; };\n'
    report = check(world, make_mod(world / "workspace" / "MyVest", config=config, script=script))
    assert report["findings"] == []


# --- reading only headers -----------------------------------------------------

def test_header_reader_stops_at_the_data(tmp_path):
    pbo = make_pbo(tmp_path / "a.pbo", "Some\\Prefix", {"config.bin": b"\xff" * 64, "x\\y.c": b"class Hidden {};"})
    props, names = cc.read_pbo_header(pbo)
    assert props["prefix"] == "Some\\Prefix"
    assert names == ["config.bin", "x\\y.c"]


def test_truncated_pbo_is_reported_not_fatal(world):
    (world / "Mods" / "@CF" / "Addons" / "broken.pbo").write_bytes(b"abc")
    report = check(world, make_mod(world / "workspace" / "MyVest"))
    cf = next(s for s in report["scanned"] if s["mod"] == "@CF")
    assert cf["pbo_headers"] == 1 and len(cf["unreadable"]) == 1


def test_scan_never_writes_to_other_mods(world):
    mods = world / "Mods"
    before = {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in mods.rglob("*")}
    check(world, make_mod(world / "workspace" / "MyVest", prefix="JM\\CF\\Scripts"))
    assert {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in mods.rglob("*")} == before


# --- which mods ---------------------------------------------------------------

def test_expansion_bundle_replaces_its_parts(tmp_path):
    for name in ("@CF", "@DayZ-Expansion-Vehicles", "@DayZ-Expansion-Core", "@DayZ-Expansion-Bundle", "@Other"):
        (tmp_path / name).mkdir()
    assert [p.name for p in cc.default_targets(tmp_path)] == ["@CF", "@DayZ-Expansion-Bundle"]
    (tmp_path / "@DayZ-Expansion-Bundle").rmdir()
    assert [p.name for p in cc.default_targets(tmp_path)] == ["@CF", "@DayZ-Expansion-Core", "@DayZ-Expansion-Vehicles"]


def test_against_names_and_own_mod(tmp_path):
    for name in ("@CF", "@MyVest", "@Other"):
        (tmp_path / name).mkdir()
    assert [p.name for p in cc.resolve_targets(["CF", "@Other", "MyVest"], False, tmp_path, "MyVest")] == ["@CF", "@Other"]
    assert [p.name for p in cc.resolve_targets([], True, tmp_path, "MyVest")] == ["@CF", "@Other"]
    with pytest.raises(cc.ConflictError):
        cc.resolve_targets(["Missing"], False, tmp_path, "MyVest")


def test_all_uses_the_expansion_bundle_alone(tmp_path):
    for name in ("@CF", "@DayZ-Expansion-Core", "@DayZ-Expansion-Bundle", "@DayZ-Expansion-Vehicles", "@Other"):
        (tmp_path / name).mkdir()
    assert [p.name for p in cc.resolve_targets([], True, tmp_path, "MyVest")] == ["@CF", "@DayZ-Expansion-Bundle", "@Other"]


def test_against_relative_source_folder(world, monkeypatch):
    source = make_mod(world / "src" / "OtherSource", prefix="OtherSource")
    monkeypatch.chdir(world)
    for item in ("src/OtherSource", "src\\OtherSource", "./src/OtherSource"):
        assert cc.resolve_targets([item], False, world / "Mods", "MyVest") == [source.resolve()]
    # A bare word is a mod name first, and a folder in the current folder only when no such mod exists.
    (world / "CF").mkdir()
    assert cc.resolve_targets(["CF"], False, world / "Mods", "MyVest") == [world / "Mods" / "@CF"]
    assert cc.resolve_targets(["src"], False, world / "Mods", "MyVest") == [(world / "src").resolve()]


def test_cli_relative_against_folder_is_compared(world, monkeypatch, capsys):
    make_mod(world / "src" / "OtherSource", prefix="MyVest")
    mod = make_mod(world / "workspace" / "MyVest")
    monkeypatch.chdir(world)
    rc = cc.main(["--mod-dir", str(mod), "--mods-root", str(world / "Mods"), "--against", "src/OtherSource", "--json"])
    verdict, _, body = capsys.readouterr().out.partition("\n")
    assert rc == 1 and verdict == "FAIL"
    assert "prefix-same" in rules(json.loads(body))


@pytest.mark.parametrize("extra", [[], ["--all"], ["--against", "CF"]])
def test_cli_missing_mods_folder_says_so(world, capsys, extra):
    missing = world / "NoSuchDrive" / "Mods"
    rc = cc.main(["--mod-dir", str(make_mod(world / "workspace" / "MyVest")), "--mods-root", str(missing), *extra])
    out = capsys.readouterr().out
    assert rc == 2 and out.startswith("ERROR\n")
    assert f"mods folder {missing} not found (is P:\\ mounted?)" in out


def test_against_source_paths_need_no_mods_folder(world):
    source = make_mod(world / "OtherSource", prefix="OtherSource")
    assert cc.resolve_targets([str(source)], False, world / "Missing", "MyVest") == [source.resolve()]


def test_only_own_mod_in_against_says_so(tmp_path):
    (tmp_path / "@MyVest").mkdir()
    with pytest.raises(cc.ConflictError, match="@MyVest is your own mod") as e:
        cc.resolve_targets(["@MyVest"], False, tmp_path, "MyVest")
    assert "none of CF" not in str(e.value)


def test_empty_targets_message_names_the_case(tmp_path):
    with pytest.raises(cc.ConflictError, match="--all found no @mod folder"):
        cc.resolve_targets([], True, tmp_path, "MyVest")
    with pytest.raises(cc.ConflictError, match="none of CF, COT or Expansion is under"):
        cc.resolve_targets([], False, tmp_path, "MyVest")
    (tmp_path / "@MyVest").mkdir()
    with pytest.raises(cc.ConflictError, match="is your own mod"):
        cc.resolve_targets([], True, tmp_path, "MyVest")


# --- CLI ----------------------------------------------------------------------

def test_cli_json_fail(world, capsys):
    mod = make_mod(world / "workspace" / "MyVest", prefix="JM\\COT\\GUI")
    rc = cc.main(["--mod-dir", str(mod), "--mods-root", str(world / "Mods"), "--json"])
    out = capsys.readouterr().out
    verdict, _, body = out.partition("\n")
    assert rc == 1 and verdict == "FAIL"
    assert json.loads(body)["findings"][0]["rule"] == "prefix-same"


def test_cli_text_lists_owner_and_fix(world, capsys):
    rc = cc.main(["--mod-dir", str(make_mod(world / "workspace" / "MyVest")), "--mods-root", str(world / "Mods")])
    out = capsys.readouterr().out
    assert rc == 0 and out.startswith("PARTIAL\n")
    assert "-> dayz-script-specialist:" in out and "scanned @CF: 1 PBO header(s)" in out


def test_cli_header_only_says_so_right_under_the_verdict(world, capsys):
    mod = make_mod(world / "workspace" / "MyVest", script="class MyVest_Helper\n{\n};\n")
    rc = cc.main(["--mod-dir", str(mod), "--mods-root", str(world / "Mods"), "--against", "CF", "Community-Online-Tools"])
    verdict, second = capsys.readouterr().out.splitlines()[:2]
    assert rc == 0 and verdict == "PARTIAL"
    assert "not a full check" in second and "--ingame" in second


@pytest.mark.parametrize("as_json", [False, True])
def test_cli_bad_arguments_print_the_error_verdict(capsys, as_json):
    rc = cc.main(["--bogus", *(["--json"] if as_json else [])])
    verdict, _, body = capsys.readouterr().out.partition("\n")
    assert rc == 2 and verdict == "ERROR"
    message = json.loads(body)["error"] if as_json else body
    assert "--bogus" in message and "Usage:" in message


def test_cli_no_mod_prints_the_error_verdict(capsys):
    rc = cc.main([])
    out = capsys.readouterr().out
    assert rc == 2 and out.startswith("ERROR\n") and "give a <ModName> or --mod-dir" in out


def test_cli_error_when_nothing_to_compare(world, capsys):
    rc = cc.main(["--mod-dir", str(make_mod(world / "workspace" / "MyVest")), "--mods-root", str(world / "Empty")])
    assert rc == 2 and capsys.readouterr().out.startswith("ERROR\n")


def test_cli_error_on_missing_mod(world, capsys):
    rc = cc.main(["--mod-dir", str(world / "nope"), "--mods-root", str(world / "Mods")])
    assert rc == 2


# --- the in-game option (the gate is never really run here) ------------------

@pytest.mark.parametrize("gate_verdict, rc_expected", [("PASS", 0), ("FAIL", 1)])
def test_ingame_runs_the_gate_with_the_compared_mods(world, monkeypatch, capsys, gate_verdict, rc_expected):
    make_mod(world / "workspace" / "MyVest")
    monkeypatch.setattr(cc.h, "resolve_project_dir", lambda: world)
    calls = []

    def fake_run(cmd):
        calls.append(cmd)
        gate = {"verdict": gate_verdict, "failures": [{"category": "script", "file": "script.log", "line": 4, "text": "SCRIPT (E): boom"}] if gate_verdict == "FAIL" else []}
        return (0 if gate_verdict == "PASS" else 1), gate_verdict + "\n" + json.dumps(gate)

    rc = cc.main(["MyVest", "--mods-root", str(world / "Mods"), "--ingame", "--server", "chernarus-hc"], run=fake_run)
    out = capsys.readouterr().out
    assert rc == rc_expected
    # CF and COT are header-only, but the game loaded them, so a passing gate turns PARTIAL into PASS
    assert out.startswith(gate_verdict + "\n")
    if gate_verdict == "PASS":
        assert "not a full check" not in out and "checked in game by --ingame" in out
    cmd = calls[0]
    assert cmd[0] == sys.executable and Path(cmd[1]).name == "gate.py"
    assert cmd[2:] == ["ingame", "MyVest", "--deps", "@CF", "@Community-Online-Tools", "@DayZ-Expansion-Core",
                       "--server", "chernarus-hc", "--port", "2302", "--json"]
    assert f"in-game gate on chernarus-hc with @CF @Community-Online-Tools @DayZ-Expansion-Core: {gate_verdict}" in out
    if gate_verdict == "FAIL":
        assert "SCRIPT (E): boom" in out


def test_ingame_unreadable_gate_output_fails(world, monkeypatch, capsys):
    make_mod(world / "workspace" / "MyVest")
    monkeypatch.setattr(cc.h, "resolve_project_dir", lambda: world)
    rc = cc.main(["MyVest", "--mods-root", str(world / "Mods"), "--ingame", "--json"], run=lambda cmd: (2, "ERROR\n  no instance"))
    report = json.loads(capsys.readouterr().out.partition("\n")[2])
    assert rc == 1 and report["ingame"]["verdict"] == "ERROR"


def test_ingame_needs_a_project_mod(world, capsys):
    assert cc.main(["--mod-dir", str(world), "--ingame"]) == 2


def test_ingame_refuses_a_source_folder_in_against(world, monkeypatch, capsys):
    make_mod(world / "workspace" / "MyVest")
    source = make_mod(world / "OtherSource", prefix="OtherSource")
    monkeypatch.setattr(cc.h, "resolve_project_dir", lambda: world)
    rc = cc.main(["MyVest", "--mods-root", str(world / "Mods"), "--against", str(source), "--ingame"],
                 run=lambda cmd: pytest.fail("the gate must not run"))
    out = capsys.readouterr().out
    assert rc == 2 and out.startswith("ERROR")
    assert "OtherSource" in out and "@mod" in out


def test_ingame_accepts_named_mods_in_against(world, monkeypatch, capsys):
    make_mod(world / "workspace" / "MyVest")
    monkeypatch.setattr(cc.h, "resolve_project_dir", lambda: world)
    calls = []
    rc = cc.main(["MyVest", "--mods-root", str(world / "Mods"), "--against", "CF", "--ingame"],
                 run=lambda cmd: calls.append(cmd) or (0, "PASS\n{}"))
    assert rc == 0 and calls[0][4:6] == ["--deps", "@CF"]


def link_folder(link: Path, target: Path) -> bool:
    """Make link point at target: a symlink, or a junction on Windows. False when neither works."""
    try:
        os.symlink(target, link, target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        pass
    if os.name == "nt":
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, text=True)
        return r.returncode == 0
    return False


def test_ingame_accepts_a_linked_mod_in_against(world, monkeypatch, capsys):
    # Workshop @mods under P:\Mods are usually links to a folder elsewhere.
    make_mod(world / "workspace" / "MyVest")
    outside = world / "Workshop" / "CF"
    outside.parent.mkdir()
    shutil.move(str(world / "Mods" / "@CF"), str(outside))
    if not link_folder(world / "Mods" / "@CF", outside):
        pytest.skip("cannot create a symlink or junction here")
    monkeypatch.setattr(cc.h, "resolve_project_dir", lambda: world)
    calls = []
    rc = cc.main(["MyVest", "--mods-root", str(world / "Mods"), "--against", "CF", "--ingame"],
                 run=lambda cmd: calls.append(cmd) or (0, "PASS\n{}"))
    assert rc == 0, capsys.readouterr().out
    assert calls[0][4:6] == ["--deps", "@CF"]
