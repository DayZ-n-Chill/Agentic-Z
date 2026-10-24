"""Tests for balance.py against the fixture vanilla tree and fixture mod.

No DayZ is needed. Four tests also run against the real P:\\DZ tree and are
skipped when that tree is absent.
"""
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
    assert set(reasons) == {"BalanceMod_Gadget"}
    assert "no vanilla parent" in reasons["BalanceMod_Gadget"]
    # PlainPlate only inherits vanilla stats, so it is compared and listed apart.
    assert [(s["item"], s["reason"]) for s in report["inherits_vanilla"]] == [
        ("BalanceMod_PlainPlate", "sets none of the compared stats")
    ]
    assert report["compared"] == report["items"] - len(report["skipped"]) == 6


def test_text_report_lines_agree_with_the_compared_count():
    # PlainPlate was printed as "not compared" while the summary counted it as
    # compared, so two "not compared" lines sat beside "7 item(s), 6 compared".
    lines = balance.render_text(run(FIXTURE_MOD)).splitlines()
    not_compared = [line for line in lines if "not compared:" in line]
    assert not_compared == ["  not compared: BalanceMod_Gadget has no vanilla parent (parent BalanceMod_Unknown)"]
    assert "  compared (inherits vanilla stats): BalanceMod_PlainPlate sets none of the compared stats" in lines
    assert lines[-1] == f"  5 outlier(s) in 7 item(s), {7 - len(not_compared)} compared"


def test_findings_carry_line_peers_and_meaning():
    report = run(FIXTURE_MOD, display_root=FIXTURES)
    pack = next(f for f in report["findings"] if f["item"] == "BalanceMod_HugePack")
    assert pack["file"] == "BalanceMod/config.cpp"
    lines = (FIXTURE_MOD / "config.cpp").read_text(encoding="utf-8").splitlines()
    assert "itemsCargoSize" in lines[pack["line"] - 1]
    assert pack["value"] == 100
    assert pack["peer_base"] == "TaloonBag_ColorBase"
    assert pack["peer_count"] == 4
    assert (pack["min"], pack["median"], pack["max"]) == (20, 36, 56)
    assert pack["meaning"] == "holds more than vanilla"
    assert {p["class"] for p in pack["peers"]} == {"TaloonBag_Blue", "TaloonBag_Green", "TaloonBag_Orange", "TaloonBag_Violet"}


# --- #include ---------------------------------------------------------------------

INCLUDE_MOD = FIXTURES / "IncludeMod"


def test_items_in_included_files_are_compared_and_point_at_the_included_file():
    # Before includes were followed this mod had no items and passed with exit 0.
    report = run(INCLUDE_MOD, display_root=FIXTURES)
    assert report["verdict"] == "FLAG"
    assert report["items"] == 2
    assert flagged(report) == {
        ("IncludeMod_HeavyPlate", "health", "high"),
        ("IncludeMod_HugePack", "capacity", "high"),
    }
    plate = next(f for f in report["findings"] if f["item"] == "IncludeMod_HeavyPlate")
    assert plate["file"] == "IncludeMod/items/vests.hpp"
    lines = (INCLUDE_MOD / "items" / "vests.hpp").read_text(encoding="utf-8").splitlines()
    assert "hitpoints = 5000" in lines[plate["line"] - 1]
    pack = next(f for f in report["findings"] if f["item"] == "IncludeMod_HugePack")
    assert pack["file"] == "IncludeMod/items/backpacks.hpp"


def test_include_that_cannot_be_followed_is_a_warning(tmp_path):
    report = run(INCLUDE_MOD, display_root=FIXTURES)
    assert report["includes_skipped"] == [
        {"file": "IncludeMod/config.cpp", "line": 18, "include": "items\\missing.hpp", "reason": "was not found"},
    ]
    text = balance.render_text(report)
    assert 'WARN IncludeMod/config.cpp:18  #include "items\\missing.hpp" not read: it was not found' in text


