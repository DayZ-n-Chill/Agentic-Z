"""dayz-gate behavior: the checks file, the test mission injector and the result parser.

gate.py imports this module. The behavior gate copies a test server instance
(.server/<instance>/) to .server/<instance>-behavior/, adds a test mission
script to the copy's init.c, runs the copy through the in-game flow and reads
the lines the script printed:

    [AZ-BEHAVIOR] START <count>
    [AZ-BEHAVIOR] PASS <check id>
    [AZ-BEHAVIOR] FAIL <check id> <reason>
    [AZ-BEHAVIOR] DONE

The script is Enforce Script written for this gate. Every engine call in it
was checked against vanilla P:\\scripts (see SKILL.md, "What behavior does").
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
import skill_helpers as h  # noqa: E402

TAG = "[AZ-BEHAVIOR]"
INSTANCE_SUFFIX = "-behavior"
CHECKS_FILENAME = "behavior-checks.json"

# action -> whether it needs a second class in "with"
ACTIONS = {"spawn": False, "hands": False, "wear": False, "attach": True, "cargo": True}
CHECK_KEYS = {"id", "feature", "item", "action", "with"}
FILE_KEYS = {"mod", "checks"}
# Ids and class names go into Enforce Script string literals and log lines,
# so they are limited to characters that need no escaping and hold no spaces.
ID_RE = re.compile(r"^[A-Za-z0-9][\w.-]{0,63}$")
CLASS_RE = re.compile(r"^[A-Za-z_]\w{0,127}$")

RESULT_RE = re.compile(r"\[AZ-BEHAVIOR\]\s+(START|PASS|FAIL|DONE)\b[ \t]*(\S*)[ \t]*(.*?)\s*$")
DONE_RE = re.compile(r"\[AZ-BEHAVIOR\]\s+DONE\b")

MARK_BEGIN = "// AZ-BEHAVIOR BEGIN: test mission added by /dayz-gate behavior. Not part of your mission."
MARK_END = "// AZ-BEHAVIOR END"
START_CALL = "AZ_BehaviorTest.Start(); // AZ-BEHAVIOR"
TEMPLATE_RE = re.compile(r'^\s*template\s*=\s*"([^"]+)"', re.MULTILINE)
# A mission template is one plain folder name: no separators, no shell metacharacters.
TEMPLATE_NAME_RE = re.compile(r"[A-Za-z0-9_.-]+")

PLAYER_WAIT_S = 240  # the in-game gate gives the client 300 s to reach the mission
SETTLE_S = 10        # seconds after the player appears before the first check

# One test per gate tick (1 s), so a script error in one check only loses that check.
# Engine calls, all in vanilla P:\scripts:
#   CallLater / Remove         2_gamelib/tools.c:61 / :65 (ScriptCallQueue)
#   GetPlayers, CreateObjectEx, ObjectDelete, ConfigIsExisting   3_game/global/game.c:945, :703, :705, :612
#   ECE_PLACE_ON_SURFACE       3_game/ce/centraleconomy.c:38
#   CreateEntityInCargo, GetSlotId, GetSlotIdCount, HasAttachmentSlot, AttachmentCount,
#   CreateAttachment, CreateAttachmentEx, GetAttachmentFromIndex
#                              3_game/systems/inventory/inventory.c:143, :171, :175, :188, :205, :209, :215, :220
#   CreateInHands, GetEntityInHands   3_game/systems/inventory/humaninventory.c:44, :16
#   InventorySlots.INVALID, GetSlotName   3_game/systems/inventory/inventoryslots.c:17, :48
# test_behavior.py (VANILLA_CALLS) holds the full list, every engine name the
# class uses, and fails when a call is added that has not been checked there.
SCRIPT = """\
{begin}
class AZ_BehaviorTest
{{
	static ref AZ_BehaviorTest s_Test;

	ref array<string> m_Ids;
	ref array<string> m_Items;
	ref array<string> m_Actions;
	ref array<string> m_With;
	PlayerBase m_Player;
	int m_Next;
	int m_Waited;
	int m_Settled;

	void AZ_BehaviorTest()
	{{
		m_Ids = new array<string>;
		m_Items = new array<string>;
		m_Actions = new array<string>;
		m_With = new array<string>;
	}}

	static void Start()
	{{
		s_Test = new AZ_BehaviorTest();
{adds}
		s_Test.Begin();
	}}

	void Add(string id, string item, string action, string other)
	{{
		m_Ids.Insert(id);
		m_Items.Insert(item);
		m_Actions.Insert(action);
		m_With.Insert(other);
	}}

	void Begin()
	{{
		Print("[AZ-BEHAVIOR] START " + m_Ids.Count().ToString());
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(Tick, 1000, true);
	}}

	void Tick()
	{{
		if (!m_Player)
		{{
			array<Man> players = new array<Man>;
			GetGame().GetPlayers(players);
			if (players.Count() > 0)
				Class.CastTo(m_Player, players[0]);
			m_Waited++;
			if (!m_Player)
			{{
				if (m_Waited >= {player_wait})
					FailRest("no player joined within {player_wait} s");
				return;
			}}
		}}
		if (m_Settled < {settle})
		{{
			m_Settled++;
			if (m_Settled == {settle})
				Strip();
			return;
		}}
		if (m_Next >= m_Ids.Count())
		{{
			Finish();
			return;
		}}
		int i = m_Next;
		m_Next++;
		string reason = RunCheck(m_Items[i], m_Actions[i], m_With[i]);
		if (reason == "")
			Print("[AZ-BEHAVIOR] PASS " + m_Ids[i]);
		else
			Print("[AZ-BEHAVIOR] FAIL " + m_Ids[i] + " " + reason);
	}}

	void FailRest(string reason)
	{{
		while (m_Next < m_Ids.Count())
		{{
			Print("[AZ-BEHAVIOR] FAIL " + m_Ids[m_Next] + " " + reason);
			m_Next++;
		}}
		Finish();
	}}

	void Finish()
	{{
		Print("[AZ-BEHAVIOR] DONE");
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(Tick);
	}}

	// Empty hands and free every clothing slot, so hands and wear checks start clean.
	void Strip()
	{{
		EntityAI held = m_Player.GetHumanInventory().GetEntityInHands();
		if (held)
			GetGame().ObjectDelete(held);
		for (int a = m_Player.GetInventory().AttachmentCount() - 1; a >= 0; a--)
		{{
			EntityAI worn = m_Player.GetInventory().GetAttachmentFromIndex(a);
			if (worn)
				GetGame().ObjectDelete(worn);
		}}
	}}

	bool InConfig(string item)
	{{
		return GetGame().ConfigIsExisting("CfgVehicles " + item) || GetGame().ConfigIsExisting("CfgWeapons " + item) || GetGame().ConfigIsExisting("CfgMagazines " + item);
	}}

	EntityAI SpawnNear(string item)
	{{
		EntityAI ent;
		vector pos = m_Player.GetPosition() + "1.5 0 0";
		Class.CastTo(ent, GetGame().CreateObjectEx(item, pos, ECE_PLACE_ON_SURFACE));
		return ent;
	}}

	string RunCheck(string item, string action, string other)
	{{
		if (!InConfig(item))
			return "no config class " + item + " in CfgVehicles, CfgWeapons or CfgMagazines";
		if (other != "" && !InConfig(other))
			return "no config class " + other + " in CfgVehicles, CfgWeapons or CfgMagazines";
		if (action == "hands")
			return InHands(item);
		if (action == "wear")
			return Wear(item);
		EntityAI ent = SpawnNear(item);
		if (!ent)
			return item + " was not created by CreateObjectEx";
		string reason = "";
		if (action == "attach" && !ent.GetInventory().CreateAttachment(other))
			reason = other + " did not attach to " + item;
		if (action == "cargo" && !ent.GetInventory().CreateEntityInCargo(other))
			reason = other + " did not fit in the cargo of " + item;
		GetGame().ObjectDelete(ent);
		return reason;
	}}

	string InHands(string item)
	{{
		EntityAI held = m_Player.GetHumanInventory().CreateInHands(item);
		if (!held)
			return item + " was not created in the player's hands";
		GetGame().ObjectDelete(held);
		return "";
	}}

	string Wear(string item)
	{{
		EntityAI probe = SpawnNear(item);
		if (!probe)
			return item + " was not created by CreateObjectEx";
		int slot = InventorySlots.INVALID;
		for (int s = 0; s < probe.GetInventory().GetSlotIdCount(); s++)
		{{
			if (m_Player.GetInventory().HasAttachmentSlot(probe.GetInventory().GetSlotId(s)))
			{{
				slot = probe.GetInventory().GetSlotId(s);
				break;
			}}
		}}
		GetGame().ObjectDelete(probe);
		if (slot == InventorySlots.INVALID)
			return item + " has no inventorySlot the player can wear";
		EntityAI worn = m_Player.GetInventory().CreateAttachmentEx(item, slot);
		if (!worn)
			return item + " could not be worn in slot " + InventorySlots.GetSlotName(slot);
		GetGame().ObjectDelete(worn);
		return "";
	}}
}};
{end}
"""


class BehaviorError(ValueError):
    """A checks file, mission or instance the behavior gate cannot use (gate exit 2)."""


# --- checks file -------------------------------------------------------------------

def default_checks_path(project_dir: Path, mod: str) -> Path:
    """Where dayz-mod-architect writes the checks: output/<ModName>-plan/behavior-checks.json."""
    return project_dir / "output" / f"{mod}-plan" / CHECKS_FILENAME


def load_checks(path: Path) -> list[dict]:
    if not path.is_file():
        raise BehaviorError(f"checks file not found: {path}. dayz-mod-architect writes it with the plan; or pass --checks.")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise BehaviorError(f"{path.name} is not valid JSON: {e}") from None
    return validate_checks(data, path.name)


def validate_checks(data: object, where: str = "checks") -> list[dict]:
    """The checks list, or BehaviorError naming the first bad entry."""
    if not isinstance(data, dict) or set(data) - FILE_KEYS:
        raise BehaviorError(f'{where}: expected an object with "checks" (and optionally "mod")')
    checks = data.get("checks")
    if not isinstance(checks, list) or not checks:
        raise BehaviorError(f'{where}: "checks" must be a non-empty list')
    seen: set[str] = set()
    for n, c in enumerate(checks, 1):
        label = f"{where} check {n}"
        if not isinstance(c, dict):
            raise BehaviorError(f"{label}: expected an object")
        extra = set(c) - CHECK_KEYS
        if extra:
            raise BehaviorError(f"{label}: unknown keys {sorted(extra)}; allowed {sorted(CHECK_KEYS)}")
        cid = c.get("id")
        if not isinstance(cid, str) or not ID_RE.match(cid):
            raise BehaviorError(f"{label}: id must be letters, digits, '_', '.' or '-' (no spaces), got {cid!r}")
        if cid in seen:
            raise BehaviorError(f"{label}: duplicate id {cid!r}")
        seen.add(cid)
        if not isinstance(c.get("feature"), str) or not c["feature"].strip():
            raise BehaviorError(f"{label} ({cid}): feature must name the feature the check proves")
        if c.get("action") not in ACTIONS:
            raise BehaviorError(f"{label} ({cid}): action must be one of {sorted(ACTIONS)}, got {c.get('action')!r}")
        for key in ("item", "with") if ACTIONS[c["action"]] else ("item",):
            if not isinstance(c.get(key), str) or not CLASS_RE.match(c[key]):
                raise BehaviorError(f"{label} ({cid}): {key} must be a config class name, got {c.get(key)!r}")
        if not ACTIONS[c["action"]] and "with" in c:
            raise BehaviorError(f"{label} ({cid}): action {c['action']!r} takes no 'with' class")
    return checks


# --- injector ----------------------------------------------------------------------

def render_script(checks: list[dict], newline: str = "\n") -> str:
    adds = "\n".join(
        f'\t\ts_Test.Add("{c["id"]}", "{c["item"]}", "{c["action"]}", "{c.get("with", "")}");' for c in checks
    )
    text = SCRIPT.format(begin=MARK_BEGIN, end=MARK_END, adds=adds, player_wait=PLAYER_WAIT_S, settle=SETTLE_S)
    return text.replace("\n", newline)


def _mask(text: str) -> str:
    """text with comments and string literals blanked (same length), so braces in them don't count."""
    return re.sub(
        r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"',
        lambda m: re.sub(r"[^\n]", " ", m.group(0)),
        text,
        flags=re.DOTALL,
    )


