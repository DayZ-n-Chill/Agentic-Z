"""dayz-lint: find errors that would stop a mod loading, before it is packed.

  lint.py <ModName> [--json]
  lint.py --mod-dir <folder> [--json]

Checks workspace/<ModName>/ without DayZ, AddonBuilder or any process:
config.cpp syntax, CfgPatches and its arrays, requiredAddons names,
$PBOPREFIX$ and its P:\\ link, CfgMods script modules against the scripts/
folders, modded classes with an extends clause, files the config and the
.rvmat materials point at, and file suffixes.

The first output line is the verdict: PASS (exit 0, warnings allowed), FAIL
(exit 1, at least one error) or ERROR (exit 2: bad arguments, no project, no
mod folder). Every finding carries file:line and its triage from
dayz-gate/known-errors.json (owner agent and fix). /dayz-gate build and
/dayz-build-pbo call lint_mod() first and stop on errors. See SKILL.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
SKILLS_DIR = HERE.parent
REPO = SKILLS_DIR.parents[1]
sys.path.insert(0, str(SKILLS_DIR / "_shared"))
import skill_helpers as h  # noqa: E402

# The config grammar of the PostToolUse syntax hook. Imported, not loaded by path:
# its dataclasses need the module registered in sys.modules.
sys.path.insert(0, str(REPO / "hooks"))
import edit_check  # noqa: E402

triage = h.load_module("dayz_lint_triage", SKILLS_DIR / "dayz-gate" / "triage.py")
pack_texture = h.load_module("dayz_lint_pack_texture", SKILLS_DIR / "dayz-pack-texture" / "pack_texture.py")

P_DRIVE = Path("P:\\")

ERROR, WARNING = "error", "warning"

# Every rule lint can report; each has a "lint-<rule>" entry in dayz-gate/known-errors.json.
RULES = (
    "config-missing", "config-syntax", "cfgpatches-missing", "cfgpatches-empty", "cfgpatches-field",
    "cfgpatches-field-missing", "required-addons-missing", "required-addon-name", "required-addon-duplicate", "pboprefix-missing", "pboprefix-mismatch",
    "p-link", "p-not-mounted", "script-module-path", "script-module-layer", "script-module-unlisted",
    "modded-class-extends", "script-suffix", "missing-model", "missing-texture", "missing-file",
    "absolute-path", "texture-format", "texture-suffix", "rvmat-syntax",
)

# CfgMods > <mod> > defs > <module class> and the scripts/ layer each one compiles.
# Vanilla: P:\DZ\data_sakhal\config.cpp lists worldScriptModule -> DZ/data_sakhal/scripts/4_World.
MODULE_LAYERS = {
    "enginescriptmodule": "1_Core",
    "gamelibscriptmodule": "2_GameLib",
    "gamescriptmodule": "3_Game",
    "worldscriptmodule": "4_World",
    "missionscriptmodule": "5_Mission",
}
LAYER_MODULE = {layer.lower(): name for name, layer in MODULE_LAYERS.items()}
MODULE_SPELLING = {
    "enginescriptmodule": "engineScriptModule",
    "gamelibscriptmodule": "gameLibScriptModule",
    "gamescriptmodule": "gameScriptModule",
    "worldscriptmodule": "worldScriptModule",
    "missionscriptmodule": "missionScriptModule",
}

# String values that name a file the engine loads at run time.
FILE_EXTS = {
    ".p3d", ".paa", ".edds", ".rvmat", ".layout", ".imageset", ".styles", ".ogg", ".wss",
    ".emat", ".ptc", ".anm", ".rtm", ".bisurf", ".png", ".tga", ".jpg", ".jpeg", ".dds", ".bmp",
}
# Tier 2 conventions/assets.md: textures are .paa only.
UNPACKED_IMAGE_EXTS = {".png", ".tga", ".jpg", ".jpeg", ".dds", ".bmp"}
# Strings checked for a texture role suffix (Tier 2 conventions/assets.md).
ROLE_SUFFIX_PROPS = re.compile(r"(?i)^(?:hiddenSelectionsTextures|texture)$")

MODDED_EXTENDS_RE = re.compile(r"^\s*modded\s+class\s+\w+\s*(?:extends|:)\s*\w+")
ADDON_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class LintError(Exception):
    """Lint cannot run (exit 2); not a verdict on the mod."""


# --- config tree --------------------------------------------------------------

class Node:
    """A class in config.cpp: its body's classes and properties."""

    def __init__(self, name: str, line: int):
        self.name = name
        self.line = line
        self.parent: Optional[str] = None  # the class after ':', when there is one
        self.classes: list[Node] = []
        # lower name -> (name, line, is_array, values: list[(text, line)])
        self.props: dict[str, tuple[str, int, bool, list[tuple[str, int]]]] = {}

    def child(self, name: str) -> Optional["Node"]:
        return next((c for c in self.classes if c.name.lower() == name.lower()), None)