def test_include_outside_the_mod_or_of_itself_is_a_warning_not_a_silent_pass(tmp_path):
    (tmp_path / "outside.hpp").write_text("class CfgVehicles { };", encoding="utf-8")
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    #include "..\\outside.hpp"
    #include "\\OtherMod\\items.hpp"
};
#include "config.cpp"
""")
    report = run(mod)
    # Nothing was read, so nothing was compared: never a PASS.
    assert report["verdict"] == "UNCHECKED"
    assert [(w["line"], w["reason"]) for w in report["includes_skipped"]] == [
        (4, "is outside the mod folder"),
        (5, "is outside the mod folder"),
        (7, "includes itself"),
    ]
    assert "WARN" in balance.render_text(report)


def test_parse_error_in_an_included_file_names_that_file(tmp_path):
    mod = make_mod(tmp_path, 'class CfgVehicles\n{\n    #include "bad.hpp"\n};\n')
    (mod / "bad.hpp").write_text("class X\n{\n    weight = 1\n};\n", encoding="utf-8")
    with pytest.raises(balance.BalanceError, match=r"bad\.hpp does not parse \(line 3"):
        run(mod)


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
    class PlateCarrierVest;
    class TestMod_Base: PlateCarrierVest { scope = 0; weight = 900; };
    class TestMod_Vest: TestMod_Base { scope = 2; };
};
""")
    report = run(mod)
    f = report["findings"][0]
    assert (f["item"], f["stat"], f["direction"], f["peer_base"]) == ("TestMod_Vest", "weight", "low", "PlateCarrierVest")
    assert f["line"] == 5


def test_inherited_vanilla_stats_are_not_judged(tmp_path):
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class PlateCarrierVest;
    class TestMod_Vest: PlateCarrierVest { scope = 2; };
};
""")
    report = run(mod)
    assert report["verdict"] == "PASS"
    assert (report["items"], report["compared"], report["skipped"]) == (1, 1, [])
    assert report["inherits_vanilla"][0]["reason"] == "sets none of the compared stats"


def test_too_few_peers_widens_to_the_next_vanilla_parent(tmp_path):
    # PressVest_ColorBase has one scope 2 item under it, so the group widens to
    # Clothing, where only the vests share the Vest slot.
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class PressVest_ColorBase;
    class TestMod_Vest: PressVest_ColorBase { scope = 2; weight = 50000; };
};
""")
    f = run(mod)["findings"][0]
    assert f["peer_base"] == "Clothing in slot Vest"
    assert f["peer_count"] == 4