def inject(init_text: str, checks: list[dict]) -> str:
    """init.c with the test class in front and a Start() call at the end of main()."""
    if MARK_BEGIN in init_text:
        raise BehaviorError("init.c already holds the behavior test mission; copy from the original instance")
    masked = _mask(init_text)
    m = re.search(r"\bvoid\s+main\s*\(\s*\)\s*\{", masked)
    if m is None:
        raise BehaviorError("init.c has no void main() to start the behavior test from")
    depth, close = 0, None
    for i in range(m.end() - 1, len(masked)):
        if masked[i] == "{":
            depth += 1
        elif masked[i] == "}":
            depth -= 1
            if depth == 0:
                close = i
                break
    if close is None:
        raise BehaviorError("init.c: main() has no closing brace")
    nl = "\r\n" if "\r\n" in init_text else "\n"
    head = init_text[:close]
    if not head.endswith("\n"):
        head += nl
    return render_script(checks, nl) + nl + head + "\t" + START_CALL + nl + init_text[close:]


def _remove_tree(path: Path) -> None:
    """Delete path; a junction or symlink is unlinked without touching its target."""
    if h.is_link(path):
        try:
            path.rmdir()  # a junction
        except OSError:
            path.unlink()  # a symlink
    elif path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def check_instance(instance: str) -> str:
    """Refuse an instance that is not one folder name directly under .server/ (same rule as /dayz-add-server)."""
    if instance in ("", ".", "..") or any(c in instance for c in '/\\:*?"<>|'):
        raise BehaviorError(
            f"{instance!r} is not a valid instance name: use a single folder name "
            "(no path separators, drive letters, '..', or the characters * ? \" < > |)"
        )
    return instance