def parse_tree(toks: list) -> Node:
    """Build the class tree from edit_check tokens. Only called on a file that passed the syntax check."""
    root = Node("", 0)
    stack = [root]
    i, n = 0, len(toks)

    def punct(k: int, text: str) -> bool:
        return k < n and toks[k].kind == "punct" and toks[k].text == text

    while i < n:
        tok = toks[i]
        if punct(i, "}"):
            if len(stack) > 1:
                stack.pop()
            i += 1
        elif tok.kind == "ident" and tok.text == "class" and i + 1 < n:
            name = toks[i + 1]
            j = i + 2
            parent = None
            if punct(j, ":"):
                parent = toks[j + 1].text if j + 1 < n else None
                j += 2
            if punct(j, "{"):
                node = Node(name.text, name.line)
                node.parent = parent
                stack[-1].classes.append(node)
                stack.append(node)
            i = j + 1
        elif tok.kind == "ident" and (punct(i + 1, "=") or punct(i + 1, "+=") or (punct(i + 1, "[") and punct(i + 2, "]"))):
            is_array = punct(i + 1, "[")
            j = i + (3 if is_array else 1)
            j += 1  # '=' or '+='
            values: list[tuple[str, int]] = []
            depth = 0
            while j < n:
                t = toks[j]
                if t.kind == "punct" and t.text == "{":
                    depth += 1
                elif t.kind == "punct" and t.text == "}":
                    depth -= 1
                    if depth <= 0:
                        j += 1
                        break
                elif t.kind == "punct" and t.text == ";" and depth == 0:
                    break
                elif t.kind in ("str", "ident", "num"):
                    values.append((unquote(t.text) if t.kind == "str" else t.text, t.line))
                j += 1
            stack[-1].props[tok.text.lower()] = (tok.text, tok.line, is_array, values)
            i = j
        else:
            i += 1
    return root


def unquote(text: str) -> str:
    return text[1:-1].replace('""', '"') if len(text) >= 2 else text


# --- the linter ---------------------------------------------------------------

