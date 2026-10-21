"""Tests for triage.py: fingerprints, the known-errors catalog, source checks and --learn."""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_gate_triage_under_test", HERE / "triage.py")
triage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(triage)

AGENTS_DIR = HERE.parents[1] / "agents"
KNOWN = triage.load_known()


# --- fingerprint ---------------------------------------------------------------

def test_fingerprint_same_error_in_two_runs_matches():
    a = r"10:01:02.123 Warning Message: Cannot load texture 'mymod\data\vest_co.paa'. at 0x7FF6A1B2C3D4"
    b = r" 22:59:59.9 Warning Message: Cannot load texture 'mymod\data\vest_co.paa'. at 0x0000000000000001"
    assert triage.fingerprint(a) == triage.fingerprint(b)


def test_fingerprint_normalizes_numbers_paths_and_addresses():
    fp = triage.fingerprint(r"Log C:\Users\me\proj\.server\!ClientDiagLogs\script_2026-01-02_03-04-05.log line 42 ptr 0xDEADBEEF")
    assert fp == "log <path> line <n> ptr <addr>"


def test_fingerprint_keeps_relative_engine_paths_and_lowercases():
    fp = triage.fingerprint(r'SCRIPT    (E): @"MyMod/scripts/4_World\Vest.c,12": Unknown type ''Foo''')
    assert "mymod/scripts/<n>_world/vest.c,<n>" in fp
    assert fp == fp.lower()


def test_fingerprint_differs_for_different_errors():
    assert triage.fingerprint("Cannot load texture 'a_co.paa'") != triage.fingerprint("Cannot load texture 'b_co.paa'")


# --- catalog ---------------------------------------------------------------------

def test_catalog_entries_are_complete_and_unique():
    raw = json.loads(triage.KNOWN_ERRORS.read_text(encoding="utf-8"))
    ids = [e["id"] for e in raw]
    assert len(ids) == len(set(ids))
    for e in raw:
        for key in ("id", "pattern", "meaning", "fix", "owner_agent", "source"):
            assert e.get(key), f"{e.get('id')} lacks {key}"
        re.compile(e["pattern"])
        assert e.get("scope", "log") in {"log", "scripts", "config"}


def test_catalog_owners_are_real_agents_or_the_user():
    for e in KNOWN:
        owner = e["owner_agent"]
        assert owner == "user" or (AGENTS_DIR / f"{owner}.md").is_file(), owner


# Real line formats from DayZ Diag RPT, script and crash logs and the skill scripts.
SAMPLES = [
    ("Connection failed 0x00020005", "filepatching-0x00020005"),
    ("The server does not support the client's current filePatching setting", "filepatching-0x00020005"),
    ("Mission script has no main function. PlayerConnect will stay disabled", "mission-no-main"),
    ('SCRIPT    (E): Can\'t compile "World" script module!', "script-module-compile"),
    ('SCRIPT    (E): @"MyMod/scripts/4_World/Vest.c,12": Unknown type \'CCConfig\'', "script-unknown-type"),
    ("MyMod/scripts/4_World/Vest.c(12): Unknown type 'CCConfig'", "script-unknown-type"),
    ('SCRIPT    (E): @"MyMod/scripts/4_World/Car.c,9": Can\'t find variable \'car_cover\'', "script-cant-find"),
    ('SCRIPT    (E): @"MyMod/scripts/3_Game/x.c,5": Can\'t find class Param9', "script-cant-find"),
    ('SCRIPT    (E): @"MyMod/scripts/5_Mission/m.c,3": Undefined function \'UIColor.BrandColor\'', "script-undefined-function"),
    ("SCRIPT    (E): NULL pointer to instance", "null-pointer"),
    ("NULL pointer to instance", "null-pointer"),
    ("10:00:00.1 Warning Message: Cannot load texture 'mymod\\data\\vest_co.paa'.", "missing-texture"),
    ("Warning Message: Cannot open object mymod\\data\\vest.p3d", "missing-model"),
    ("Warning Message: No entry 'bin\\config.bin/CfgVehicles/MyVest.displayName'.", "missing-config-entry"),
    ("[FAIL] P:\\ is NOT mounted", "p-drive-not-mounted"),
    ("[FAIL] DayZ Tools not found.", "dayz-tools-missing"),
    ("[FAIL] P:\\Mods\\ does not exist and creating the junction failed: denied", "p-mods-junction"),
    ("[FAIL] P:\\Mods\\@MyMod\\ exists but has no Agentic-Z ownership marker", "deploy-dir-not-owned"),
    ("[FAIL] P:\\MyMod junction is missing.", "mod-junction-missing"),
    ("[FAIL] P:\\MyMod exists as a real folder, not a link.", "mod-junction-missing"),
    ("[FAIL] workspace\\MyMod\\$PBOPREFIX$ is 'Other', expected 'MyMod'.", "pboprefix-mismatch"),
    ("[FAIL] workspace\\MyMod\\config.cpp missing.", "scaffold-file-missing"),
    ("[FAIL] Mod 'CF' has no Addons folder at P:\\Mods\\@CF\\Addons", "pbo-not-built"),
    ("[FAIL] Mod 'MyMod' has no .pbo files in P:\\Mods\\@MyMod\\Addons", "pbo-not-built"),
    ("[FAIL] Instance 'chernarus' is not set up. Missing:", "instance-not-set-up"),
    ("[FAIL] DayZDiag_x64.exe not found.", "diag-exe-missing"),
    ("[FAIL] UDP port 2302 in use; run /dayz-stop-test or pass --port.", "port-in-use"),
    ("[WARN] extras.pbo has no matching .bisign - clients with signature verification", "unsigned-payload"),
]