def test_no_peer_group_large_enough_skips_the_item(tmp_path):
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class PressVest_ColorBase;
    class TestMod_Vest: PressVest_ColorBase { scope = 2; weight = 50000; };
};
""")
    report = run(mod, min_peers=50)
    assert report["verdict"] == "UNCHECKED"
    assert "fewer than 50 vanilla peers" in report["skipped"][0]["reason"]


MASK_MOD = """
class CfgVehicles
{
    class SurgicalMask;
    class TestMod_Mask: SurgicalMask
    {
        scope = 2;
        class Protection { biological = %s; };
    };
};
"""


def _mask_peers(mod_dir: Path):
    bal = balance.Balance(balance.load_mod(mod_dir), balance.load_vanilla(VANILLA), 1.5, 3)
    node = bal.mod.sections["cfgvehicles"]["testmod_mask"]
    slots = bal.r.slots("cfgvehicles", node, mod_first=True)
    return bal.peer_values("cfgvehicles", bal.ancestors("cfgvehicles", node), "protection.biological", slots)


def test_widened_mask_is_compared_with_mask_slot_peers_only(tmp_path):
    # SurgicalMask alone is too few peers, so the group widens to Clothing, which
    # also holds backpacks that inherit biological = 0 from Inventory_Base.
    base, peers = _mask_peers(make_mod(tmp_path, MASK_MOD % "1"))
    assert base == "Clothing in slot Mask"
    assert {name for name, _ in peers} == {"GasMask", "SurgicalMask", "NioshFaceMask", "BalaclavaMask_Black"}
    assert not any("Pack" in name or "Bag" in name for name, _ in peers)


def test_mask_far_below_the_other_masks_is_flagged_against_them(tmp_path):
    # Against the whole Clothing group the median is 0, so a weak mask would pass.
    f = run(make_mod(tmp_path, MASK_MOD % "0.05"))["findings"][0]
    assert (f["stat"], f["direction"]) == ("protection.biological", "low")
    assert f["peer_base"] == "Clothing in slot Mask"
    assert {p["class"] for p in f["peers"]} == {"GasMask", "SurgicalMask", "NioshFaceMask", "BalaclavaMask_Black"}


DIRECT_MASK_MOD = """
class CfgVehicles
{
    class Clothing;
    class TestMod_Mask: Clothing
    {
        scope = 2;
        inventorySlot[] = {"Mask"};
        class Protection { biological = %s; };
    };
};
"""


def test_mask_written_like_vanilla_is_compared_with_masks_from_the_first_group(tmp_path):
    # class GasMask: Clothing is how vanilla writes masks, so Clothing is the
    # nearest vanilla class at once. Its whole group holds vests and backpacks
    # that inherit biological = 0, so without the slot filter the median is 0.
    base, peers = _mask_peers(make_mod(tmp_path, DIRECT_MASK_MOD % "5"))
    assert base == "Clothing in slot Mask"
    assert {name for name, _ in peers} == {"GasMask", "SurgicalMask", "NioshFaceMask", "BalaclavaMask_Black"}


def test_weak_mask_written_like_vanilla_is_flagged_against_masks(tmp_path):
    f = run(make_mod(tmp_path, DIRECT_MASK_MOD % "0.05"))["findings"][0]
    assert (f["item"], f["stat"], f["direction"]) == ("TestMod_Mask", "protection.biological", "low")
    assert f["peer_base"] == "Clothing in slot Mask"
    assert f["median"] == 0.625


def test_group_where_every_peer_shares_the_slot_keeps_its_plain_name(tmp_path):
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class PlateCarrierVest;
    class TestMod_Vest: PlateCarrierVest { scope = 2; weight = 900; };
};
""")
    assert run(mod)["findings"][0]["peer_base"] == "PlateCarrierVest"


def test_slot_filter_falls_back_when_too_few_share_the_slot(tmp_path):
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class SurgicalMask;
    class TestMod_Mask: SurgicalMask
    {
        scope = 2;
        inventorySlot[] = {"Eyewear"};
        class Protection { biological = 1; };
    };
};
""")
    base, peers = _mask_peers(mod)
    assert base == "Clothing"
    assert any(name == "TaloonBag_Blue" for name, _ in peers)


def test_value_inside_the_vanilla_range_passes(tmp_path):
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class TaloonBag_ColorBase;
    class TestMod_Pack: TaloonBag_ColorBase { scope = 2; weight = 1700; itemsCargoSize[] = {6, 9}; };
};
""")
    assert run(mod)["verdict"] == "PASS"


def test_ratio_controls_how_far_out_counts(tmp_path):
    # Capacity 63 is above the vanilla max of 56 but only 1.75x the median of 36.
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class TaloonBag_ColorBase;
    class TestMod_Pack: TaloonBag_ColorBase { scope = 2; itemsCargoSize[] = {7, 9}; };
};
""")
    assert run(mod, ratio=2.0)["verdict"] == "PASS"
    assert run(mod, ratio=1.5)["verdict"] == "FLAG"


def test_mod_redefinition_of_a_vanilla_item_is_not_its_own_peer(tmp_path):
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class TaloonBag_ColorBase;
    class TaloonBag_Orange: TaloonBag_ColorBase { scope = 2; itemsCargoSize[] = {20, 20}; };
};
""")
    f = run(mod)["findings"][0]
    assert f["item"] == "TaloonBag_Orange"
    assert "TaloonBag_Orange" not in {p["class"] for p in f["peers"]}
    assert f["peer_count"] == 3