class Lint:
    def __init__(self, mod: str, mod_dir: Path, display_root: Path, p_drive: Optional[Path], vanilla_root: Optional[Path]):
        self.mod = mod
        self.mod_dir = mod_dir
        self.display_root = display_root
        self.p_drive = p_drive
        self.vanilla_root = vanilla_root
        self.findings: list[dict] = []
        self.prefix = mod

    def add(self, rule: str, severity: str, path: Optional[Path], line: Optional[int], message: str) -> None:
        self.findings.append({
            "rule": rule,
            "severity": severity,
            "file": self.rel(path) if path is not None else self.rel(self.mod_dir),
            "line": line,
            "message": message,
            "text": f"[lint:{rule}] {message}",
        })

    def rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.display_root).as_posix()
        except ValueError:
            return path.as_posix()

    # entry point
    def run(self) -> Optional[str]:
        """Run every rule. Returns a note when there was nothing to lint."""
        cfg = self.mod_dir / "config.cpp"
        addons = self.mod_dir / "Addons"
        if not cfg.is_file():
            # Tier 2 conventions/config.md, "Bundle / umbrella mods": a payload-only bundle has no source.
            if addons.is_dir() and any(addons.glob("*.pbo")):
                return "payload-only bundle (prebuilt Addons\\*.pbo, no config.cpp): nothing to lint"
            self.add("config-missing", ERROR, cfg, None, "config.cpp is missing, so the mod has nothing to load.")
            return None
        self.check_prefix()
        tree = self.check_config(cfg)
        if tree is not None:
            self.check_patches(cfg, tree)
            self.check_modules(cfg, tree)
        self.check_scripts()
        self.check_rvmats()
        return None

    # $PBOPREFIX$ and the P:\ link
    def check_prefix(self) -> None:
        path = self.mod_dir / "$PBOPREFIX$"
        if not path.is_file():
            self.add("pboprefix-missing", ERROR, path, None,
                     f"$PBOPREFIX$ is missing; the PBO would have no root for paths starting {self.mod}\\.")
            return
        prefix = path.read_text(encoding="utf-8-sig").strip()
        if prefix != self.mod:
            self.add("pboprefix-mismatch", ERROR, path, 1,
                     f"$PBOPREFIX$ is {prefix!r}, expected {self.mod!r} (the mod folder name /dayz-build-pbo packs under).")
        if prefix:
            self.prefix = prefix
        self.check_link(path)

    def check_link(self, prefix_file: Path) -> None:
        if self.p_drive is None:
            return
        link = self.p_drive / self.prefix
        if not self.p_drive.is_dir():
            self.add("p-not-mounted", WARNING, prefix_file, None, f"{self.p_drive} is not mounted, so the {link} link was not checked.")
            return
        if not os.path.lexists(link):
            self.add("p-link", ERROR, prefix_file, None, f"{link} is missing; AddonBuilder packs the mod through that link.")
            return
        target = h.link_target(link)
        if target is None:
            self.add("p-link", ERROR, prefix_file, None, f"{link} is a real folder, not a link to {self.mod_dir}.")
        elif not h.paths_equal(target, self.mod_dir):
            self.add("p-link", ERROR, prefix_file, None, f"{link} points at {target}, not at {self.mod_dir}.")

    # config.cpp
    def check_config(self, cfg: Path) -> Optional[Node]:
        text = cfg.read_text(encoding="utf-8", errors="replace")
        problems = edit_check.check_config(text)
        for p in problems:
            self.add("config-syntax", ERROR, cfg, p.line, p.message)
        if problems:
            return None  # the structure is unreliable until the syntax is fixed
        toks = edit_check.tokenize(text)
        self.check_file_refs(cfg, toks)
        return parse_tree(toks)

    def check_patches(self, cfg: Path, tree: Node) -> None:
        patches = tree.child("CfgPatches")
        if patches is None:
            self.add("cfgpatches-missing", ERROR, cfg, None, "config.cpp has no class CfgPatches, so the engine never loads the mod's config.")
            return
        if not patches.classes:
            self.add("cfgpatches-empty", ERROR, cfg, patches.line, "class CfgPatches declares no patch class; add class <ModName> { ... };.")
            return
        own = {p.name.lower() for p in patches.classes}
        vanilla = self.vanilla_patches()
        for patch in patches.classes:
            for field in ("units", "weapons", "requiredAddons"):
                prop = patch.props.get(field.lower())
                if prop is None and field == "requiredAddons":
                    # Without it the mod's config can load before the vanilla classes it changes.
                    self.add("required-addons-missing", ERROR, cfg, patch.line,
                             f"CfgPatches class {patch.name} has no requiredAddons[] array, so its load order is not guaranteed.")
                elif prop is None:
                    # Vanilla loads patch classes without units[] or weapons[] (P:\DZ\data\aiconfigs\config.cpp,
                    # class DZ_data_aiconfigs has an empty body), so a missing one is only a warning.
                    self.add("cfgpatches-field-missing", WARNING, cfg, patch.line, f"CfgPatches class {patch.name} has no {field}[] array.")
                elif not prop[2]:
                    self.add("cfgpatches-field", ERROR, cfg, prop[1], f"CfgPatches class {patch.name}: {field} must be an array, {field}[] = {{...}};.")
            prop = patch.props.get("requiredaddons")
            if prop is not None and prop[2]:
                self.check_addon_names(cfg, patch.name, prop[3], own, vanilla)

    def check_addon_names(self, cfg: Path, patch: str, values: list[tuple[str, int]], own: set[str], vanilla: Optional[set[str]]) -> None:
        seen: set[str] = set()
        for name, line in values:
            low = name.lower()
            if not ADDON_NAME_RE.match(name):
                self.add("required-addon-name", ERROR, cfg, line,
                         f"requiredAddons entry {name!r} is not a CfgPatches class name (no paths, .pbo files, @mod folders or spaces).")
            elif low in own:
                self.add("required-addon-name", ERROR, cfg, line, f"requiredAddons lists {name}, a CfgPatches class of this mod itself.")
            elif vanilla is not None and low.startswith("dz_") and low not in vanilla:
                self.add("required-addon-name", ERROR, cfg, line,
                         f"requiredAddons entry {name} is not a vanilla CfgPatches class on {self.vanilla_root}; check the spelling.")
            if low in seen:
                self.add("required-addon-duplicate", WARNING, cfg, line, f"requiredAddons lists {name} twice in {patch}.")
            seen.add(low)

    def vanilla_patches(self) -> Optional[set[str]]:
        """Lowercased CfgPatches class names from the vanilla configs, or None when they are not on disk."""
        root = self.vanilla_root
        if root is None or not (root / "DZ").is_dir():
            return None
        # Unpacked vanilla data: P:\DZ\ holds every addon, P:\scripts\ holds DZ_Scripts.
        configs = [*(root / "DZ").rglob("config.cpp"), root / "scripts" / "config.cpp", root / "bin" / "config.cpp"]
        names: set[str] = set()
        for cfg in configs:
            if cfg.is_file():
                names |= patch_names(cfg.read_text(encoding="utf-8", errors="replace"))
        return names or None

    def check_modules(self, cfg: Path, tree: Node) -> None:
        mods = tree.child("CfgMods")
        listed: set[str] = set()  # lowercased mod-relative folders the defs compile
        if mods is not None:
            for mod_class in mods.classes:
                defs = mod_class.child("defs")
                for module in defs.classes if defs is not None else []:
                    key = module.name.lower()
                    files = module.props.get("files")
                    if key not in MODULE_LAYERS or files is None:
                        continue
                    for value, line in files[3]:
                        rel = self.in_mod(value)
                        if rel is None:
                            self.add("script-module-path", ERROR, cfg, line,
                                     f"{module.name} lists {value!r}, which is not inside this mod (paths start {self.prefix}/).")
                            continue
                        listed.add(rel.lower())
                        if not (self.mod_dir / rel).is_dir():
                            self.add("script-module-path", ERROR, cfg, line,
                                     f"{module.name} lists {value!r}, but {self.rel(self.mod_dir / rel)}/ does not exist.")
                        layer = Path(rel).name
                        want = MODULE_LAYERS[key]
                        if layer.lower() in LAYER_MODULE and layer.lower() != want.lower():
                            self.add("script-module-layer", ERROR, cfg, line,
                                     f"{module.name} compiles the {want} layer, but {value!r} is a {layer} folder "
                                     f"(that belongs in {MODULE_SPELLING[LAYER_MODULE[layer.lower()]]}).")
        scripts = self.mod_dir / "scripts"
        for folder in sorted(p for p in scripts.iterdir() if p.is_dir()) if scripts.is_dir() else []:
            if not any(folder.rglob("*.c")):
                continue
            rel = folder.relative_to(self.mod_dir).as_posix()
            low = rel.lower()
            if not any(entry == low or entry.startswith(low + "/") or low.startswith(entry + "/") for entry in listed):
                module = MODULE_SPELLING.get(LAYER_MODULE.get(folder.name.lower(), ""), "a script module")
                self.add("script-module-unlisted", WARNING, cfg, mods.line if mods is not None else None,
                         f"{rel}/ holds scripts, but no CfgMods defs entry lists {self.prefix}/{rel}; "
                         f"add it to {module} or the engine ignores those files.")

    def in_mod(self, value: str) -> Optional[str]:
        """The mod-relative path of a config path that starts with the prefix, else None."""
        norm = value.replace("/", "\\").lstrip("\\")
        head = self.prefix.replace("/", "\\").lower() + "\\"
        if not norm.lower().startswith(head):
            return None
        return norm[len(head):].replace("\\", "/")

    # file references in config.cpp and .rvmat files
    def check_file_refs(self, source: Path, toks: list) -> None:
        last_ident = ""
        for tok in toks:
            if tok.kind == "ident":
                last_ident = tok.text
                continue
            if tok.kind != "str":
                continue
            value = unquote(tok.text).strip()
            ext = os.path.splitext(value)[1].lower()
            if ext not in FILE_EXTS:
                continue
            if re.match(r"^[A-Za-z]:[\\/]", value) or value.replace("/", "\\").lower().startswith("workspace\\"):
                self.add("absolute-path", ERROR, source, tok.line,
                         f"{value!r} is a disk path; in game paths start at the PBO prefix, {self.prefix}\\...")
                continue
            rel = self.in_mod(value)
            if ext in UNPACKED_IMAGE_EXTS:
                self.add("texture-format", ERROR, source, tok.line,
                         f"{value!r} is a {ext} image; the game loads textures as .paa. Pack it with /dayz-pack-texture.")
            if rel is None:
                continue  # vanilla or another mod: not ours to check
            if not (self.mod_dir / rel).is_file():
                rule = {".p3d": "missing-model", ".paa": "missing-texture", ".edds": "missing-texture",
                        ".rvmat": "missing-texture"}.get(ext, "missing-file")
                self.add(rule, ERROR, source, tok.line, f"{value!r} points at {self.rel(self.mod_dir / rel)}, which does not exist.")
            elif ext == ".paa" and ROLE_SUFFIX_PROPS.match(last_ident) and not pack_texture.SUFFIX_RE.search(Path(rel).stem):
                self.add("texture-suffix", WARNING, source, tok.line,
                         f"{Path(rel).name} has no texture role suffix (_co, _ca, _nohq, _smdi, ...); ImageToPAA picks its format from it.")

    def check_rvmats(self) -> None:
        for path in sorted(self.mod_dir.rglob("*.rvmat")):
            text = path.read_text(encoding="utf-8", errors="replace")
            try:
                toks = edit_check.tokenize(text)
            except edit_check.TokenizeError as e:
                self.add("rvmat-syntax", ERROR, path, e.line, e.message)
                continue
            self.check_file_refs(path, toks)

    # scripts
    def check_scripts(self) -> None:
        scripts = self.mod_dir / "scripts"
        if not scripts.is_dir():
            return
        for path in sorted(p for p in scripts.rglob("*") if p.is_file()):
            if path.name.startswith("."):
                continue  # .gitkeep and editor files
            if path.suffix.lower() != ".c":
                self.add("script-suffix", WARNING, path, None,
                         f"{path.name} is under scripts/ but is not a .c file, so it is never compiled.")
                continue
            source = path.read_text(encoding="utf-8", errors="replace")
            # Drop // and /* */ comments but keep their newlines, so line numbers stay right.
            source = re.sub(r"//[^\n]*|/\*.*?\*/", lambda m: "\n" * m.group().count("\n"), source, flags=re.DOTALL)
            for number, text in enumerate(source.splitlines(), 1):
                if MODDED_EXTENDS_RE.search(text):
                    self.add("modded-class-extends", ERROR, path, number,
                             f"{text.strip()}: a modded class with an extends clause is a silent no-op.")