def make_junction(link: Path, target: Path) -> None:
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, text=True)
    if result.returncode != 0:
        raise BehaviorError(f"could not create junction {link}: {(result.stderr or result.stdout).strip()}")


# Server profile files that are logs or dumps, not settings: the gate reads the
# copy's own logs, so the instance's must not be copied in with the settings.
PROFILE_LOG_SUFFIXES = (".log", ".rpt", ".mdmp", ".bidmp")


def _profile_logs(_folder: str, names: list[str]) -> set[str]:
    """shutil.copytree ignore: the logs and crash dumps among `names`."""
    return {n for n in names if n.lower().endswith(PROFILE_LOG_SUFFIXES) or n.lower().startswith("crash")}


def prepare_instance(project_dir: Path, instance: str, checks: list[dict]) -> dict:
    """Copy .server/<instance>/ to .server/<instance>-behavior/ with the test mission injected.

    The copy gets serverDZ.cfg, mission/ (without storage_* persistence, so the
    test world starts fresh), the <template>/ junction /dayz-launch-test needs
    and the instance's Profiles/ settings: every file and folder there except
    logs and crash dumps (PROFILE_LOG_SUFFIXES and crash*), so a mod or CF/COT
    that reads its config from the server profile behaves as on the instance.
    A previous copy is replaced; the copy's own Profiles/ logs stay, and its
    settings files are overwritten by the instance's.
    """
    check_instance(instance)
    if instance.endswith(INSTANCE_SUFFIX):
        raise BehaviorError(f"pass the original instance, not the behavior copy {instance!r}")
    server = project_dir / ".server"
    src = server / instance
    cfg = src / "serverDZ.cfg"
    init = src / "mission" / "init.c"
    if not cfg.is_file() or not init.is_file():
        raise BehaviorError(f"instance {instance!r} is not set up (no serverDZ.cfg or mission/init.c). Run /dayz-add-server {instance}")
    match = TEMPLATE_RE.search(cfg.read_text(encoding="utf-8", errors="replace"))
    if match is None:
        raise BehaviorError(f'{cfg} has no template = "..."; line. Run /dayz-add-server {instance}')
    template = match.group(1)
    if template in (".", "..") or not TEMPLATE_NAME_RE.fullmatch(template):
        raise BehaviorError(f"{cfg} has template = {template!r}; it must be one mission folder name such as dayzOffline.chernarusplus")

    name = instance + INSTANCE_SUFFIX
    dst = server / name
    mission = dst / "mission"
    link = dst / template
    # link may already be a junction, so check its own path, not where it points.
    if dst.resolve().parent != server.resolve() or Path(os.path.normpath(dst.resolve() / template)).parent != dst.resolve():
        raise BehaviorError(f"refusing to write outside {server}: instance {instance!r}, template {template!r}")
    dst.mkdir(parents=True, exist_ok=True)
    _remove_tree(link)
    _remove_tree(mission)
    shutil.copytree(src / "mission", mission, ignore=shutil.ignore_patterns("storage_*"))
    text = (mission / "init.c").read_bytes().decode("utf-8-sig")
    (mission / "init.c").write_bytes(inject(text, checks).encode("utf-8"))
    shutil.copy2(cfg, dst / "serverDZ.cfg")
    make_junction(link, mission)
    if (src / "Profiles").is_dir():
        shutil.copytree(src / "Profiles", dst / "Profiles", ignore=_profile_logs, dirs_exist_ok=True)
    else:
        (dst / "Profiles").mkdir(exist_ok=True)
    return {"instance": name, "dir": dst, "init": mission / "init.c", "template": template}