@pytest.mark.parametrize("line,expected", SAMPLES, ids=[s[1] + "-" + str(i) for i, s in enumerate(SAMPLES)])
def test_known_errors_match_real_line_formats(line, expected):
    result = triage.match_line(line, KNOWN)
    assert result["status"] == "known"
    assert result["id"] == expected


def test_every_log_entry_has_a_sample():
    covered = {expected for _, expected in SAMPLES}
    log_ids = {e["id"] for e in KNOWN if e.get("scope", "log") == "log"}
    assert log_ids <= covered


def test_unknown_line_is_new_with_fingerprint():
    result = triage.match_line("SCRIPT    (E): something nobody has seen 42", KNOWN)
    assert result == {"status": "new", "fingerprint": "script (e): something nobody has seen <n>"}


def test_fix_placeholders_are_filled_from_context():
    result = triage.match_line("[FAIL] Instance 'x' is not set up.", KNOWN, {"instance": "livonia", "ModName": "MyMod"})
    assert result["fix"] == "Run /dayz-add-server livonia."


# --- classify ----------------------------------------------------------------------

@pytest.mark.parametrize("line,category", [
    ("Unhandled exception", "crash"),
    ('Can\'t compile "Mission" script module!', "compile"),
    ('SCRIPT    (E): @"A/b.c,1": Unexpected statement', "compile"),
    ("NULL pointer to instance", "null_pointer"),
    ("Can't find something at runtime", "cant_find"),
    ("Warning Message: No entry 'x'", "missing_config"),
    ("Warning Message: Cannot load texture 'x_co.paa'", "missing_texture"),
    ("Warning Message: Cannot open object x.p3d", "missing_model"),
    ("[FAIL] whatever", "script_fail"),
    ("RENDER    (E):   Shader compile failed, can't load shader source 'system/shaders/x.hlsl'.", None),
    ("SCRIPT       : Creating Mission: mpmissions\\__cur_mp.chernarusplus\\mission.c", None),
])
def test_classify(line, category):
    assert triage.classify(line) == category


# --- triage_files ------------------------------------------------------------------

def test_triage_files_skips_normal_lines_and_dedupes(tmp_path):
    log = tmp_path / "script.log"
    log.write_text(
        "SCRIPT       : Module: Game; loaded 415x files\n"
        "10:00:01 Warning Message: Cannot load texture 'a_co.paa'.\n"
        "10:00:02 Warning Message: Cannot load texture 'a_co.paa'.\n"
        "SCRIPT    (E): brand new thing\n",
        encoding="utf-8",
    )
    results = triage.triage_files([log], KNOWN)
    assert [r["line"] for r in results] == [2]
    assert results[0]["count"] == 2
    assert results[0]["id"] == "missing-texture"


# --- source checks ------------------------------------------------------------------

def _mod(tmp_path: Path, config: str | None, script: str = "") -> Path:
    mod = tmp_path / "MyMod"
    (mod / "scripts" / "4_World").mkdir(parents=True)
    (mod / "scripts" / "4_World" / "player.c").write_text(script, encoding="utf-8")
    if config is not None:
        (mod / "config.cpp").write_text(config, encoding="utf-8")
    return mod


def test_source_check_finds_modded_class_with_extends(tmp_path):
    mod = _mod(tmp_path, "class CfgPatches { class MyMod {}; };",
               "class Helper {}\nmodded class PlayerBase extends PlayerBase\n{\n}\n")
    findings = triage.check_sources(mod, KNOWN)
    assert [(f["id"], f["line"]) for f in findings] == [("modded-class-extends", 2)]
    assert findings[0]["owner_agent"] == "dayz-script-specialist"


