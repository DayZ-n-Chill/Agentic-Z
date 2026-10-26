"""The Enforce Script examples must compile together when copied into one mod.

The scans catch the name clashes that break that: a top-level class, const, enum
or function declared in two files, and a field or non-override method that two
files add to the same modded class. They also check cross-file uses, RPC ids
handled by more than one example, modded-class fields nothing uses, and a few
vanilla-backed behaviours of single examples.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parent / "enscript" / "examples"

# A plain (not modded) class declaration at the start of a line.
_CLASS = re.compile(r"^class\s+(\w+)", re.MULTILINE)
# A top-level const at the start of a line (class members are indented).
_CONST = re.compile(r"^(?:static\s+)?const\s+\w+\s+(\w+)\s*=", re.MULTILINE)
# A top-level enum at the start of a line.
_ENUM = re.compile(r"^enum\s+(\w+)", re.MULTILINE)
# A top-level function at the start of a line: an optional static, a return type
# (optionally ref or generic) and a name followed by "(". Class members are
# indented, so they never match.
_FUNC = re.compile(
    r"^(?!(?:class|modded|enum|const|typedef)\b)(?:static\s+)?(?!const\b)"
    r"(?:ref\s+)?\w+(?:<[\w\s,]*>)?\s+(\w+)\s*\(",
    re.MULTILINE,
)
# "Placement: Scripts/4_World/..." names the script layer a file belongs to.
_PLACEMENT = re.compile(r"Placement:\s*scripts/(\d)_\w+", re.IGNORECASE)
# Comments, kept apart from string literals so "//" inside a string survives.
_COMMENT_OR_STRING = re.compile(r'"(?:\\.|[^"\\\n])*"|//[^\n]*|/\*.*?\*/', re.DOTALL)
_STRING = re.compile(r'"(?:\\.|[^"\\\n])*"')


def _sources() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(EXAMPLES.glob("*.c"))}


def _strip_comments(text: str) -> str:
    return _COMMENT_OR_STRING.sub(lambda m: m.group(0) if m.group(0).startswith('"') else " ", text)


def _code(text: str) -> str:
    """Return text with comments removed and every string literal emptied to ""."""
    return _STRING.sub('""', _strip_comments(text))


def _duplicates(pattern: re.Pattern[str], sources: dict[str, str]) -> tuple[dict, dict]:
    seen = defaultdict(list)
    for name_, text in sources.items():
        for name in pattern.findall(_strip_comments(text)):
            seen[name].append(name_)
    return seen, {name: files for name, files in seen.items() if len(files) > 1}


def _cross_file_problems(sources: dict[str, str]) -> list[str]:
    """List uses of another file's top-level name that the using file cannot rely on.

    A file that uses a class, enum, const or function declared in another example
    must name that file (so a reader copies both), and the declaring file must sit
    in the same or a lower script layer: 3_Game cannot see 4_World, and 4_World
    cannot see 5_Mission. A name that appears only in a comment or a string literal
    is not a use.
    """
    declared: dict[str, str] = {}
    for fname, text in sources.items():
        code = _code(text)
        for pattern in (_CLASS, _ENUM, _CONST, _FUNC):
            for name in pattern.findall(code):
                declared.setdefault(name, fname)
    layers = {f: (int(m.group(1)) if (m := _PLACEMENT.search(t)) else None) for f, t in sources.items()}
    problems = []
    for fname, text in sources.items():
        code = _code(text)
        for name, owner in sorted(declared.items()):
            if owner == fname or not re.search(rf"\b{re.escape(name)}\b", code):
                continue
            if owner not in text:
                problems.append(f"{fname} uses {name} from {owner} without naming {owner}")
            if layers[fname] is None or layers[owner] is None:
                problems.append(f"{fname} uses {name} from {owner}, but one of them has no Placement layer")
            elif layers[owner] > layers[fname]:
                problems.append(
                    f"{fname} (layer {layers[fname]}) uses {name} from {owner} (layer {layers[owner]}), "
                    "a higher layer it cannot see"
                )
    return problems


# A modded class header at the start of a line; the body follows at the next "{".
_MODDED = re.compile(r"^modded\s+class\s+(\w+)[^{]*\{", re.MULTILINE)
_ATTRIBUTE = re.compile(r"^\s*\[[^\]]*\]\s*")
_GENERIC = re.compile(r"<[^<>]*>")


def _modded_members(text: str) -> dict[str, set[str]]:
    """Map each modded class in one file to the new members its blocks declare.

    Members marked override are left out: they chain through super across files.
    Constructors and destructors are left out too, as they carry the class name.
    """
    code = _code(text)
    members: dict[str, set[str]] = defaultdict(set)
    for m in _MODDED.finditer(code):
        cls = m.group(1)
        added = members[cls]  # a block of only overrides still counts as found
        # Keep only the class body's top level; each nested block becomes "{}".
        top, depth = [], 1
        for ch in code[m.end():]:
            if ch == "{":
                depth += 1
                if depth == 2:
                    top.append("{};")
                continue
            if ch == "}":
                depth -= 1
                if depth == 0:
                    break
                continue
            if depth == 1:
                top.append(ch)
        for stmt in re.split(r"[;]|\{\}", "".join(top)):
            stmt = _ATTRIBUTE.sub("", stmt).strip()
            if not stmt or re.search(r"\boverride\b", stmt):
                continue
            head = stmt.split("=", 1)[0]
            if "(" in head:
                names = re.findall(r"(~?\w+)\s*\(", head)[:1]
            else:
                while _GENERIC.search(head):
                    head = _GENERIC.sub("", head)
                names = [re.findall(r"\w+", part)[-1] for part in head.split(",") if re.search(r"\w", part)]
            added.update(n for n in names if n.lstrip("~") != cls)
    return members


def _modded_member_clashes(sources: dict[str, str]) -> list[str]:
    """List new members that two files add to the same modded class."""
    owners: dict[tuple[str, str], list[str]] = defaultdict(list)
    for fname, text in sources.items():
        for cls, names in _modded_members(text).items():
            for name in names:
                owners[(cls, name)].append(fname)
    return [
        f"modded class {cls}: {name} declared in {', '.join(files)}"
        for (cls, name), files in sorted(owners.items())
        if len(files) > 1
    ]


def test_examples_modded_classes_add_each_member_once():
    # Two files that add the same field or non-override method to one modded class
    # fail to compile when both are copied into one mod.
    sources = _sources()
    found = {cls for text in sources.values() for cls in _modded_members(text)}
    assert {"PlayerBase", "ActionConstructor"} <= found, "modded class scan found too little"
    clashes = _modded_member_clashes(sources)
    assert not clashes, "\n".join(clashes)


def test_modded_member_check_catches_clashes_and_skips_overrides():
    a = (
        "modded class PlayerBase\n{\n    protected int m_MyMod_A, m_MyMod_Shared;\n"
        "    override void Init()\n    {\n        int m_Local;\n    }\n"
        '    void MyMod_Helper(string s = "{")\n    {\n    }\n}\n'
    )
    b = (
        "modded class PlayerBase\n{\n    [NonSerialized()]\n    protected ref map<string, int> m_MyMod_Shared;\n"
        "    override void Init()\n    {\n    }\n    void PlayerBase()\n    {\n    }\n"
        "    // void MyMod_Helper()\n    bool MyMod_Helper(int x)\n    {\n        return true;\n    }\n}\n"
    )
    other = "modded class MissionServer\n{\n    void MyMod_Helper()\n    {\n    }\n}\n"
    assert _modded_members(a) == {"PlayerBase": {"m_MyMod_A", "m_MyMod_Shared", "MyMod_Helper"}}
    assert _modded_member_clashes({"a.c": a, "b.c": b, "c.c": other}) == [
        "modded class PlayerBase: MyMod_Helper declared in a.c, b.c",
        "modded class PlayerBase: m_MyMod_Shared declared in a.c, b.c",
    ]


def test_examples_declare_each_class_once():
    seen, duplicates = _duplicates(_CLASS, _sources())
    assert seen, "no example classes found"
    assert not duplicates, f"class declared more than once across examples: {duplicates}"


def test_examples_declare_each_const_once():
    seen, duplicates = _duplicates(_CONST, _sources())
    assert seen, "no example consts found"
    assert not duplicates, f"const declared more than once across examples: {duplicates}"


def test_examples_declare_each_enum_once():
    # Two files declaring the same enum fail to compile when copied into one mod.
    seen, duplicates = _duplicates(_ENUM, _sources())
    assert seen, "no example enums found"
    assert not duplicates, f"enum declared more than once across examples: {duplicates}"


def test_examples_declare_each_function_once():
    # Two files declaring the same global function fail to compile together.
    seen, duplicates = _duplicates(_FUNC, _sources())
    assert {"MyMod_SendNotification", "GetMyModConfig"} <= set(seen), "top-level function scan found too little"
    assert not duplicates, f"function declared more than once across examples: {duplicates}"


def test_function_scan_ignores_class_members_and_comments():
    code = _strip_comments(
        "void MyMod_Top(int a)\n{\n}\nclass A\n{\n    void MyMod_Member() {}\n}\n"
        "// void MyMod_Commented()\nref array<int> MyMod_Generic()\n"
    )
    assert _FUNC.findall(code) == ["MyMod_Top", "MyMod_Generic"]


def test_function_scan_catches_static_globals():
    # A file-scope static function is still a global name two files cannot share.
    a = (
        "static void MyMod_Shared()\n{\n}\nstatic const int MYMOD_LIMIT = 3;\n"
        "static ref array<int> MyMod_List()\n{\n}\n"
    )
    b = "static void MyMod_Shared()\n{\n}\n"
    assert _FUNC.findall(a) == ["MyMod_Shared", "MyMod_List"]
    _, duplicates = _duplicates(_FUNC, {"a.c": a, "b.c": b})
    assert duplicates == {"MyMod_Shared": ["a.c", "b.c"]}


def test_examples_cross_file_uses_are_declared_and_visible():
    # A user who copies one example alone must be told which other example declares
    # a name it uses, and that example must load in the same or a lower layer.
    sources = _sources()
    assert any("01_custom_item.c" in t for f, t in sources.items() if f != "01_custom_item.c")
    problems = _cross_file_problems(sources)
    assert not problems, "\n".join(problems)


def test_cross_file_check_catches_missing_note_and_higher_layer():
    owner = "// Placement: Scripts/4_World/X.c\nclass MyMod_Item : ItemBase\n{\n}\n"
    silent = "// Placement: Scripts/4_World/Y.c\nclass MyMod_User\n{\n    MyMod_Item m_Item;\n}\n"
    too_low = "// Placement: Scripts/3_Game/Z.c\n// Needs a.c.\nclass MyMod_Cfg\n{\n    MyMod_Item m_Item;\n}\n"
    noted = "// Placement: Scripts/5_Mission/W.c\n// MyMod_Item comes from a.c.\nvoid MyMod_Use(MyMod_Item i)\n{\n}\n"
    only_comment = "// Placement: Scripts/4_World/V.c\n// Unlike MyMod_Item, this is standalone.\nclass MyMod_Other\n{\n}\n"
    problems = _cross_file_problems(
        {"a.c": owner, "b.c": silent, "c.c": too_low, "d.c": noted, "e.c": only_comment}
    )
    assert problems == [
        "b.c uses MyMod_Item from a.c without naming a.c",
        "c.c (layer 3) uses MyMod_Item from a.c (layer 4), a higher layer it cannot see",
    ]


def test_cross_file_check_ignores_names_inside_strings():
    # Print("MyMod_Item ...") in a lower layer, with no note, is not a use of the class.
    owner = "// Placement: Scripts/4_World/X.c\nclass MyMod_Item : ItemBase\n{\n}\n"
    logger = (
        "// Placement: Scripts/3_Game/L.c\nclass MyMod_Logger\n{\n"
        '    void Go()\n    {\n        Print("MyMod_Item spawned");\n    }\n}\n'
    )
    assert _cross_file_problems({"a.c": owner, "l.c": logger}) == []


def test_stamina_pct_divides_by_configured_max():
    # Raw stamina runs 0..staminaMax from cfggameplay.json
    # (P:\scripts\4_world\classes\staminahandler.c:335-338), so a percentage helper
    # must divide by CfgGameplayHandler.GetStaminaMax()
    # (P:\scripts\3_game\cfggameplayhandler.c:217-220).
    source = (EXAMPLES / "10_modded_playerbase.c").read_text(encoding="utf-8")
    body = _method_body(source, "float MyMod_GetStaminaPct(")
    assert re.search(
        r"GetStamina\(\)\s*/\s*CfgGameplayHandler\.GetStaminaMax\(\)\s*\*\s*100", body
    ), "MyMod_GetStaminaPct returns raw stamina instead of a 0..100 percentage"


def test_player_eonframe_overrides_guard_local_client():
    # PlayerBase.EOnFrame fires for every player on the server and for every nearby
    # player on each client; HUD-style work must be limited to the controlled player,
    # as vanilla does (P:\scripts\4_world\entities\manbase\playerbase.c:4607-4610).
    checked = 0
    for path in sorted(EXAMPLES.glob("*.c")):
        text = _code(path.read_text(encoding="utf-8"))
        for block in re.split(r"^modded\s+class\s+", text, flags=re.MULTILINE)[1:]:
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
    text = _code((EXAMPLES / "09_scheduler_timer.c").read_text(encoding="utf-8"))
    assert re.search(r"float\s+m_LastEatTime\s*=\s*-COOLDOWN\s*;", text), (
        "m_LastEatTime must start at -COOLDOWN so the first CanEat() succeeds"
    )


def _method_body(source: str, signature: str) -> str:
    """Return the brace-delimited body of the first method whose header matches.

    Comments are removed and string literals emptied first, so a "}" inside either
    cannot end the body early, and a commented-out header never matches.
    """
    source = _code(source)
    start = source.index(signature)
    open_at = source.index("{", start)
    depth = 0
    for i in range(open_at, len(source)):
        depth += {"{": 1, "}": -1}.get(source[i], 0)
        if depth == 0:
            return source[open_at + 1 : i]
    raise AssertionError(f"unbalanced braces after {signature!r}")


def test_method_body_skips_braces_in_strings_and_comments():
    source = (
        "// void MyMod_Go() { Stale(); }\n"
        'void MyMod_Go()\n{\n    Print("}");\n    // }\n    /* } */\n    MyMod_Real();\n}\n'
        "void MyMod_Next()\n{\n}\n"
    )
    body = _method_body(source, "void MyMod_Go(")
    assert "MyMod_Real();" in body
    assert "Stale" not in body and "MyMod_Next" not in body


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
    # return when the top menu (UIManager.GetMenu, P:\scripts\3_game\tools\uimanager.c:59) is not ours,
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


_RPC_CASE = re.compile(r"\bcase\s+(\w*RPC\w*\.\w+)\s*:")


def _rpc_case_clashes(sources: dict[str, str]) -> list[str]:
    """List RPC ids that more than one example handles in a switch case.

    Every modded OnRPC runs through the super chain, so when two copied examples
    both handle one id, the second handler re-reads a context the first already read.
    """
    owners: dict[str, list[str]] = defaultdict(list)
    for fname, text in sources.items():
        for rpc in sorted(set(_RPC_CASE.findall(_code(text)))):
            owners[rpc].append(fname)
    return [f"{rpc} handled in {', '.join(files)}" for rpc, files in sorted(owners.items()) if len(files) > 1]


def test_examples_handle_each_rpc_once():
    sources = _sources()
    assert any(_RPC_CASE.search(t) for t in sources.values()), "RPC case scan found nothing"
    clashes = _rpc_case_clashes(sources)
    assert not clashes, "\n".join(clashes)


def test_rpc_case_check_catches_a_second_handler():
    a = "switch (rpc_type)\n{\n    case MyMod_ERPCs.RPC_A:\n        break;\n}\n"
    b = "// case MyMod_ERPCs.RPC_B:\nswitch (rpc_type)\n{\n    case MyMod_ERPCs.RPC_A:\n        break;\n}\n"
    c = 'Print("case MyMod_ERPCs.RPC_A:");\nswitch (rpc_type)\n{\n    case MyMod_ERPCs.RPC_B:\n        break;\n}\n'
    assert _rpc_case_clashes({"a.c": a, "b.c": b, "c.c": c}) == ["MyMod_ERPCs.RPC_A handled in a.c, b.c"]


def _unused_modded_fields(sources: dict[str, str]) -> list[str]:
    """List m_ fields a modded class declares that no example code ever uses."""
    code = " ".join(_code(t) for t in sources.values())
    unused = []
    for fname, text in sources.items():
        for cls, names in _modded_members(text).items():
            for name in sorted(n for n in names if n.startswith("m_")):
                if len(re.findall(rf"\b{re.escape(name)}\b", code)) < 2:
                    unused.append(f"{fname}: modded class {cls} declares {name} but never uses it")
    return unused


def test_examples_modded_fields_are_used():
    # A declared-but-unused field teaches a feature the example never shows.
    unused = _unused_modded_fields(_sources())
    assert not unused, "\n".join(unused)


def test_unused_field_check_catches_a_dead_field():
    a = (
        "modded class PlayerBase\n{\n    protected int m_MyMod_Used;\n    protected float m_MyMod_Dead;\n"
        '    void MyMod_Go()\n    {\n        m_MyMod_Used = 1; // m_MyMod_Dead\n        Print("m_MyMod_Dead");\n    }\n}\n'
    )
    assert _unused_modded_fields({"a.c": a}) == ["a.c: modded class PlayerBase declares m_MyMod_Dead but never uses it"]