def patch_names(text: str) -> set[str]:
    """Lowercased class names directly inside class CfgPatches { }."""
    text = re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.DOTALL)
    m = re.search(r"\bclass\s+CfgPatches\s*\{", text)
    if not m:
        return set()
    names, depth = set(), 1
    for t in re.finditer(r"\bclass\s+(\w+)\s*(?::\s*\w+\s*)?\{|[{}]", text[m.end():]):
        token = t.group(0)
        if token == "}":
            depth -= 1
            if depth == 0:
                break
        elif token == "{":
            depth += 1
        else:
            if depth == 1:
                names.add(t.group(1).lower())
            depth += 1
    return names


# --- report -------------------------------------------------------------------

def lint_mod(
    mod: str,
    mod_dir: Path,
    display_root: Optional[Path] = None,
    check_link: bool = True,
    p_drive: Optional[Path] = None,
    project_dir: Optional[Path] = None,
    in_workspace: bool = True,
) -> dict:
    """Lint one mod folder and return the report.

    p_drive (default P:\\) holds the $PBOPREFIX$ link and the unpacked vanilla
    data used for the requiredAddons spelling check (skipped when P:\\DZ\\ is
    not there). check_link=False skips the link check, for /dayz-build-pbo,
    which checks the link itself. project_dir: for the learned known-errors
    file used in triage. in_workspace=False: the folder is not
    <project>\\workspace\\<ModName>\\, so the p-link fix points at
    /dayz-import-mod or mklink /J instead of /dayz-add-scaffold, which only
    works on workspace mods.
    """
    if not mod_dir.is_dir():
        raise LintError(f"{mod_dir} not found")
    p_drive = p_drive or P_DRIVE
    lint = Lint(mod, mod_dir, display_root or mod_dir.parent, p_drive if check_link else None, p_drive)
    note = lint.run()
    known = triage.load_known(triage.KNOWN_ERRORS, triage.learned_path(project_dir) if project_dir else None)
    context = {"ModName": mod}
    for f in lint.findings:
        f["triage"] = triage.match_line(f["text"], known, context)
        if f["rule"] == "p-link" and not in_workspace and f["triage"]["status"] == "known":
            f["triage"]["fix"] = outside_link_fix(p_drive / lint.prefix, mod_dir)
        elif f["rule"] == "script-module-path" and f["triage"]["status"] == "known":
            # The catalog fix names workspace/<ModName>/; name the folder actually linted instead.
            f["triage"]["fix"] = (f"Point files[] at {mod}/scripts/<layer> and make sure that folder "
                                  f"exists under {lint.rel(mod_dir)}/.")
    findings = sorted(lint.findings, key=lambda f: (f["severity"] != ERROR, f["file"], f["line"] or 0))
    errors = sum(f["severity"] == ERROR for f in findings)
    report = {
        "verdict": "FAIL" if errors else "PASS",
        "mod": mod,
        "mod_dir": str(mod_dir),
        "errors": errors,
        "warnings": len(findings) - errors,
        "findings": findings,
    }
    if note:
        report["note"] = note
    return report


