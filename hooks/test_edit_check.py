"""Tests for the PostToolUse syntax-check hook (edit_check.py)."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "edit_check.py"
_spec = importlib.util.spec_from_file_location("edit_check", SCRIPT)
ec = importlib.util.module_from_spec(_spec)
sys.modules["edit_check"] = ec  # dataclasses look the module up while the class is built
_spec.loader.exec_module(ec)

GOOD_CONFIG = '''\
#define MOD_NAME "MyVest"
class CfgPatches
{
\tclass MyVest
\t{
\t\tunits[] = {};
\t\tweapons[] = {};
\t\trequiredVersion = 0.1;
\t\trequiredAddons[] = {"DZ_Data", "DZ_Characters_Vests"};
\t};
};
class CfgVehicles
{
\tclass Clothing;
\tclass MyVest_Base: Clothing
\t{
\t\tscope = 0;
\t\tdisplayName = "Vest ""Mk2"""; // escaped quotes
\t\tdescriptionShort = "{ not a brace }";
\t\thiddenSelectionsTextures[] =
\t\t{
\t\t\t"MyVest\\data\\vest_co.paa"
\t\t};
\t\tclass DamageSystem
\t\t{
\t\t\tclass GlobalHealth { class Health { hitpoints = 100; healthLevels[] = {{1.0, {"a.rvmat"}}, {0.7, {"b.rvmat"}}}; }; };
\t\t};
\t\t/* block
\t\t   comment */
\t\tinventorySlot[] += {"Vest"};
\t};
\tclass 1kHz_Shader { samples[] = {{"x", 1}}; };
\tdelete OldClass;
};
'''


def _problems(text: str, kind: str = "config"):
    return ec.check_config(text) if kind == "config" else ec.check_layout(text)


def test_valid_config_is_clean():
    assert _problems(GOOD_CONFIG) == []


@pytest.mark.parametrize(
    "broken, line, fragment",
    [
        ("class A\n{\n\tscope = 2\n\tdisplayName = \"x\";\n};\n", 3, "missing ';' after 'scope'"),
        ("class A\n{\n\tscope = 2\n};\n", 3, "missing ';' after 'scope'"),
        ("class A\n{\n\tclass B\n\t{\n\t\tscope = 2;\n\t}\n\tclass C {};\n};\n", 6, "closing class B; write '};'"),
        ("class A\n{\n\tscope = 2;\n", 1, "class A opened here is never closed"),
        ("class A {};\n};\n", 2, "unexpected '}'"),
        ("class A\n{\n\titems = {\"a\", \"b\"};\n};\n", 3, "declare it as 'items[]'"),
        ("class A\n{\n\titems[] = {\"a\"; \"b\"};\n};\n", 3, "';' inside array"),
        ("class A\n{\n\titems[] = {\"a\", \"b\"}\n\tscope = 1;\n};\n", 3, "missing ';' after array 'items[]'"),
        ("class A\n{\n\tdisplayName = \"unclosed;\n};\n", 3, "string starting with \" is not closed"),
        ("class A\n{\n\tscope 2;\n};\n", 3, "missing '='"),
        ("/* never closed\nclass A {};\n", 1, "'/*' comment is never closed"),
    ],
)
def test_config_errors_report_line_and_fix(broken, line, fragment):
    problems = _problems(broken)
    assert problems, broken
    assert problems[0].line == line
    assert fragment in problems[0].message


def test_macro_lines_are_not_flagged():
    text = "class A\n{\n\tMY_MACRO(1, 2)\n\tOTHER_MACRO\n\tscope = 2;\n};\n"
    assert _problems(text) == []


GOOD_LAYOUT = """\
FrameWidgetClass rootFrame {
 position 0 0
 size 1 1
 imageTexture "{5A89D58DD2276E85}gui/textures/x.edds"
 {
  TextWidgetClass Title {
   text "Hello { world }"
   "text halign" center
  }
  TextWidgetClass Cell0 { visible 0 size 0 34 text "" }
  PanelWidgetClass Panel {
   {
    ScriptParamsClass {
     m_ChildName "grid"
    }
   }
  }
 }
}
"""


def test_valid_layout_is_clean():
    assert _problems(GOOD_LAYOUT, "layout") == []


@pytest.mark.parametrize(
    "broken, line, fragment",
    [
        ('<?xml version="1.0"?>\n<layout><FrameWidget/></layout>\n', 1, "this is XML"),
        ("FrameWidgetClass root {\n size 1 1\n {\n  TextWidgetClass t {\n   text \"x\"\n  }\n }\n", 1, "widget root opened here is never closed"),
        ("FrameWidgetClass root {\n size 1 1\n}\n}\n", 4, "unexpected '}'"),
        ("FrameWidgetClass root {\n TextWidgetClass t {\n }\n}\n", 2, "must be inside the parent's bare '{ }' children block"),
        ("FrameWidgetClass root {\n {\n  size 1 1\n }\n}\n", 3, "property 'size' is in a children block"),
        ("FrameWidgetClass root {\n text \"unclosed\n}\n", 2, "unbalanced"),
        ("FrameWidgetClass a {\n}\nFrameWidgetClass b {\n}\n", 3, "second root widget b"),
    ],
)
def test_layout_errors_report_line_and_fix(broken, line, fragment):
    problems = _problems(broken, "layout")
    assert problems, broken
    assert problems[0].line == line
    assert fragment in problems[0].message


@pytest.mark.parametrize(
    "path, kind",
    [
        (r"C:\proj\workspace\MyMod\config.cpp", "config"),
        (r"C:\anywhere\config.cpp", "config"),
        (r"C:\proj\workspace\MyMod\CfgVehicles.hpp", "config"),
        (r"C:\proj\workspace\MyMod\data\model.cpp", "config"),
        (r"C:\elsewhere\CfgVehicles.hpp", None),
        (r"C:\proj\workspace\MyMod\gui\layouts\hud.layout", "layout"),
        (r"C:\proj\workspace\MyMod\scripts\4_World\x.c", None),
        (r"C:\proj\README.md", None),
    ],
)
def test_file_kind(path, kind):
    assert ec.file_kind(path) == kind


def _run_hook(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT)], input=json.dumps(payload), capture_output=True, text=True, timeout=30
    )


def _payload(path: Path, tool: str = "Edit") -> dict:
    return {
        "session_id": "s",
        "cwd": str(path.parent),
        "hook_event_name": "PostToolUse",
        "tool_name": tool,
        "tool_input": {"file_path": str(path), "old_string": "a", "new_string": "b"},
        "tool_response": {"success": True},
    }


def test_hook_is_silent_on_clean_file(tmp_path):
    f = tmp_path / "config.cpp"
    f.write_text(GOOD_CONFIG, encoding="utf-8")
    r = _run_hook(_payload(f))
    assert r.returncode == 0
    assert r.stdout == ""


def test_hook_blocks_with_file_and_line(tmp_path):
    f = tmp_path / "config.cpp"
    f.write_text("class A\n{\n\tscope = 2\n};\n", encoding="utf-8")
    r = _run_hook(_payload(f, "Write"))
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["decision"] == "block"
    assert f"{f}:3: missing ';' after 'scope'" in out["reason"]


def test_hook_ignores_unrelated_files(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("class A {", encoding="utf-8")
    r = _run_hook(_payload(f))
    assert (r.returncode, r.stdout) == (0, "")


@pytest.mark.parametrize("stdin", ["", "not json", json.dumps({"tool_input": {}})])
def test_hook_never_fails_on_bad_input(stdin):
    r = subprocess.run([sys.executable, str(SCRIPT)], input=stdin, capture_output=True, text=True, timeout=30)
    assert (r.returncode, r.stdout) == (0, "")


def test_manual_file_mode(tmp_path):
    f = tmp_path / "hud.layout"
    f.write_text("<layout/>", encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), "--file", str(f)], capture_output=True, text=True, timeout=30)
    assert r.returncode == 1
    assert "this is XML" in r.stdout
