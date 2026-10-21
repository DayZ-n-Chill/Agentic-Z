"""Tests for recipe.py: each recipe on a small vanilla tree built in tmp_path, plus the failure paths.

The tree holds only the classes and properties the recipes read, at the paths
the recipe hints name. One test also runs the default recipes against the real
P:\\ when it is mounted.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
_spec = importlib.util.spec_from_file_location("dayz_recipe_under_test", HERE / "recipe.py")
recipe = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = recipe  # its dataclasses look the module up while it loads
_spec.loader.exec_module(recipe)

VANILLA_FILES = {
    "dz/data/config.cpp": """class CfgPatches
{
    class DZ_Data { units[] = {}; requiredAddons[] = {}; };
};
class CfgVehicles
{
    class HouseNoDestruct;
    class Inventory_Base: HouseNoDestruct
    {
        scope = 0;
    };
    class Clothing_Base: Inventory_Base {};
    class Clothing: Clothing_Base {};
};
""",
    "dz/weapons/firearms/akm/config.cpp": """class CfgPatches
{
    class DZ_Weapons_Firearms_AKM
    {
        units[] = {"AKM"};
        requiredAddons[] = {"DZ_Data"};
    };
};
class Mode_FullAuto;
class cfgWeapons
{
    class Rifle_Base;
    class AKM_Base: Rifle_Base
    {
        // class NotAClass { } in a comment must not count
        descriptionShort = "A rifle; with { braces } in a string";
        magazines[] = {"Mag_AKM_30Rnd", "Mag_AKM_Drum75Rnd"};
        hiddenSelections[] = {"camo", "camo2"};
        class Particles { class OnFire {}; };
    };
    class AKM: AKM_Base
    {
        scope = 2;
        attachments[] =
        {
            "weaponButtstockAK",
            "weaponOpticsAK"
        };
        itemSize[] = {8, 3};
    };
};
""",
    "dz/weapons/firearms/m4/config.cpp": """class CfgPatches
{
    class DZ_Weapons_Firearms_M4 { units[] = {"M4A1"}; };
};
class CfgWeapons
{
    class Rifle_Base;
    class M4A1: Rifle_Base
    {
        attachments[] = {"weaponButtstockM4"};
        magazines[] = {"Mag_STANAG_30Rnd"};
    };
};
""",
    "dz/weapons/attachments/support/config.cpp": """class CfgPatches
{
    class DZ_Weapons_Supports {};
};
class CfgVehicles
{
    class Inventory_Base;
    class AK_WoodBttstck: Inventory_Base
    {
        inventorySlot[] = {"weaponButtstockAK"};
    };
    class M4_OEBttstck: Inventory_Base
    {
        inventorySlot = "weaponButtstockM4";
    };
};
""",
    "dz/weapons/attachments/magazine/config.cpp": """class CfgPatches
{
    class DZ_Weapons_Magazines {};
};
class CfgMagazines
{
    class Magazine_Base;
    class Mag_AKM_30Rnd: Magazine_Base { count = 30; };
    class Mag_STANAG_30Rnd: Magazine_Base { count = 30; };
};
""",
    "dz/characters/vests/config.cpp": """class CfgPatches
{
    class DZ_Characters_Vests {};
};
class CfgVehicles
{
    class Clothing;
    class SmershVest: Clothing
    {
        attachments[] = {"VestBackpack", "VestGrenadeA"};
        inventorySlot[] = {"Vest"};
        itemsCargoSize[] = {4, 4};
        hiddenSelections[] = {"camoGround", "camoMale", "camoFemale"};
    };
};
""",
    "dz/characters/backpacks/config.cpp": """class CfgPatches
{
    class DZ_Characters_Backpacks {};
};
class CfgVehicles
{
    class Clothing;
    class SmershBag: Clothing
    {
        inventorySlot[] = {"Back", "VestBackpack"};
    };
};
""",
    "dz/gear/consumables/config.cpp": """class CfgPatches
{
    class DZ_Gear_Consumables {};
};
class CfgVehicles
{
    class Inventory_Base;
    class Rag: Inventory_Base { itemSize[] = {1, 3}; inventorySlot[] = {"Rags"}; };
    class DuctTape: Inventory_Base { itemSize[] = {1, 2}; };
    class BigBox: Inventory_Base { itemSize[] = {5, 5}; };
};
""",
    "scripts/4_world/classes/recipes/recipebase.c": "const int MAX_NUMBER_OF_INGREDIENTS = 2;\n\nclass RecipeBase\n{\n}\n",
    "scripts/4_world/classes/recipes/recipes/craftragrope.c": "class CraftRagRope extends RecipeBase\n{\n}\n",
    "scripts/4_world/classes/recipes/recipes/pluginrecipesmanagerbase.c":
        "class PluginRecipesManagerBase extends PluginBase\n{\n\tvoid RegisterRecipies()\n\t{\n\t}\n}\n",
    "scripts/4_world/plugins/pluginbase/pluginrecipesmanager.c":
        "// comment\nclass PluginRecipesManager extends PluginRecipesManagerBase\n{\n}\n",
}


@pytest.fixture
def vanilla(tmp_path):
    root = tmp_path / "P"
    for rel, text in VANILLA_FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


@pytest.fixture
def project(tmp_path):
    path = tmp_path / "project"
    path.mkdir()
    return path


def run(vanilla, project, *args):
    return recipe.main(list(args) + ["--vanilla", str(vanilla), "--project", str(project)])


def plan_dir(project, mod):
    return project / "output" / f"{mod}-plan"


# --- the three recipes -------------------------------------------------------------

def test_there_are_three_recipes():
    assert recipe.list_recipes() == ["craftable", "vest", "weapon"]


@pytest.mark.parametrize("name", ["weapon", "vest", "craftable"])
def test_recipe_writes_plan_checks_and_report(name, vanilla, project, capsys):
    assert run(vanilla, project, name, "MyMod") == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "WROTE"
    folder = plan_dir(project, "MyMod")
    plan = (folder / "plan.md").read_text(encoding="utf-8")
    assert plan.startswith(recipe.DRAFT_MARK)
    assert "{" not in plan.replace("{}", "")  # every placeholder filled
    for heading in ("## Classes", "## Vanilla classes", "## Files", "## Tasks", "## Behavior checks",
                    "## Needs a person in game", "## Open questions"):
        assert heading in plan
    # The checks file is what /dayz-gate behavior reads by default, and its own loader accepts it.
    checks_path = recipe.behavior.default_checks_path(project, "MyMod")
    checks = recipe.behavior.load_checks(checks_path)
    assert checks and all(c["item"] for c in checks)
    data = json.loads((folder / "recipe.json").read_text(encoding="utf-8"))
    assert data["recipe"] == name and data["failures"] == []


def test_weapon_plan_names_verified_parents(vanilla, project):
    assert run(vanilla, project, "weapon", "MyGun") == 0
    plan = (plan_dir(project, "MyGun") / "plan.md").read_text(encoding="utf-8")
    akm = vanilla / "dz/weapons/firearms/akm/config.cpp"
    line = VANILLA_FILES["dz/weapons/firearms/akm/config.cpp"].splitlines().index("    class AKM: AKM_Base") + 1
    assert f"`{akm}:{line}`" in plan
    assert "`DZ_Weapons_Firearms_AKM`" in plan
    assert "Add DZ_Weapons_Firearms_AKM to requiredAddons[]" in plan
    assert "Hidden selections of `AKM`: camo, camo2." in plan  # inherited from AKM_Base
    assert "[OK] AK_WoodBttstck fits AKM in slot weaponButtstockAK." in plan
    assert "[OK] AKM takes Mag_AKM_30Rnd." in plan  # magazines[] inherited from AKM_Base
    assert "| T1: Add class MyGun_Rifle : AKM" in plan


def test_cited_lines_hold_the_class(vanilla, project):
    for name in recipe.list_recipes():
        assert run(vanilla, project, name, f"M{name}") == 0
        data = json.loads((plan_dir(project, f"M{name}") / "recipe.json").read_text(encoding="utf-8"))
        for entry in data["vanilla"]:
            line = Path(entry["file"]).read_text(encoding="utf-8").splitlines()[entry["line"] - 1]
            assert re.match(rf"\s*class\s+{entry['class']}\b", line), (entry, line)
        for entry in data["scripts"]:
            line = Path(entry["file"]).read_text(encoding="utf-8").splitlines()[entry["line"] - 1]
            assert entry["symbol"] in line, (entry, line)


def test_vest_checks_cover_wear_attach_cargo(vanilla, project):
    assert run(vanilla, project, "vest", "MyVest", "--item", "MyVest_Carrier") == 0
    checks = json.loads((plan_dir(project, "MyVest") / "behavior-checks.json").read_text(encoding="utf-8"))
    assert checks["mod"] == "MyVest"
    actions = {c["action"]: c for c in checks["checks"]}
    assert set(actions) == {"spawn", "wear", "attach", "cargo"}
    assert actions["attach"]["with"] == "SmershBag" and actions["cargo"]["with"] == "Rag"
    assert all(c["item"] == "MyVest_Carrier" for c in checks["checks"])


def test_craftable_uses_chosen_ingredients(vanilla, project):
    assert run(vanilla, project, "craftable", "MyKit", "--ingredient2", "BigBox") == 0
    plan = (plan_dir(project, "MyKit") / "plan.md").read_text(encoding="utf-8")
    assert "ingredient 0 Rag, ingredient 1 BigBox, result MyKit_Item" in plan
    assert "`Craft_MyKit_Item`" in plan and "RegisterRecipies" in plan


def test_plan_notes_missing_workspace_and_spec(vanilla, project):
    assert run(vanilla, project, "vest", "MyVest") == 0
    plan = (plan_dir(project, "MyVest") / "plan.md").read_text(encoding="utf-8")
    assert "`/dayz-new-mod MyVest`" in plan and "spec.md" not in plan
    (project / "workspace" / "MyVest").mkdir(parents=True)
    (project / "workspace" / "MyVest" / "spec.md").write_text("# spec\n", encoding="utf-8")
    assert run(vanilla, project, "vest", "MyVest", "--force") == 0
    plan = (plan_dir(project, "MyVest") / "plan.md").read_text(encoding="utf-8")
    assert "/dayz-new-mod" not in plan and "`workspace/MyVest/spec.md` exists" in plan


# --- recipe files ------------------------------------------------------------------

TEAMS = {"Script", "Config", "Art", "UI", "Server", "Release"}
AGENTS = {p.stem for p in (REPO / ".claude" / "agents").glob("*.md")}


@pytest.mark.parametrize("name", ["weapon", "vest", "craftable"])
def test_recipe_file_is_consistent(name):
    r = recipe.load_recipe(name)
    ids = [t["id"] for t in r["tasks"]]
    assert len(ids) == len(set(ids))
    for t in r["tasks"]:
        assert t["team"] in TEAMS
        assert t["worker"] in AGENTS
        assert set(t["depends"]) <= set(ids) - {t["id"]}
        assert t["done"] and t["files"]
    assert len({c["id"] for c in r["checks"]}) == len(r["checks"])
    for opt in r["options"].values():
        assert opt["root"] in {"CfgVehicles", "CfgWeapons", "CfgMagazines"}
    for fit in r["fits"]:
        assert fit["host"] in r["options"] and fit.get("item", "parent") in r["options"]
    for spec in r["scripts"]:
        re.compile(spec["pattern"])


@pytest.mark.parametrize("name", ["weapon", "vest", "craftable"])
def test_recipe_prose_has_no_dash_punctuation(name):
    text = (HERE / "recipes" / f"{name}.json").read_text(encoding="utf-8")
    assert "\u2014" not in text and "\u2013" not in text and " - " not in text


# --- failures ----------------------------------------------------------------------

@pytest.mark.parametrize("args, message", [
    (["weapon", "MyGun", "--attachment", "M4_OEBttstck"], "M4_OEBttstck fits no attachment slot of AKM"),
    (["weapon", "MyGun", "--parent", "M4A1"], "M4A1 does not take Mag_AKM_30Rnd"),
    (["vest", "MyVest", "--cargo", "BigBox"], "BigBox (itemSize 5x5) does not fit SmershVest cargo (4x4)"),
    (["vest", "MyVest", "--parent", "Rag"], "Rag is not worn in the Vest slot"),
    (["weapon", "MyGun", "--parent", "NoSuchRifle"], "NoSuchRifle (parent) is not defined in CfgWeapons"),
    # Right name, wrong config root: a magazine is not a CfgVehicles class.
    (["vest", "MyVest", "--attachment", "Mag_AKM_30Rnd"], "Mag_AKM_30Rnd (attachment) is not defined in CfgVehicles"),
])
def test_failed_check_writes_nothing(vanilla, project, capsys, args, message):
    assert run(vanilla, project, *args) == 1
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "FAIL"
    assert message in out and "Nothing was written." in out
    assert not (project / "output").exists()


def test_override_found_outside_the_hint_file(vanilla, project):
    # The weapon hint names the AKM file; an M4 parent is found by scanning every config.cpp.
    assert run(vanilla, project, "weapon", "MyGun", "--parent", "M4A1", "--attachment", "M4_OEBttstck",
               "--magazine", "Mag_STANAG_30Rnd") == 0
    data = json.loads((plan_dir(project, "MyGun") / "recipe.json").read_text(encoding="utf-8"))
    parent = next(e for e in data["vanilla"] if e["option"] == "parent")
    assert Path(parent["file"]) == vanilla / "dz/weapons/firearms/m4/config.cpp"
    assert parent["addon"] == "DZ_Weapons_Firearms_M4"


def test_missing_script_symbol_fails(vanilla, project, capsys):
    (vanilla / "scripts/4_world/classes/recipes/recipebase.c").unlink()
    assert run(vanilla, project, "craftable", "MyKit") == 1
    assert "RecipeBase is not defined under" in capsys.readouterr().out


@pytest.mark.parametrize("args, message", [
    (["vest", "My-Vest"], "mod name 'My-Vest'"),
    (["vest"], "give a <ModName>"),
    (["armor", "MyMod"], "unknown recipe 'armor'"),
    (["vest", "MyVest", "--magazine", "Mag_AKM_30Rnd"], "has no option --magazine"),
    (["vest", "MyVest", "--item", "1Bad"], "--item '1Bad' is not a config class name"),
])
def test_bad_arguments_are_errors(vanilla, project, capsys, args, message):
    assert run(vanilla, project, *args) == 2
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "ERROR" and message in out


def test_no_vanilla_data_is_an_error(tmp_path, project, capsys):
    assert recipe.main(["vest", "MyVest", "--vanilla", str(tmp_path / "nope"), "--project", str(project)]) == 2
    assert "/dayz-workdrive" in capsys.readouterr().out


def test_existing_plan_needs_force(vanilla, project, capsys):
    assert run(vanilla, project, "vest", "MyVest") == 0
    plan = plan_dir(project, "MyVest") / "plan.md"
    plan.write_text("the architect's final plan\n", encoding="utf-8")
    assert run(vanilla, project, "vest", "MyVest") == 2
    assert "already exists" in capsys.readouterr().out
    assert plan.read_text(encoding="utf-8") == "the architect's final plan\n"
    assert run(vanilla, project, "vest", "MyVest", "--force") == 0
    assert plan.read_text(encoding="utf-8").startswith(recipe.DRAFT_MARK)


def test_out_folder_and_json(vanilla, project, tmp_path, capsys):
    out_dir = tmp_path / "elsewhere"
    assert run(vanilla, project, "weapon", "MyGun", "--out", str(out_dir), "--json") == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "WROTE"
    report = json.loads("\n".join(lines[1:]))
    assert report["item"] == "MyGun_Rifle" and len(report["written"]) == 3
    assert (out_dir / "plan.md").is_file()


# --- parser ------------------------------------------------------------------------

def test_parser_skips_comments_strings_and_forward_declarations(tmp_path):
    path = tmp_path / "config.cpp"
    path.write_text(VANILLA_FILES["dz/weapons/firearms/akm/config.cpp"], encoding="utf-8")
    classes = {c.name: c for c in recipe.parse_config(path)}
    assert set(classes) == {"AKM_Base", "AKM"}  # nested Particles and forward declarations are not roots
    assert classes["AKM"].parent == "AKM_Base" and classes["AKM"].root == "cfgWeapons"
    assert classes["AKM"].addon == "DZ_Weapons_Firearms_AKM"
    props = recipe.properties(classes["AKM_Base"].body)
    assert props["magazines"] == ["Mag_AKM_30Rnd", "Mag_AKM_Drum75Rnd"]
    assert props["descriptionShort"] == "A rifle; with { braces } in a string"
    assert "Particles" not in props


def test_cli_list(capsys):
    assert recipe.main(["list", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert [r["name"] for r in listed] == ["craftable", "vest", "weapon"]
    assert listed[2]["options"]["parent"] == "AKM"
    out = subprocess.run([sys.executable, str(HERE / "recipe.py"), "list"], capture_output=True, text=True, check=True)
    assert "--parent SmershVest" in out.stdout


P_DRIVE = Path("P:\\")


@pytest.mark.skipif(not (P_DRIVE / "dz").is_dir() or not (P_DRIVE / "scripts").is_dir(),
                    reason="vanilla data on P: not available")
@pytest.mark.parametrize("name", ["weapon", "vest", "craftable"])
def test_defaults_verify_on_real_p_drive(name, project):
    assert recipe.main([name, "MyMod", "--project", str(project)]) == 0