def outside_link_fix(link: Path, mod_dir: Path) -> str:
    """The p-link fix for a folder outside workspace\\ (/dayz-add-scaffold refuses those)."""
    return (f'Run /dayz-import-mod --source "{mod_dir}" to link it into workspace\\ and create {link}, '
            f'or link it by hand: mklink /J "{link}" "{mod_dir}".')


def cached_workspace() -> Optional[Path]:
    """<project>\\workspace\\ of the project cached by /dayz-init, or None. Never exits."""
    project = h.load_module("dayz_lint_init_state", h.DAYZ_INIT_STATE).cached_project_root()
    return project / "workspace" if project is not None and project.is_dir() else None


def is_workspace_mod(mod_dir: Path, mod: str) -> bool:
    """True when mod_dir is (or is linked from) workspace\\<mod>\\ of the cached project."""
    workspace = cached_workspace()
    if workspace is None:
        return False
    entry = workspace / mod
    return entry.is_dir() and h.paths_equal(entry.resolve(), mod_dir.resolve())


def render_text(report: dict) -> str:
    out = []
    for f in report["findings"]:
        where = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
        out.append(f"- {where}  {f['severity']} {f['rule']}: {f['message']}")
        t = f["triage"]
        if t["status"] == "known":
            out.append(f"    -> {t['owner_agent']}: {t['fix']}")
    if report.get("note"):
        out.append(f"  {report['note']}")
    out.append(f"  {report['errors']} error(s), {report['warnings']} warning(s)")
    return "\n".join(out)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Find errors that would stop a DayZ mod loading, before packing.")
    parser.add_argument("mod", nargs="?", help="Mod name under workspace/ in the project cached by /dayz-init.")
    parser.add_argument("--mod-dir", type=Path, help="Lint this folder instead (its name is the mod name).")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON after the verdict line.")
    try:
        args = parser.parse_args(argv)
        if not args.mod and not args.mod_dir:
            parser.error("give a <ModName> or --mod-dir")
    except SystemExit as e:
        return 0 if e.code == 0 else 2

    try:
        if args.mod_dir:
            mod_dir = args.mod_dir.resolve()
            mod = args.mod or mod_dir.name
            report = lint_mod(mod, mod_dir, display_root=Path.cwd(), in_workspace=is_workspace_mod(mod_dir, mod))
        else:
            project_dir = h.resolve_project_dir()
            report = lint_mod(args.mod, project_dir / "workspace" / args.mod, project_dir, project_dir=project_dir)
    except SystemExit:  # resolve_project_dir already printed why on stderr
        return _error("no usable project: run /dayz-init, or pass --mod-dir", args.json)
    except (LintError, OSError, ValueError) as e:
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