def test_mod_override_without_scope_inherits_it_from_the_vanilla_class(tmp_path):
    # The engine merges the block into vanilla TaloonBag_Orange, so its scope = 2 still applies.
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class TaloonBag_ColorBase;
    class TaloonBag_Orange: TaloonBag_ColorBase { itemsCargoSize[] = {20, 20}; };
};
""")
    result = run(mod)
    assert result["items"] == 1
    f = result["findings"][0]
    assert f["item"] == "TaloonBag_Orange"
    assert "TaloonBag_Orange" not in {p["class"] for p in f["peers"]}
    assert f["peer_count"] == 3


# --- ammo families ---------------------------------------------------------------

def _ammo_mod(tmp_path: Path, parent: str, body: str) -> Path:
    return make_mod(tmp_path, f"""
class CfgAmmo
{{
    class {parent};
    class TestMod_Round: {parent}
    {{
        {body}
    }};
}};
""")


def _ammo_peers(mod_dir: Path, stat: str = "damage.health"):
    bal = balance.Balance(balance.load_mod(mod_dir), balance.load_vanilla(VANILLA), 1.5, 3)
    node = bal.mod.sections["cfgammo"]["testmod_round"]
    health = bal.r.stats("cfgammo", node, mod_first=True)["damage.health"]["value"]
    ammo = (bal.ammo_family(node, mod_first=True), health > 0)
    return bal.peer_values("cfgammo", bal.ancestors("cfgammo", node), stat, ammo=ammo)


def test_vanilla_ammo_families():
    bal = balance.Balance(balance.Index(), balance.load_vanilla(VANILLA), 1.5, 3)
    families = {key: bal.vanilla_family(key) for key in bal.descendants("cfgammo", "bullet_base")}
    assert families == {
        "bullet_9x19": "bullet", "bullet_45acp": "bullet", "bullet_380": "bullet", "bullet_beanbag": "bullet",
        "grenade_test": "explosive", "bullet_flare_test": "illumination",
        "meleedamage": "melee", "meleeknife": "melee", "finisherhit": "melee",
        "bullet_40mm_base": "launcher", "bullet_40mm_chemgas": "launcher", "dart_syringe": "dart",
    }


def test_40mm_grenades_and_darts_are_not_firearm_peers(tmp_path):
    # Bullet_40mm_Base, Bullet_40mm_ChemGas and Dart_Syringe deal health damage
    # like a bullet, so they used to sit in the firearm group and drag its median.
    mod = _ammo_mod(tmp_path, "Bullet_Base", "class DamageApplied { class Health { damage = 70; }; };")
    base, peers = _ammo_peers(mod)
    assert base == "Bullet_Base (firearm rounds)"
    assert {name for name, _ in peers} == {"Bullet_9x19", "Bullet_45ACP", "Bullet_380"}


def test_mod_40mm_round_is_measured_against_40mm_rounds_only(tmp_path):
    mod = _ammo_mod(tmp_path, "Bullet_40mm_Base", "class DamageApplied { class Health { damage = 120; }; };")
    bal = balance.Balance(balance.load_mod(mod), balance.load_vanilla(VANILLA), 1.5, 2)
    node = bal.mod.sections["cfgammo"]["testmod_round"]
    assert bal.ammo_family(node, mod_first=True) == "launcher"
    base, peers = bal.peer_values("cfgammo", bal.ancestors("cfgammo", node), "damage.health", ammo=("launcher", True))
    assert base == "Bullet_40mm_Base (40mm launcher rounds)"
    assert {name for name, _ in peers} == {"Bullet_40mm_Base", "Bullet_40mm_ChemGas"}


def test_hot_bullet_is_measured_against_firearm_rounds_only():
    # Every hit inherits Bullet_Base, and the fixture's FinisherHit (1000), explosive
    # (999) and flare (900) used to put a 400 damage round inside the range.
    f = next(f for f in run(FIXTURE_MOD)["findings"] if f["item"] == "BalanceMod_Bullet_Hot")
    assert (f["stat"], f["direction"]) == ("damage.health", "high")
    assert f["peer_base"] == "Bullet_Base (firearm rounds)"
    assert (f["min"], f["max"], f["peer_count"]) == (50, 80, 3)
    assert {p["class"] for p in f["peers"]} == {"Bullet_9x19", "Bullet_45ACP", "Bullet_380"}


def test_weak_lethal_round_leaves_out_non_lethal_peers(tmp_path):
    # The beanbag's health damage 0 used to make the range start at 0, so no round could be low.
    mod = _ammo_mod(tmp_path, "Bullet_Base", "class DamageApplied { class Health { damage = 10; }; };")
    base, peers = _ammo_peers(mod)
    assert base == "Bullet_Base (firearm rounds)"
    assert "Bullet_Beanbag" not in {name for name, _ in peers}
    f = run(mod)["findings"][0]
    assert (f["stat"], f["direction"]) == ("damage.health", "low")


def test_non_lethal_round_is_compared_with_every_firearm_round(tmp_path):
    mod = _ammo_mod(tmp_path, "Bullet_Base", "class DamageApplied { class Health { damage = 0; }; class Shock { damage = 90; }; };")
    _, peers = _ammo_peers(mod)
    assert "Bullet_Beanbag" in {name for name, _ in peers}
    assert run(mod)["verdict"] == "PASS"


def test_mod_melee_hit_is_measured_against_melee_hits(tmp_path):
    mod = _ammo_mod(tmp_path, "MeleeDamage", "class DamageApplied { class Health { damage = 5000; }; };")
    base, peers = _ammo_peers(mod)
    assert base == "MeleeDamage (melee and environment hits)"
    assert {name for name, _ in peers} == {"MeleeDamage", "MeleeKnife", "FinisherHit"}
    assert run(mod)["findings"][0]["direction"] == "high"


def test_mod_explosive_is_not_judged_against_bullets(tmp_path):
    # The fixture has one explosive, fewer than --min-peers, so the stat is not judged.
    mod = _ammo_mod(tmp_path, "Bullet_Base", "explosive = 1; class DamageApplied { class Health { damage = 50000; }; };")
    report = run(mod)
    assert report["verdict"] == "UNCHECKED"
    assert "fewer than 3 vanilla peers" in report["skipped"][0]["reason"]


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
    assert lines[-1].strip() == "5 outlier(s) in 7 item(s), 6 compared"


def test_value_thousands_of_times_below_the_median_reads_as_times_below(tmp_path):
    # Rounding value / median to 2 decimals printed weight 1 against a 12000
    # median as "0x the median"; the report must say how far below it is.
    mod = make_mod(tmp_path, "class CfgVehicles { class PlateCarrierVest; class TestMod_Vest: PlateCarrierVest { scope = 2; weight = 1; }; };")
    report = run(mod)
    f = report["findings"][0]
    assert (f["stat"], f["direction"]) == ("weight", "low")
    assert f["median"] >= 10000
    assert f["ratio"] == float(f"{1 / f['median']:.4g}") and f["ratio"] > 0
    text = balance.render_text(report)
    assert f"weight = 1: lighter than vanilla, {f['median'] / 1:g}x below the median {f['median']:g}" in text
    assert "0x the median" not in text


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


def test_every_item_skipped_is_unchecked_not_pass(tmp_path):
    # A mod built on another mod's bases (CF, Expansion) has no vanilla parent for
    # any item. Comparing nothing used to print PASS and exit 0.
    mod = make_mod(tmp_path, "class CfgVehicles { class OtherMod_VestBase; class TestMod_Vest: OtherMod_VestBase { scope = 2; weight = 99999; }; };")
    report = run(mod)
    assert report["verdict"] == "UNCHECKED"
    assert (report["items"], report["compared"]) == (1, 0)
    assert "has no vanilla parent" in report["skipped"][0]["reason"]
    assert "not a PASS" in balance.render_text(report)
    result = _cli("--mod-dir", str(mod), "--vanilla-root", str(VANILLA))
    assert result.returncode == 3
    assert result.stdout.splitlines()[0] == "UNCHECKED"


def test_mod_with_no_items_is_unchecked(tmp_path):
    mod = make_mod(tmp_path, "class CfgVehicles { class Inventory_Base; class TestMod_Base: Inventory_Base { scope = 0; weight = 5; }; };")
    report = run(mod)
    assert (report["verdict"], report["items"]) == ("UNCHECKED", 0)


def test_item_without_own_stats_on_another_mods_base_is_unchecked(tmp_path):
    # Its stats come from a base we never read, so they are not vanilla's.
    mod = make_mod(tmp_path, "class CfgVehicles { class OtherMod_VestBase; class TestMod_Vest: OtherMod_VestBase { scope = 2; }; };")
    report = run(mod)
    assert report["verdict"] == "UNCHECKED"
    assert "has no vanilla parent" in report["skipped"][0]["reason"]


def test_one_compared_item_still_passes_beside_skipped_ones(tmp_path):
    mod = make_mod(tmp_path, """class CfgVehicles {
    class Bottle_Base; class OtherMod_Base;
    class TestMod_Flask: Bottle_Base { scope = 2; weight = 220; };
    class TestMod_Odd: OtherMod_Base { scope = 2; weight = 5; };
};""")
    report = run(mod)
    assert (report["verdict"], report["items"], report["compared"]) == ("PASS", 2, 1)


def test_vanilla_config_that_does_not_tokenize_is_reported(tmp_path):
    # load_vanilla used to drop such a file silently, so its classes vanished from the peers.
    root = tmp_path / "vroot"
    bad = root / "DZ" / "broken" / "config.cpp"
    bad.parent.mkdir(parents=True)
    bad.write_text('class CfgVehicles { class Broken { name = "open; }; };', encoding="utf-8")
    good = root / "DZ" / "gear" / "drinks" / "config.cpp"
    good.parent.mkdir(parents=True)
    good.write_text((VANILLA / "DZ" / "gear" / "drinks" / "config.cpp").read_text(encoding="utf-8"), encoding="utf-8")
    report = balance.balance_mod("BalanceMod", FIXTURE_MOD, root)
    assert [Path(u["file"]) for u in report["vanilla_unread"]] == [bad]
    assert report["vanilla_unread"][0]["error"].startswith("line 1:")
    assert "WARN" in balance.render_text(report) and "vanilla config not read" in balance.render_text(report)


def test_fixture_vanilla_tree_reads_every_file():
    assert run(FIXTURE_MOD)["vanilla_unread"] == []


def test_cli_error_exits_two(tmp_path):
    result = _cli("--mod-dir", str(tmp_path / "missing"), "--vanilla-root", str(VANILLA))
    assert result.returncode == 2
    assert result.stdout.splitlines()[0] == "ERROR"


def test_cli_without_a_mod_exits_two():
    assert _cli().returncode == 2


# --- the real vanilla tree -------------------------------------------------------

REAL_DZ = balance.P_DRIVE / "DZ" / "characters" / "vests" / "config.cpp"


@pytest.mark.skipif(not REAL_DZ.is_file(), reason="P:\\DZ is not mounted")
def test_real_tree_flags_a_tough_plate_carrier(tmp_path):
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class PlateCarrierVest;
    class TestMod_Vest: PlateCarrierVest
    {
        scope = 2;
        class DamageSystem { class GlobalHealth { class Health { hitpoints = 5000; }; }; };
    };
};
""")
    report = balance.balance_mod(mod.name, mod, balance.P_DRIVE)
    health = [f for f in report["findings"] if f["item"] == "TestMod_Vest" and f["stat"] == "health"]
    assert health, report["findings"]
    assert health[0]["direction"] == "high"
    assert health[0]["peer_base"] == "PlateCarrierVest"


