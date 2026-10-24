"""The Enforce Script examples must compile together when copied into one mod."""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parent / "enscript" / "examples"

# A plain (not modded) class declaration at the start of a line.
_CLASS = re.compile(r"^class\s+(\w+)", re.MULTILINE)


def test_examples_declare_each_class_once():
    seen = defaultdict(list)
    for path in sorted(EXAMPLES.glob("*.c")):
        for name in _CLASS.findall(path.read_text(encoding="utf-8")):
            seen[name].append(path.name)
    assert seen, "no example classes found"
    duplicates = {name: files for name, files in seen.items() if len(files) > 1}
    assert not duplicates, f"class declared more than once across examples: {duplicates}"


def test_player_eonframe_overrides_guard_local_client():
    # PlayerBase.EOnFrame fires for every player on the server and for every nearby
    # player on each client; HUD-style work must be limited to the controlled player,
    # as vanilla does (P:\scripts\4_world\entities\manbase\playerbase.c:4607-4610).
    checked = 0
    for path in sorted(EXAMPLES.glob("*.c")):
        text = path.read_text(encoding="utf-8")
        for block in re.split(r"^modded class ", text, flags=re.MULTILINE)[1:]:
            if not block.startswith("PlayerBase") or "void EOnFrame(" not in block:
                continue
            body = _method_body(block, "void EOnFrame(")
            checked += 1
            assert "INSTANCETYPE_CLIENT" in body and "IsControlledPlayer()" in body, (
                f"{path.name}: PlayerBase.EOnFrame override lacks the client + controlled-player guard"
            )
    assert checked, "no PlayerBase.EOnFrame override found in the examples"


def test_eat_cooldown_starts_ready():
    # A last-time field defaulting to 0 makes CanEat() false for the first COOLDOWN seconds.
    text = (EXAMPLES / "09_scheduler_timer.c").read_text(encoding="utf-8")
    assert re.search(r"float\s+m_LastEatTime\s*=\s*-COOLDOWN\s*;", text), (
        "m_LastEatTime must start at -COOLDOWN so the first CanEat() succeeds"
    )


def _method_body(source: str, signature: str) -> str:
    """Return the brace-delimited body of the first method whose header matches."""
    start = source.index(signature)
    open_at = source.index("{", start)
    depth = 0
    for i in range(open_at, len(source)):
        depth += {"{": 1, "}": -1}.get(source[i], 0)
        if depth == 0:
            return source[open_at + 1 : i]
    raise AssertionError(f"unbalanced braces after {signature!r}")


def test_gui_menu_hover_only_tints_the_buttons():
    # The handler sits on layoutRoot, so enter/leave fire for every widget under it.
    # Each hover handler must bail out for non-button widgets before it recolors,
    # and leave must restore the saved color instead of forcing white.
    source = (EXAMPLES / "08_gui_menu.c").read_text(encoding="utf-8")
    guard = _method_body(source, "bool IsHoverButton(")
    assert "m_Menu.m_BtnClose" in guard and "m_Menu.m_BtnRefresh" in guard
    for signature in ("bool OnMouseEnter(", "bool OnMouseLeave("):
        body = _method_body(source, signature)
        assert "SetColor" in body
        bail = re.search(r"if\s*\(\s*!IsHoverButton\(w\)\s*\)\s*return false;", body)
        assert bail, f"{signature} recolors without checking the widget is a button"
        assert bail.start() < body.index("SetColor"), f"{signature} recolors before the guard"
    assert "ARGB(255, 255, 255, 255)" not in _method_body(source, "bool OnMouseLeave(")


def test_gui_menu_hotkey_skips_when_another_menu_is_open():
    # DayZGame forwards every key press to the mission, also while chat or another
    # menu is open (P:\scripts\3_game\dayzgame.c:2848, :2914-2917). The hotkey must
    # return when the top menu (UIManager.GetMenu, uimanager.c:59) is not ours,
    # before it can call EnterScriptedMenu and stack the menu on top.
    source = (EXAMPLES / "08_gui_menu.c").read_text(encoding="utf-8")
    body = _method_body(source, "void OnKeyPress(")
    guard = re.search(
        r"UIScriptedMenu\s+(\w+)\s*=\s*GetGame\(\)\.GetUIManager\(\)\.GetMenu\(\);\s*"
        r"if\s*\(\s*\1\s*&&\s*\1\.GetID\(\)\s*!=\s*MENU_MYMOD_INVENTORY\s*\)\s*return;",
        body,
    )
    assert guard, "OnKeyPress opens the menu without checking another menu is on top"
    assert guard.start() < body.index("EnterScriptedMenu"), "guard must come before EnterScriptedMenu"
