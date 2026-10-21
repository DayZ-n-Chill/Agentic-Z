"""dayz-conflict-check: find class name and path collisions with other mods.

  conflict_check.py <ModName> [--against MOD ...] [--all] [--json]
  conflict_check.py --mod-dir <folder> [--against MOD ...] [--json]
  conflict_check.py <ModName> --ingame [--server <instance>] [--port N]

Compares workspace/<ModName>/ with other mods under P:\\Mods\\ (by default CF,
COT and Expansion, when they are there). It reads only unpacked config.cpp
and .c files and the header of each .pbo: the $PBOPREFIX$ and the file list.
It never extracts a PBO, never reads a packed file's data and never copies
another mod's files or code; the report holds class names and paths only.

Checks: the same $PBOPREFIX$ or one nested in the other, the same game path
shipped twice, the same CfgPatches class, the same config class defined in
both, the same script class declared in both, and modded classes both mods
override. --ingame then runs /dayz-gate ingame with those mods loaded.

The first output line is the verdict: PASS (exit 0, warnings allowed), FAIL
(exit 1, at least one error, or the in-game gate failed) or ERROR (exit 2:
bad arguments, no project, no mod folder, nothing to compare). See SKILL.md.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

HERE = Path(__file__).resolve().parent
SKILLS_DIR = HERE.parent
sys.path.insert(0, str(SKILLS_DIR / "_shared"))
import skill_helpers as h  # noqa: E402

GATE = SKILLS_DIR / "dayz-gate" / "gate.py"
P_DRIVE = Path("P:\\")
ERROR, WARNING = "error", "warning"

# rule -> (severity, owner, fix)
RULES = {
    "prefix-same": (ERROR, "dayz-config-specialist",
                    "Give $PBOPREFIX$ a folder only your mod uses, usually the mod name, and move the files with it."),
    "prefix-nested": (WARNING, "dayz-config-specialist",
                      "Move $PBOPREFIX$ out of the other mod's folder so the two can never ship the same path."),
    "path-collision": (ERROR, "dayz-config-specialist",
                       "Rename or move the file. Two mods shipping one game path means only one of them is loaded."),
    "cfgpatches-collision": (ERROR, "dayz-config-specialist",
                             "Rename the CfgPatches class to a name only your mod uses, such as <ModName>_<Part>."),
    "class-collision": (ERROR, "dayz-config-specialist",
                        "Rename your class, or, if you mean to change theirs, add their CfgPatches class to requiredAddons[]."),
    "class-override": (WARNING, "dayz-config-specialist",
                       "You change their class on purpose (it is in requiredAddons[]). Check that both mods still work."),
    "vanilla-class-overlap": (WARNING, "dayz-config-specialist",
                              "Both mods change this vanilla class; the one loaded last wins each property it sets."),
    "script-class-collision": (ERROR, "dayz-script-specialist",
                               "Rename your class or enum. Two declarations of one name stop the scripts compiling."),
    "modded-class-overlap": (WARNING, "dayz-script-specialist",
                             "Both mods override this class. Call super in every override so neither mod loses its code."),
    "script-name-match": (WARNING, "dayz-script-specialist",
                          "Their PBO ships a script file with this class's name, so they may declare or mod it too. Test with --ingame."),
}

SKIP_DIRS = {"__pycache__", "node_modules"}
# Files every addon has at its root; they never reach the game path table.
NOT_GAME_PATHS = {"config.cpp", "config.bin", "$pboprefix$", "$prefix$", "$pboprefix$.txt"}

COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
STRING_RE = re.compile(r'"(?:[^"\\\n]|\\.|"")*"')
CONFIG_TOKEN_RE = re.compile(r"\bclass\s+(\w+)\s*(?::\s*\w+\s*)?([{;])|[{}]")
REQUIRED_RE = re.compile(r"\brequiredAddons\s*\[\s*\]\s*\+?=\s*\{([^}]*)\}", re.IGNORECASE)
SCRIPT_DECL_RE = re.compile(r"^[ \t]*(?:(?:sealed|static)\s+)*(modded\s+)?(class|enum)\s+(\w+)\b(?![ \t]*;)", re.MULTILINE)


class ConflictError(Exception):
    """The check cannot run (exit 2); not a verdict on the mod."""


# --- what one mod declares ----------------------------------------------------

@dataclass
class Facts:
    """Names and paths one mod declares, each with where it was seen. Keys are lowercased."""

    name: str
    prefixes: list[tuple[str, str]] = field(default_factory=list)          # (prefix, where)
    paths: dict[str, tuple[str, str]] = field(default_factory=dict)        # path -> (path, where)
    patches: dict[str, tuple[str, str]] = field(default_factory=dict)      # name -> (name, where)
    classes: dict[tuple[str, str], tuple[str, str]] = field(default_factory=dict)  # (section, name) -> (name, where)
    script_classes: dict[str, tuple[str, str]] = field(default_factory=dict)
    modded: dict[str, tuple[str, str]] = field(default_factory=dict)
    script_files: dict[str, tuple[str, str]] = field(default_factory=dict)  # stem -> (path, where), from PBO headers
    required: set[str] = field(default_factory=set)
    pbos: int = 0
    unpacked: int = 0
    unreadable: list[str] = field(default_factory=list)


def norm_path(path: str) -> str:
    return path.replace("/", "\\").strip("\\").lower()


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def blank(match: re.Match) -> str:
    """Replace a comment or string with spaces, keeping its line breaks."""
    return re.sub(r"[^\n]", " ", match.group(0))


def scan_config(text: str, where: str, facts: Facts) -> None:
    """Record CfgPatches classes, class definitions one level inside each Cfg section, and requiredAddons."""
    for m in REQUIRED_RE.finditer(COMMENT_RE.sub(blank, text)):
        facts.required |= {v.lower() for v in re.findall(r'"([^"]+)"', m.group(1))}
    clean = STRING_RE.sub(blank, COMMENT_RE.sub(blank, text))
    clean = re.sub(r"(?m)^[ \t]*#[^\n]*", blank, clean)  # preprocessor lines
    stack: list[Optional[str]] = []
    for m in CONFIG_TOKEN_RE.finditer(clean):
        token = m.group(0)
        if token == "}":
            if stack:
                stack.pop()
            continue
        if token == "{":
            stack.append(None)  # an array or other body that is not a class
            continue
        name, end = m.group(1), m.group(2)
        if end == "{":
            if len(stack) == 1 and stack[0]:
                section = stack[0].lower()
                at = f"{where}:{line_of(clean, m.start())}"
                if section == "cfgpatches":
                    facts.patches.setdefault(name.lower(), (name, at))
                else:
                    facts.classes.setdefault((section, name.lower()), (name, at))
            stack.append(name)


def scan_script(text: str, where: str, facts: Facts) -> None:
    """Record the class and enum names a .c file declares. Only names are kept."""
    clean = STRING_RE.sub(blank, COMMENT_RE.sub(blank, text))
    for m in SCRIPT_DECL_RE.finditer(clean):
        modded, name = m.group(1), m.group(3)
        target = facts.modded if modded else facts.script_classes
        target.setdefault(name.lower(), (name, f"{where}:{line_of(clean, m.start(3))}"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def scan_unpacked(root: Path, facts: Facts, display: Callable[[Path], str]) -> None:
    """Read an unpacked mod or addon tree: $PBOPREFIX$ files, config.cpp files and .c files."""
    files = [p for p in root.rglob("*") if p.is_file() and not any(
        part.startswith(".") or part in SKIP_DIRS for part in p.relative_to(root).parts)]
    prefix_files = [p for p in files if p.name.lower() == "$pboprefix$"]
    addon_roots: dict[Path, Optional[str]] = {}
    for pf in prefix_files:
        lines = read_text(pf).strip().splitlines()
        prefix = lines[0].strip() if lines else ""
        if prefix.lower().startswith("prefix="):  # the key=value form some tools write
            prefix = prefix.split("=", 1)[1].strip()
        if prefix:
            addon_roots[pf.parent] = prefix
            facts.prefixes.append((prefix, display(pf)))
    if not addon_roots:
        addon_roots[root] = None
    facts.unpacked += len(addon_roots)
    by_depth = sorted(addon_roots, key=lambda p: len(p.parts), reverse=True)
    for path in files:
        low = path.name.lower()
        if low == "config.cpp":
            scan_config(read_text(path), display(path), facts)
        elif path.suffix.lower() == ".c":
            scan_script(read_text(path), display(path), facts)
        owner = next((r for r in by_depth if r == path.parent or r in path.parents), None)
        prefix = addon_roots.get(owner) if owner else None
        if prefix and low not in NOT_GAME_PATHS:
            game = norm_path(prefix) + "\\" + norm_path(path.relative_to(owner).as_posix())
            facts.paths.setdefault(game, (game, display(path)))


# --- PBO headers --------------------------------------------------------------

VERS = 0x56657273
MAX_ENTRIES = 200_000


def _cstr(f) -> str:
    out = bytearray()
    while True:
        c = f.read(1)
        if not c or c == b"\0":
            return out.decode("utf-8", errors="replace")
        out += c


def read_pbo_header(path: Path) -> tuple[dict[str, str], list[str]]:
    """The header properties (prefix and others) and the file names of a .pbo.

    Reads the header only: the entry table ends where the packed data starts,
    and nothing after it is read.
    """
    props: dict[str, str] = {}
    names: list[str] = []
    with path.open("rb") as f:
        for _ in range(MAX_ENTRIES):
            name = _cstr(f)
            raw = f.read(20)
            if len(raw) < 20:
                raise ValueError("header ends early")
            method = struct.unpack("<5I", raw)[0]
            if not name and method == VERS:
                while True:
                    key = _cstr(f)
                    if not key:
                        break
                    props[key.lower()] = _cstr(f)
                continue
            if not name:
                return props, names
            names.append(name)
    raise ValueError("header has no end")


def scan_pbo(path: Path, facts: Facts, display: Callable[[Path], str]) -> None:
    where = display(path)
    try:
        props, names = read_pbo_header(path)
    except (OSError, ValueError, struct.error) as e:
        facts.unreadable.append(f"{where}: {e}")
        return
    facts.pbos += 1
    prefix = props.get("prefix", "").strip()
    if prefix:
        facts.prefixes.append((prefix, where))
    for name in names:
        rel = norm_path(name)
        base = rel.rsplit("\\", 1)[-1]
        if prefix and base not in NOT_GAME_PATHS:
            game = norm_path(prefix) + "\\" + rel
            facts.paths.setdefault(game, (game, f"{where} > {name}"))
        if base.endswith(".c"):
            facts.script_files.setdefault(base[:-2], (name, where))


def find_addons_dir(mod_dir: Path) -> Optional[Path]:
    return next((p for p in mod_dir.iterdir() if p.is_dir() and p.name.lower() == "addons"), None)


def read_mod(mod_dir: Path, name: str, display: Callable[[Path], str]) -> Facts:
    """An @mod folder (Addons\\*.pbo and unpacked addon folders) or an unpacked mod tree."""
    facts = Facts(name)
    addons = find_addons_dir(mod_dir)
    if addons is None:
        scan_unpacked(mod_dir, facts, display)
        return facts
    for entry in sorted(addons.iterdir()):
        if entry.is_file() and entry.suffix.lower() == ".pbo":
            scan_pbo(entry, facts, display)
        elif entry.is_dir() and any(entry.rglob("config.cpp")):
            scan_unpacked(entry, facts, display)
    if mod_dir.joinpath("config.cpp").is_file():  # a source tree that also holds prebuilt PBOs
        scan_unpacked(mod_dir, facts, display)
    return facts


# --- vanilla names ------------------------------------------------------------

class Vanilla:
    """Class names vanilla DayZ declares, read lazily from the unpacked data on P:\\."""

    def __init__(self, root: Optional[Path]):
        self.root = root
        self._config: Optional[set[str]] = None
        self._script: Optional[set[str]] = None

    @property
    def available(self) -> bool:
        return self.root is not None and (self.root / "DZ").is_dir()

    def config_class(self, name: str) -> bool:
        if self._config is None:
            facts = Facts("vanilla")
            if self.available:
                for cfg in [*(self.root / "DZ").rglob("config.cpp"), self.root / "scripts" / "config.cpp"]:
                    if cfg.is_file():
                        scan_config(read_text(cfg), str(cfg), facts)
            self._config = {n for _, n in facts.classes}
        return name.lower() in self._config

    def script_class(self, name: str) -> bool:
        if self._script is None:
            facts = Facts("vanilla")
            scripts = self.root / "scripts" if self.root else None
            if scripts is not None and scripts.is_dir():
                for c in scripts.rglob("*.c"):
                    scan_script(read_text(c), str(c), facts)
            self._script = set(facts.script_classes)
        return name.lower() in self._script


# --- which mods to compare with -----------------------------------------------

def default_targets(mods_root: Path) -> list[Path]:
    """CF, COT and Expansion, in load order, when they are under mods_root.

    The Expansion bundle holds every Expansion part, so when it is there the
    parts are not added a second time.
    """
    found = {p.name.lower(): p for p in mods_root.iterdir() if p.is_dir()} if mods_root.is_dir() else {}
    out = [found[n] for n in ("@cf", "@community-online-tools") if n in found]
    if "@dayz-expansion-bundle" in found:
        return out + [found["@dayz-expansion-bundle"]]
    parts = sorted((p for n, p in found.items() if n.startswith("@dayz-expansion")),
                   key=lambda p: (p.name.lower() != "@dayz-expansion-core", p.name.lower()))
    return out + parts


def resolve_targets(against: list[str], scan_all: bool, mods_root: Path, mod: str) -> list[Path]:
    if scan_all:
        targets = sorted(p for p in mods_root.iterdir() if p.is_dir() and p.name.startswith("@")) if mods_root.is_dir() else []
    elif against:
        targets = []
        for item in against:
            path = Path(item)
            if not path.is_absolute():
                path = mods_root / (item if item.startswith("@") else f"@{item}")
            if not path.is_dir():
                raise ConflictError(f"{item}: no folder at {path}")
            targets.append(path)
    else:
        targets = default_targets(mods_root)
    own = {mod.lower(), f"@{mod.lower()}"}
    return [t for t in targets if t.name.lower() not in own]


# --- comparison ---------------------------------------------------------------

def prefix_contains(outer: str, inner: str) -> bool:
    return inner.startswith(outer + "\\")


def compare(ours: Facts, theirs: Facts, vanilla: Vanilla) -> list[dict]:
    out: list[dict] = []

    def add(rule: str, where: str, message: str, other: str) -> None:
        severity, owner, fix = RULES[rule]
        out.append({"rule": rule, "severity": severity, "mod": theirs.name, "where": where,
                    "other": other, "message": message, "owner": owner, "fix": fix})

    for prefix, where in ours.prefixes:
        p = norm_path(prefix)
        for their_prefix, their_where in theirs.prefixes:
            q = norm_path(their_prefix)
            if p == q:
                add("prefix-same", where, f"$PBOPREFIX$ {prefix} is also the prefix of {theirs.name}.", their_where)
            elif prefix_contains(p, q) or prefix_contains(q, p):
                add("prefix-nested", where, f"$PBOPREFIX$ {prefix} and {theirs.name}'s {their_prefix} sit one inside the other.", their_where)
    for key, (path, where) in ours.paths.items():
        if key in theirs.paths:
            add("path-collision", where, f"{path} is also shipped by {theirs.name}.", theirs.paths[key][1])
    for key, (name, where) in ours.patches.items():
        if key in theirs.patches:
            add("cfgpatches-collision", where, f"CfgPatches class {name} is also declared by {theirs.name}.", theirs.patches[key][1])
    requires_them = bool(ours.required & set(theirs.patches))
    for (section, key), (name, where) in ours.classes.items():
        if (section, key) not in theirs.classes:
            continue
        other = theirs.classes[(section, key)][1]
        if vanilla.config_class(name):
            add("vanilla-class-overlap", where, f"{name} is a vanilla class both you and {theirs.name} change.", other)
        elif requires_them:
            add("class-override", where, f"{name} is also defined by {theirs.name}, whose CfgPatches you require.", other)
        else:
            add("class-collision", where, f"{name} is also defined by {theirs.name} and you do not require it.", other)
    for key, (name, where) in ours.script_classes.items():
        if key in theirs.script_classes and not vanilla.script_class(name):
            add("script-class-collision", where, f"{name} is also declared by {theirs.name}.", theirs.script_classes[key][1])
    for key, (name, where) in ours.modded.items():
        if key in theirs.modded:
            add("modded-class-overlap", where, f"modded class {name} is also in {theirs.name}.", theirs.modded[key][1])
    for source in (ours.modded, ours.script_classes):
        for key, (name, where) in source.items():
            if key in theirs.script_files and key not in theirs.modded and key not in theirs.script_classes:
                path, pbo = theirs.script_files[key]
                add("script-name-match", where, f"{theirs.name} ships {path} in its PBO, a file named after {name}.", pbo)
    return out


# --- report -------------------------------------------------------------------

def check_mod(
    mod: str,
    mod_dir: Path,
    targets: list[Path],
    display_root: Optional[Path] = None,
    vanilla_root: Optional[Path] = None,
) -> dict:
    """Compare one mod folder with each target mod folder and return the report."""
    if not mod_dir.is_dir():
        raise ConflictError(f"{mod_dir} not found")
    if not targets:
        raise ConflictError("no mods to compare with: none of CF, COT or Expansion is under the mods folder; pass --against")
    root = display_root or mod_dir.parent

    def display(path: Path) -> str:
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return str(path)

    ours = read_mod(mod_dir, mod, display)
    vanilla = Vanilla(vanilla_root if vanilla_root is not None else P_DRIVE)
    findings: list[dict] = []
    scanned = []
    for target in targets:
        theirs = read_mod(target, target.name, lambda p, t=target: f"{t.name}/{p.relative_to(t).as_posix()}")
        findings += compare(ours, theirs, vanilla)
        scanned.append({"mod": target.name, "pbo_headers": theirs.pbos, "unpacked": theirs.unpacked,
                        "unreadable": theirs.unreadable})
    findings.sort(key=lambda f: (f["severity"] != ERROR, f["where"], f["rule"]))
    errors = sum(f["severity"] == ERROR for f in findings)
    report = {
        "verdict": "FAIL" if errors else "PASS",
        "mod": mod,
        "mod_dir": str(mod_dir),
        "errors": errors,
        "warnings": len(findings) - errors,
        "scanned": scanned,
        "findings": findings,
    }
    if any(s["pbo_headers"] and not s["unpacked"] for s in scanned):
        report["note"] = ("Packed mods were read from their PBO headers only: prefixes, paths and script file names. "
                          "Their config and script classes are not compared; --ingame checks those at run time.")
    if not vanilla.available:
        report.setdefault("note", "")
        report["note"] = (report["note"] + " P:\\DZ\\ is not mounted, so vanilla classes were not told apart.").strip()
    return report


def gate_command(mod: str, deps: list[str], server: str, port: int) -> list[str]:
    return [sys.executable, str(GATE), "ingame", mod, "--deps", *deps, "--server", server, "--port", str(port), "--json"]


def run_captured(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def add_ingame(report: dict, mod: str, targets: list[Path], server: str, port: int,
               run: Callable[[list[str]], tuple[int, str]]) -> None:
    """Run /dayz-gate ingame with the compared mods loaded, in the same order, and fold its verdict in."""
    deps = [t.name for t in targets]
    rc, output = run(gate_command(mod, deps, server, port))
    first, _, rest = output.partition("\n")
    try:
        gate = json.loads(rest)
    except json.JSONDecodeError:
        gate = {"verdict": "ERROR", "error": output.strip()[-2000:]}
    report["ingame"] = {"deps": deps, "server": server, "rc": rc, "verdict": first.strip() or "ERROR", "report": gate}
    if report["ingame"]["verdict"] != "PASS":
        report["verdict"] = "FAIL"


def render_text(report: dict) -> str:
    out = []
    for f in report["findings"]:
        out.append(f"- {f['where']}  {f['severity']} {f['rule']}: {f['message']}")
        out.append(f"    theirs: {f['other']}")
        out.append(f"    -> {f['owner']}: {f['fix']}")
    for s in report["scanned"]:
        extra = f", {len(s['unreadable'])} unreadable" if s["unreadable"] else ""
        out.append(f"  scanned {s['mod']}: {s['pbo_headers']} PBO header(s), {s['unpacked']} unpacked addon(s){extra}")
    if report.get("note"):
        out.append(f"  {report['note']}")
    out.append(f"  {report['errors']} error(s), {report['warnings']} warning(s)")
    if "ingame" in report:
        g = report["ingame"]
        out.append(f"  in-game gate on {g['server']} with {' '.join(g['deps'])}: {g['verdict']}")
        for f in g["report"].get("failures", []):
            where = f"{f.get('file')}:{f.get('line')}" if f.get("line") else f.get("file", "")
            out.append(f"- [{f.get('category', 'ingame')}] {where}  {f.get('text', '')}")
        if g["report"].get("error"):
            out.append(f"    {g['report']['error']}")
    return "\n".join(out)


def main(argv: Optional[list[str]] = None, run: Callable[[list[str]], tuple[int, str]] = run_captured) -> int:
    parser = argparse.ArgumentParser(description="Find class name and path collisions with other mods.")
    parser.add_argument("mod", nargs="?", help="Mod name under workspace/ in the project cached by /dayz-init.")
    parser.add_argument("--mod-dir", type=Path, help="Check this folder instead (its name is the mod name).")
    pick = parser.add_mutually_exclusive_group()
    pick.add_argument("--against", nargs="+", default=[], metavar="MOD",
                      help="Mods to compare with, in load order: names under the mods folder (CF or @CF) or folder paths.")
    pick.add_argument("--all", action="store_true", help="Compare with every @mod under the mods folder.")
    parser.add_argument("--mods-root", type=Path, default=P_DRIVE / "Mods", help="Folder holding the @mods (default P:\\Mods).")
    parser.add_argument("--ingame", action="store_true", help="Then run /dayz-gate ingame with the compared mods loaded.")
    parser.add_argument("--server", default="chernarus", help="--ingame: server instance (default chernarus).")
    parser.add_argument("--port", type=int, default=2302, help="--ingame: server port (default 2302).")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON after the verdict line.")
    try:
        args = parser.parse_args(argv)
        if not args.mod and not args.mod_dir:
            parser.error("give a <ModName> or --mod-dir")
        if args.ingame and not args.mod:
            parser.error("--ingame needs the <ModName> of a mod in the project")
    except SystemExit as e:
        return 0 if e.code == 0 else 2

    try:
        if args.mod_dir and not args.ingame:
            mod_dir = args.mod_dir.resolve()
            mod = args.mod or mod_dir.name
            display_root = Path.cwd()
        else:
            project_dir = h.resolve_project_dir()
            mod = args.mod
            mod_dir = args.mod_dir.resolve() if args.mod_dir else project_dir / "workspace" / mod
            display_root = project_dir
        targets = resolve_targets(args.against, args.all, args.mods_root, mod)
        report = check_mod(mod, mod_dir, targets, display_root)
        if args.ingame:
            add_ingame(report, mod, targets, args.server, args.port, run)
    except SystemExit:  # resolve_project_dir already printed why on stderr
        return _error("no usable project: run /dayz-init, or pass --mod-dir", args.json)
    except (ConflictError, OSError, ValueError) as e:
        return _error(str(e), args.json)
    print(report["verdict"])
    print(json.dumps(report, indent=2) if args.json else render_text(report))
    return 0 if report["verdict"] == "PASS" else 1


def _error(message: str, as_json: bool) -> int:
    print("ERROR")
    print(json.dumps({"verdict": "ERROR", "error": message}, indent=2) if as_json else f"  {message}")
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