@pytest.mark.skipif(not REAL_DZ.is_file(), reason="P:\\DZ is not mounted")
def test_real_tree_compares_a_direct_clothing_mask_with_masks_only(tmp_path):
    # Vanilla writes masks as class GasMask: Clothing, so a mod mask written the
    # same way starts at Clothing, which also holds every backpack.
    mod = make_mod(tmp_path, """
class CfgVehicles
{
    class Clothing;
    class TestMod_Mask: Clothing
    {
        scope = 2;
        inventorySlot[] = {"Mask"};
        class Protection { biological = 5; };
    };
};
""")
    report = balance.balance_mod(mod.name, mod, balance.P_DRIVE)
    bio = [f for f in report["findings"] if f["stat"] == "protection.biological"]
    assert bio, report["findings"]
    assert bio[0]["peer_base"] == "Clothing in slot Mask"
    # GasMask's biological = 1 is the top of the Mask slot group.
    assert bio[0]["max"] == 1
    # The whole Clothing group has about 786 items; the Mask slot holds far fewer.
    assert bio[0]["peer_count"] < 100
    assert not any("Bag" in p["class"] for p in bio[0]["peers"])


@pytest.mark.skipif(not REAL_DZ.is_file(), reason="P:\\DZ is not mounted")
def test_real_tree_flags_a_400_damage_bullet(tmp_path):
    # All 230 vanilla classes under Bullet_Base ranged from 0 to 1000 (melee
    # FinisherHit, P:\DZ\weapons\melee\config.cpp:151), so this round passed.
    mod = _ammo_mod(tmp_path, "Bullet_Base", "class DamageApplied { class Health { damage = 400; }; class Shock { damage = 45; }; };")
    report = balance.balance_mod(mod.name, mod, balance.P_DRIVE)
    health = [f for f in report["findings"] if f["stat"] == "damage.health"]
    assert health, report["findings"]
    assert (health[0]["direction"], health[0]["peer_base"]) == ("high", "Bullet_Base (firearm rounds)")
    # Bullet_308Win and Bullet_762x54 deal 150, the most of any firearm round.
    assert health[0]["max"] == 150
    bal = balance.Balance(balance.load_mod(mod), balance.load_vanilla(balance.P_DRIVE), 1.5, 3)
    node = bal.mod.sections["cfgammo"]["testmod_round"]
    _, peers = bal.peer_values("cfgammo", bal.ancestors("cfgammo", node), "damage.health", ammo=("bullet", True))
    names = {name for name, _ in peers}
    assert not any(n.startswith(("Melee", "Rocket", "Grenade", "Bullet_Flare", "Bullet_40mm_Smoke")) for n in names)
    assert not names & {"FinisherHit", "Bullet_40mm_Explosive", "Bullet_12GaugeBeanbag", "Bullet_12GaugeRubberSlug"}
    assert {"Bullet_9x19", "Bullet_308Win", "Bullet_556x45"} <= names


