"""Tests for balance.py against the fixture vanilla tree and fixture mod. No DayZ, no real P:\\."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_balance_under_test", HERE / "balance.py")
balance = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(balance)

FIXTURES = HERE / "fixtures"
VANILLA = FIXTURES / "vanilla"
FIXTURE_MOD = FIXTURES / "BalanceMod"


def make_mod(tmp_path: Path, body: str, name: str = "TestMod") -> Path:
    mod_dir = tmp_path / name
    mod_dir.mkdir()
    (mod_dir / "config.cpp").write_text(body, encoding="utf-8")
    return mod_dir


def run(mod_dir: Path, **kwargs) -> dict:
    return balance.balance_mod(mod_dir.name, mod_dir, VANILLA, **kwargs)


def flagged(report: dict) -> set[tuple[str, str, str]]:
    return {(f["item"], f["stat"], f["direction"]) for f in report["findings"]}


# --- the fixture mod ------------------------------------------------------------

def test_fixture_mod_flags_every_planted_outlier_and_nothing_else():
    report = run(FIXTURE_MOD)
    assert report["verdict"] == "FLAG"
    assert flagged(report) == {
        ("BalanceMod_HeavyPlate", "health", "high"),
        ("BalanceMod_HeavyPlate", "protection.projectile.health", "low"),
        ("BalanceMod_HugePack", "capacity", "high"),
        ("BalanceMod_Flask", "quantity", "high"),
        ("BalanceMod_Bullet_Hot", "damage.health", "high"),
    }
    assert report["outliers"] == 5


def test_fixture_mod_counts_items_and_explains_what_it_skipped():
    report = run(FIXTURE_MOD)
    # The scope 0 mod base class is not an item; the ammo class without scope is.
    assert report["items"] == 7
    reasons = {s["item"]: s["reason"] for s in report["skipped"]}
    assert reasons["BalanceMod_PlainPlate"] == "sets none of the compared stats"
    assert "no vanilla parent" in reasons["BalanceMod_Gadget"]
    assert "BalanceMod_PlateBase" not in reasons


def test_findings_carry_line_peers_and_meaning():
    report = run(FIXTURE_MOD, display_root=FIXTURES)
    pack = next(f for f in report["findings"] if f["item"] == "BalanceMod_HugePack")
    assert pack["file"] == "BalanceMod/config.cpp"
    lines = (FIXTURE_MOD / "config.cpp").read_text(encoding="utf-8").splitlines()
    assert "itemsCargoSize" in lines[pack["line"] - 1]
    assert pack["value"] == 100
    assert pack["peer_base"] == "Backpack_Base"
    assert pack["peer_count"] == 4
    assert (pack["min"], pack["median"], pack["max"]) == (20, 36, 56)
    assert pack["meaning"] == "holds more than vanilla"
    assert {p["class"] for p in pack["peers"]} == {"TaloonPack", "HuntingPack", "MountainPack", "CourierBag"}


def test_protection_wording_follows_the_damage_multiplier():
    assert balance.meaning("protection.projectile.health", "low") == "more protection than vanilla"
    assert balance.meaning("protection.melee.shock", "high") == "less protection than vanilla"
    # Protection class values are coverage, so higher means more protection.
    assert balance.meaning("protection.biological", "high") == "more protection than vanilla"
    assert balance.meaning("protection.biological", "low") == "less protection than vanilla"
    assert balance.meaning("protection.dust_particle_inhalation", "high") == "more protection than vanilla"
    assert balance.meaning("weight", "low") == "lighter than vanilla"
    assert balance.meaning("damage.health", "high") == "hits harder than vanilla"


# --- peers -----------------------------------------------------------------------

def test_stat_set_on_a_mod_base_class_is_compared_with_the_vanilla_peers(tmp_path):
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class PlateVest;
    class TestMod_Base: PlateVest { scope = 0; weight = 900; };
    class TestMod_Vest: TestMod_Base { scope = 2; };
};
""")
    report = run(mod)
    f = report["findings"][0]
    assert (f["item"], f["stat"], f["direction"], f["peer_base"]) == ("TestMod_Vest", "weight", "low", "PlateVest")
    assert f["line"] == 5


def test_inherited_vanilla_stats_are_not_judged(tmp_path):
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class PlateVest;
    class TestMod_Vest: PlateVest { scope = 2; };
};
""")
    report = run(mod)
    assert report["verdict"] == "PASS"
    assert report["skipped"][0]["reason"] == "sets none of the compared stats"


def test_too_few_peers_widens_to_the_next_vanilla_parent(tmp_path):
    # PressVest has one scope 2 item under it, so the group widens to Vest_Base.
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class PressVest;
    class TestMod_Vest: PressVest { scope = 2; weight = 50000; };
};
""")
    f = run(mod)["findings"][0]
    assert f["peer_base"] == "Vest_Base"
    assert f["peer_count"] == 4


def test_no_peer_group_large_enough_skips_the_item(tmp_path):
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class PressVest;
    class TestMod_Vest: PressVest { scope = 2; weight = 50000; };
};
""")
    report = run(mod, min_peers=10)
    assert report["verdict"] == "PASS"
    assert "fewer than 10 vanilla peers" in report["skipped"][0]["reason"]


def test_value_inside_the_vanilla_range_passes(tmp_path):
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class Backpack_Base;
    class TestMod_Pack: Backpack_Base { scope = 2; weight = 1700; itemsCargoSize[] = {6, 9}; };
};
""")
    assert run(mod)["verdict"] == "PASS"