def test_source_check_accepts_plain_modded_class(tmp_path):
    mod = _mod(tmp_path, "class CfgPatches { class MyMod {}; };", "modded class PlayerBase\n{\n}\n")
    assert triage.check_sources(mod, KNOWN) == []


def test_source_check_flags_config_without_cfgpatches(tmp_path):
    mod = _mod(tmp_path, "class CfgVehicles { class MyVest: Vest_Base {}; };")
    findings = triage.check_sources(mod, KNOWN, {"ModName": "MyMod"})
    assert [f["id"] for f in findings] == ["missing-cfgpatches"]
    assert "class MyMod" in findings[0]["fix"]


def test_source_check_skips_config_entries_for_payload_bundle(tmp_path):
    mod = _mod(tmp_path, None)
    assert triage.check_sources(mod, KNOWN) == []


# --- learn -------------------------------------------------------------------------

def test_learn_new_id_writes_project_file_not_shipped_catalog(tmp_path):
    shipped_before = triage.KNOWN_ERRORS.read_text(encoding="utf-8")
    learned = triage.learned_path(tmp_path)
    entry = triage.learn("cot-perm-warning", "12:00:00 COT: permission file 3 stale", learned, KNOWN,
                         meaning="COT noise", fix="ignore", owner="user")
    assert entry["fingerprint"] == "cot: permission file <n> stale"
    assert json.loads(learned.read_text(encoding="utf-8")) == [entry]
    assert triage.KNOWN_ERRORS.read_text(encoding="utf-8") == shipped_before
    known = triage.load_known(learned=learned)
    hit = triage.match_line("09:09:09 COT: permission file 7 stale", known)
    assert (hit["status"], hit["id"], hit["owner_agent"]) == ("known", "cot-perm-warning", "user")


def test_learn_existing_id_inherits_meaning_fix_and_owner(tmp_path):
    learned = triage.learned_path(tmp_path)
    entry = triage.learn("null-pointer", "SCRIPT (E): Null ref in MyMod thing", learned, KNOWN)
    assert entry["owner_agent"] == "dayz-script-specialist"
    assert entry["fix"].startswith("Open the first mod file")


def test_learn_unknown_id_without_details_is_refused(tmp_path):
    with pytest.raises(ValueError, match="not a known id"):
        triage.learn("brand-new", "x", triage.learned_path(tmp_path), KNOWN)


def test_learn_refuses_duplicate_fingerprint(tmp_path):
    learned = triage.learned_path(tmp_path)
    triage.learn("null-pointer", "odd line 1", learned, KNOWN)
    with pytest.raises(ValueError, match="already learned"):
        triage.learn("null-pointer", "odd line 2", learned, KNOWN)


def test_learned_regexless_entries_are_skipped_by_source_checks(tmp_path):
    learned = triage.learned_path(tmp_path)
    triage.learn("null-pointer", "odd line", learned, KNOWN)
    mod = _mod(tmp_path, "class CfgPatches {};")
    assert triage.check_sources(mod, triage.load_known(learned=learned)) == []


def test_load_known_rejects_non_list(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        triage.load_known(shipped=bad)


# --- CLI ---------------------------------------------------------------------------

def test_cli_learn_and_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(triage, "cached_project_dir", lambda: tmp_path)
    assert triage.main(["--learn", "null-pointer", "--fingerprint", "weird 1"]) == 0
    assert triage.learned_path(tmp_path).is_file()
    log = tmp_path / "x.log"
    log.write_text("weird 99\nNULL pointer to instance\n", encoding="utf-8")
    capsys.readouterr()
    assert triage.main([str(log), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert [r["id"] for r in data["lines"]] == ["null-pointer", "null-pointer"]


def test_cli_learn_without_project_exits_2(monkeypatch, capsys):
    monkeypatch.setattr(triage, "cached_project_dir", lambda: None)
    assert triage.main(["--learn", "null-pointer", "--fingerprint", "x"]) == 2
    assert "run /dayz-init" in capsys.readouterr().err


def test_cli_missing_file_exits_2(tmp_path, monkeypatch):
    monkeypatch.setattr(triage, "cached_project_dir", lambda: None)
    assert triage.main([str(tmp_path / "nope.log")]) == 2


def test_cli_text_output(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(triage, "cached_project_dir", lambda: None)
    log = tmp_path / "x.log"
    log.write_text("Warning Message: Cannot open object mymod\\v.p3d\nUnhandled exception\n", encoding="utf-8")
    assert triage.main([str(log), "--mod", "MyMod"]) == 0
    out = capsys.readouterr().out
    assert "known missing-model -> dayz-config-specialist" in out
    assert "workspace/MyMod/" in out
    assert "new " in out