@pytest.mark.skipif(not REAL_DZ.is_file(), reason="P:\\DZ is not mounted")
def test_real_tree_keeps_40mm_grenades_and_darts_out_of_rifle_peers(tmp_path):
    # Bullet_40mm_Base (P:\DZ\weapons\projectiles\config.cpp:6875), Bullet_40mm_ChemGas
    # (line 6949) and the shock pistol's Dart_Syringe (line 6445) were 3 of the 21
    # lethal "firearm" peers of a rifle round.
    mod = _ammo_mod(tmp_path, "Bullet_556x45", "class DamageApplied { class Health { damage = 400; }; };")
    bal = balance.Balance(balance.load_mod(mod), balance.load_vanilla(balance.P_DRIVE), 1.5, 3)
    node = bal.mod.sections["cfgammo"]["testmod_round"]
    assert bal.ammo_family(node, mod_first=True) == "bullet"
    assert bal.vanilla_family("bullet_40mm_base") == bal.vanilla_family("bullet_40mm_chemgas") == "launcher"
    assert bal.vanilla_family("dart_syringe") == "dart"
    base, peers = bal.peer_values("cfgammo", bal.ancestors("cfgammo", node), "damage.health", ammo=("bullet", True))
    names = {name for name, _ in peers}
    assert base == "Bullet_Base (firearm rounds)"
    assert not any(n.startswith(("Bullet_40mm", "Dart")) for n in names)
    assert len(peers) == 18
    assert (min(v for _, v in peers), max(v for _, v in peers)) == (20, 150)


@pytest.mark.parametrize("argv", [[], ["--mod-dir", "x", "--ratio", "abc"], ["--json"]])
def test_argparse_errors_still_print_error_first_line(argv, capsys):
    assert balance.main(argv) == 2
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "ERROR"
    if "--json" in argv:
        assert json.loads("\n".join(out[1:]))["verdict"] == "ERROR"