def test_ratio_controls_how_far_out_counts(tmp_path):
    # Capacity 63 is above the vanilla max of 56 but only 1.75x the median of 36.
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class Backpack_Base;
    class TestMod_Pack: Backpack_Base { scope = 2; itemsCargoSize[] = {7, 9}; };
};
""")
    assert run(mod, ratio=2.0)["verdict"] == "PASS"
    assert run(mod, ratio=1.5)["verdict"] == "FLAG"


def test_mod_redefinition_of_a_vanilla_item_is_not_its_own_peer(tmp_path):
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class Backpack_Base;
    class MountainPack: Backpack_Base { scope = 2; itemsCargoSize[] = {20, 20}; };
};
""")
    f = run(mod)["findings"][0]
    assert f["item"] == "MountainPack"
    assert "MountainPack" not in {p["class"] for p in f["peers"]}
    assert f["peer_count"] == 3


def test_mod_override_without_scope_inherits_it_from_the_vanilla_class(tmp_path):
    # The engine merges the block into vanilla MountainPack, so its scope = 2 still applies.
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class Backpack_Base;
    class MountainPack: Backpack_Base { itemsCargoSize[] = {20, 20}; };
};
""")
    result = run(mod)
    assert result["items"] == 1
    f = result["findings"][0]
    assert f["item"] == "MountainPack"
    assert "MountainPack" not in {p["class"] for p in f["peers"]}
    assert f["peer_count"] == 3


# --- parser ------------------------------------------------------------------------

def test_parser_reads_parents_arrays_and_signed_numbers():
    root = balance.parse_config("""
class CfgVehicles
{
    class A;
    class B: A { offset = -2.5; size[] = {3, 4}; name = "x"; };
};
""")
    b = root.classes["cfgvehicles"].classes["b"]
    assert b.parent == "A"
    assert b.props["offset"][0] == [-2.5]
    assert b.props["size"][0] == [3.0, 4.0]
    assert "a" not in root.classes["cfgvehicles"].classes  # forward declaration, no body


def test_repeated_class_definitions_merge():
    index = balance.Index()
    index.add(balance.parse_config("class CfgVehicles { class X: Y { weight = 1; a = 1; }; };"))
    index.add(balance.parse_config("class CfgVehicles { class X { weight = 2; }; };"))
    x = index.get("cfgvehicles", "x")
    assert x.parent == "Y"
    assert x.props["weight"][0] == [2.0]
    assert x.props["a"][0] == [1.0]


# --- errors and CLI --------------------------------------------------------------------

def test_broken_config_is_an_error_pointing_at_lint(tmp_path):
    mod = make_mod(tmp_path, "class CfgVehicles { class X { weight = 1 }; };")
    with pytest.raises(balance.BalanceError, match="dayz-lint"):
        run(mod)


def test_missing_vanilla_data_is_an_error(tmp_path):
    with pytest.raises(balance.BalanceError, match="no vanilla data"):
        balance.balance_mod("BalanceMod", FIXTURE_MOD, tmp_path)


def test_mod_without_config_is_an_error(tmp_path):
    (tmp_path / "Empty").mkdir()
    with pytest.raises(balance.BalanceError, match="no config.cpp"):
        run(tmp_path / "Empty")


@pytest.mark.parametrize("kwargs", [{"ratio": 1.0}, {"min_peers": 0}])
def test_bad_thresholds_are_errors(kwargs):
    with pytest.raises(balance.BalanceError):
        run(FIXTURE_MOD, **kwargs)


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HERE / "balance.py"), *args],
        capture_output=True, text=True, encoding="utf-8",
    )


def test_cli_text_report_exits_one_on_outliers():
    result = _cli("--mod-dir", str(FIXTURE_MOD), "--vanilla-root", str(VANILLA))
    assert result.returncode == 1
    lines = result.stdout.splitlines()
    assert lines[0] == "FLAG"
    assert any("BalanceMod_Flask quantity = 9000: holds more than vanilla, 9x the median 1000" in line for line in lines)
    assert lines[-1].strip() == "5 outlier(s) in 7 item(s)"


def test_cli_json_report(tmp_path):
    mod = make_mod(tmp_path, "class CfgVehicles { class Bottle_Base; class TestMod_Flask: Bottle_Base { scope = 2; weight = 220; }; };")
    result = _cli("--mod-dir", str(mod), "--vanilla-root", str(VANILLA), "--json")
    assert result.returncode == 0
    first, rest = result.stdout.split("\n", 1)
    assert first == "PASS"
    data = json.loads(rest)
    assert data["mod"] == "TestMod"
    assert data["items"] == 1
    assert data["findings"] == []


def test_cli_error_exits_two(tmp_path):
    result = _cli("--mod-dir", str(tmp_path / "missing"), "--vanilla-root", str(VANILLA))
    assert result.returncode == 2
    assert result.stdout.splitlines()[0] == "ERROR"


def test_cli_without_a_mod_exits_two():
    assert _cli().returncode == 2