# --- parser ------------------------------------------------------------------------

def parse_lines(lines: Iterable[tuple[Path, int, str]], checks: list[dict]) -> dict:
    """Per-check results from [AZ-BEHAVIOR] lines, in the checks file's order.

    A START line begins a new run and clears earlier results, so the newest run
    in the logs wins. A check with no result line fails.
    """
    ids = {c["id"] for c in checks}
    found: dict[str, dict] = {}
    started = done = False
    unexpected: list[str] = []
    for path, number, text in lines:
        m = RESULT_RE.search(text)
        if m is None:
            continue
        kind, ident, rest = m.groups()
        if kind == "START":
            found, started, done, unexpected = {}, True, False, []
        elif kind == "DONE":
            done = True
        elif ident not in ids:
            unexpected.append(ident)
        else:
            reason = (rest or "no reason given") if kind == "FAIL" else ""
            found[ident] = {"status": kind, "reason": reason, "file": path, "line": number, "text": text.strip()}
    results = []
    for c in checks:
        r = found.get(c["id"])
        if r is None:
            why = ("the test mission never started (no [AZ-BEHAVIOR] START line in the logs)" if not started
                   else "the test mission stopped before this check; look for a script error near it")
            r = {"status": "FAIL", "reason": f"no result line: {why}", "file": None, "line": None, "text": None}
        results.append({"id": c["id"], "feature": c["feature"], "item": c["item"], "action": c["action"], **r})
    return {"started": started, "done": done, "results": results, "unexpected": unexpected}


def read_logs(files: list[Path]) -> list[tuple[Path, int, str]]:
    lines = []
    for f in files:
        for number, text in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            lines.append((f, number, text))
    return lines


def server_script_logs(project_dir: Path, instance: str) -> list[Path]:
    """The behavior copy's server script logs, oldest first (the test mission prints there)."""
    check_instance(instance)
    profiles = project_dir / ".server" / instance / "Profiles"
    return sorted(profiles.glob("script*.log")) if profiles.is_dir() else []
