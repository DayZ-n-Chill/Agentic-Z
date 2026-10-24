"""dayz-recipe: pre-fill dayz-mod-architect's plan from a recipe.

  recipe.py list [--json]
  recipe.py <weapon|vest|craftable> <ModName> [--item NAME] [--parent CLASS] [...] [--force] [--json]

A recipe (recipes/<name>.json) is a plan template for a common mod: the
classes, the vanilla classes they build on, the files, a task per team with a
done check, and the /dayz-gate behavior checks. This script fills it in for
one mod and checks every vanilla class against P:\\ before writing anything:

  - each vanilla class is defined in a config.cpp under P:\\dz in the expected
    config root (CfgWeapons, CfgVehicles or CfgMagazines), and its CfgPatches
    addon becomes the requiredAddons[] entry
  - each script symbol the recipe uses is defined under P:\\scripts
  - each fit holds on the resolved vanilla config: the attachment's
    inventorySlot is one of the parent's attachments[], the magazine is in the
    parent's magazines[], the vest takes the Vest slot, the cargo item fits the
    parent's itemsCargoSize

Then it writes output/<ModName>-plan/plan.md (a draft the architect finishes),
behavior-checks.json (validated with dayz-gate's own checker) and recipe.json.

The first output line is the verdict: WROTE (exit 0), FAIL (exit 1, a vanilla
class or fit did not check out; nothing written) or ERROR (exit 2: bad
arguments, no project, P:\\ not mounted, plan already there). See SKILL.md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
SKILLS_DIR = HERE.parent
RECIPES_DIR = HERE / "recipes"
sys.path.insert(0, str(SKILLS_DIR / "_shared"))
import skill_helpers as h  # noqa: E402

behavior = h.load_module("dayz_recipe_behavior", SKILLS_DIR / "dayz-gate" / "behavior.py")

P_DRIVE = Path("P:\\")
PLAN_FILES = ("plan.md", behavior.CHECKS_FILENAME, "recipe.json")
MOD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
DRAFT_MARK = "<!-- dayz-recipe draft -->"


class RecipeError(Exception):
    """Bad arguments, a broken recipe file or an unusable setup (exit 2)."""


# --- vanilla config index ----------------------------------------------------------

@dataclass
class ClassDef:
    name: str
    parent: Optional[str]
    root: str          # top-level class it sits in, e.g. CfgVehicles
    file: Path
    line: int
    body: str          # text between its braces
    addon: Optional[str]  # first CfgPatches class of the file


TOKEN_RE = re.compile(
    r'"(?:[^"]|"")*"'                                            # string
    r"|//[^\n]*|/\*.*?\*/"                                        # comments
    r"|\bclass\s+(\w+)\s*(?::\s*(\w+))?\s*([{;])"                # class header
    r"|[{}]",
    re.S,
)


def parse_config(path: Path) -> list[ClassDef]:
    """Every class with a body in one config.cpp, with its enclosing root."""
    text = path.read_text(encoding="utf-8", errors="replace")
    stack: list[Optional[tuple[str, Optional[str], int, int]]] = []  # class or None for an array brace
    out: list[ClassDef] = []
    patches: list[str] = []
    line, counted = 1, 0
    for m in TOKEN_RE.finditer(text):
        tok = m.group(0)
        if tok[0] in '"/':
            continue
        if m.group(1):
            if m.group(3) == ";":
                continue  # forward declaration
            line += text.count("\n", counted, m.start())
            counted = m.start()
            stack.append((m.group(1), m.group(2), m.end(), line))
        elif tok == "{":
            stack.append(None)
        elif stack:
            top = stack.pop()
            if top is None:
                continue
            names = [s[0] for s in stack if s is not None]
            name, parent, start, at = top
            if len(names) == 1:
                if names[0].lower() == "cfgpatches":
                    patches.append(name)
                else:
                    out.append(ClassDef(name, parent, names[0], path, at, text[start:m.start()], None))
    addon = patches[0] if patches else None
    for c in out:
        c.addon = addon
    return out


PROP_RE = re.compile(r"(\w+)(\[\])?\s*(\+?=)\s*")


def properties(body: str) -> dict[str, object]:
    """Direct properties of a class body: name -> str, or list of str for arrays."""
    props: dict[str, object] = {}
    depth, i = 0, 0
    while i < len(body):
        ch = body[i]
        if ch == '"':
            j = body.find('"', i + 1)
            i = len(body) if j < 0 else j + 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0 and (ch.isalpha() or ch == "_"):
            m = PROP_RE.match(body, i)
            if m and not body.startswith("class", i):
                end = _value_end(body, m.end())
                raw = body[m.end():end].strip()
                if m.group(2):
                    values = re.findall(r'"((?:[^"]|"")*)"|(-?[\d.]+)', raw)
                    items = [s if s else n for s, n in values]
                    if m.group(3) == "+=" and isinstance(props.get(m.group(1)), list):
                        items = props[m.group(1)] + items  # type: ignore[operator]
                    props[m.group(1)] = items
                else:
                    props[m.group(1)] = raw.strip('"')
                i = end + 1
                continue
            word = re.match(r"\w+", body[i:])
            i += len(word.group(0)) if word else 1
            continue
        i += 1
    return props


def _value_end(body: str, i: int) -> int:
    depth = 0
    while i < len(body):
        ch = body[i]
        if ch == '"':
            j = body.find('"', i + 1)
            i = len(body) if j < 0 else j + 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif ch == ";" and depth <= 0:
            return i
        i += 1
    return i


class Vanilla:
    """Lookups in the vanilla data on P:\\ (or a fixture tree with dz/ and scripts/)."""

    def __init__(self, root: Path):
        self.root = root
        self._parsed: dict[Path, list[ClassDef]] = {}
        self._all: Optional[list[Path]] = None

    def _classes(self, path: Path) -> list[ClassDef]:
        if path not in self._parsed:
            self._parsed[path] = parse_config(path) if path.is_file() else []
        return self._parsed[path]

    def find(self, name: str, root: str, hint: Optional[str] = None) -> Optional[ClassDef]:
        """The definition of a class in a config root, trying the hint file first."""
        first = [self.root / hint] if hint else []
        if self._all is None:
            self._all = sorted((self.root / "dz").rglob("config.cpp"))
        for path in first + self._all:
            for c in self._classes(path):
                if c.name.lower() == name.lower() and c.root.lower() == root.lower():
                    return c
        return None

    def resolve(self, cls: ClassDef, prop: str) -> object:
        """A property with inheritance: the class, then its parents in the same root."""
        seen = set()
        cur: Optional[ClassDef] = cls
        while cur is not None and cur.name.lower() not in seen:
            seen.add(cur.name.lower())
            props = properties(cur.body)
            if prop in props:
                return props[prop]
            cur = self.find(cur.parent, cur.root, _rel(self.root, cur.file)) if cur.parent else None
        return None

    def items_for_slots(self, root: str, slots: list[str]) -> dict[str, list[str]]:
        """Spawnable (scope 2) classes in a config root per slot their resolved inventorySlot names."""
        if self._all is None:
            self._all = sorted((self.root / "dz").rglob("config.cpp"))
        index: dict[str, ClassDef] = {}
        for path in self._all:
            for c in self._classes(path):
                if c.root.lower() == root.lower():
                    index.setdefault(c.name.lower(), c)

        def resolved(cls: ClassDef, prop: str) -> object:
            seen = set()
            cur: Optional[ClassDef] = cls
            while cur is not None and cur.name.lower() not in seen:
                seen.add(cur.name.lower())
                props = properties(cur.body)
                if prop in props:
                    return props[prop]
                cur = index.get(cur.parent.lower()) if cur.parent else None
            return None

        out: dict[str, list[str]] = {s: [] for s in slots}
        by_lower = {s.lower(): s for s in slots}
        for c in index.values():
            if resolved(c, "scope") != "2":
                continue
            for s in _as_list(resolved(c, "inventorySlot")):
                if s.lower() in by_lower:
                    out[by_lower[s.lower()]].append(c.name)
        return out

    def find_script(self, pattern: str, hint: Optional[str] = None) -> Optional[tuple[Path, int]]:
        rx = re.compile(pattern, re.MULTILINE)
        scripts = self.root / "scripts"
        paths = ([scripts / hint] if hint else []) + sorted(scripts.rglob("*.c"))
        for path in paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            m = rx.search(text)
            if m:
                # A leading \s* can start the match on the line before; count from the first word.
                start = m.start() + len(m.group(0)) - len(m.group(0).lstrip())
                return path, text.count("\n", 0, start) + 1
        return None


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    return value if isinstance(value, list) else [str(value)]


# --- recipes -----------------------------------------------------------------------

def list_recipes() -> list[str]:
    return sorted(p.stem for p in RECIPES_DIR.glob("*.json"))


def load_recipe(name: str) -> dict:
    path = RECIPES_DIR / f"{name}.json"
    if not path.is_file():
        raise RecipeError(f"unknown recipe {name!r}; choose one of {', '.join(list_recipes())}")
    return json.loads(path.read_text(encoding="utf-8"))


def all_option_names() -> list[str]:
    names: set[str] = set()
    for name in list_recipes():
        names.update(load_recipe(name)["options"])
    return sorted(names)


class _Strict(dict):
    def __missing__(self, key):
        raise RecipeError(f"recipe uses unknown placeholder {{{key}}}")


def fill(value, values: dict):
    """Fill {placeholders} in every string of a recipe value."""
    if isinstance(value, str):
        return value.format_map(_Strict(values))
    if isinstance(value, list):
        return [fill(v, values) for v in value]
    if isinstance(value, dict):
        return {k: fill(v, values) for k, v in value.items()}
    return value


@dataclass
class Result:
    recipe: dict
    mod: str
    item: str
    values: dict
    vanilla: list[dict] = field(default_factory=list)
    scripts: list[dict] = field(default_factory=list)
    fits: list[dict] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


def build(recipe: dict, mod: str, item: Optional[str], chosen: dict[str, str], vanilla: Vanilla,
          display: Path = P_DRIVE) -> Result:
    """Check the recipe's vanilla classes, scripts and fits; return everything the plan needs."""
    if not MOD_RE.match(mod):
        raise RecipeError(f"mod name {mod!r}: start with a letter, then letters, digits or '_' (max 64)")
    unknown = set(chosen) - set(recipe["options"])
    if unknown:
        raise RecipeError(f"the {recipe['name']} recipe has no option --{sorted(unknown)[0]}; "
                          f"it takes {', '.join('--' + o for o in recipe['options'])}")
    item = item or recipe["item"]["default"].format(mod=mod)
    for label, name in [("item", item)] + sorted(chosen.items()):
        if not behavior.CLASS_RE.match(name):
            raise RecipeError(f"--{label} {name!r} is not a config class name")

    values = {"mod": mod, "item": item, "item_lower": item.lower()}
    res = Result(recipe, mod, item, values)
    found: dict[str, ClassDef] = {}
    for opt, spec in recipe["options"].items():
        name = chosen.get(opt, spec["default"])
        values[opt] = name
        cls = vanilla.find(name, spec["root"], spec["hint"] if name == spec["default"] else None)
        entry = {"option": opt, "class": name, "root": spec["root"]}
        if cls is None:
            res.failures.append(f"{name} ({opt}) is not defined in {spec['root']} in any config.cpp under "
                                f"{display / 'dz'}. Check the spelling, or pass --{opt} with another vanilla class.")
            entry.update(file=None, line=None, addon=None)
        else:
            found[opt] = cls
            entry.update(file=str(display / Path(_rel(vanilla.root, cls.file))), line=cls.line,
                         addon=cls.addon, parent=cls.parent)
        res.vanilla.append(entry)

    parent = found.get("parent")
    values["parent_addon"] = (parent.addon if parent else None) or "<its CfgPatches class>"
    selections = _as_list(vanilla.resolve(parent, "hiddenSelections")) if parent else []
    values["parent_selections"] = ", ".join(selections) if selections else "none (the parent has no hiddenSelections)"

    for spec in recipe["scripts"]:
        hit = vanilla.find_script(spec["pattern"], spec.get("hint"))
        entry = {"symbol": spec["symbol"], "why": spec["why"], "file": None, "line": None}
        if hit is None:
            res.failures.append(f"{spec['symbol']} is not defined under {display / 'scripts'}.")
        else:
            entry.update(file=str(display / Path(_rel(vanilla.root, hit[0]))), line=hit[1])
        res.scripts.append(entry)

    for fit in recipe["fits"]:
        host = found.get(fit["host"])
        guest = found.get(fit.get("item", ""))
        if host is None or ("item" in fit and guest is None):
            continue  # already a failure above
        res.fits.append(_check_fit(fit, host, guest, vanilla, res.failures))
    return res


def _check_fit(fit: dict, host: ClassDef, guest: Optional[ClassDef], vanilla: Vanilla, failures: list[str]) -> dict:
    """One fit on the resolved vanilla config. A miss adds a failure that says what to pass instead."""
    kind, opt = fit["kind"], fit.get("item")
    if kind == "slot":
        slots = {s.lower() for s in _as_list(vanilla.resolve(guest, "inventorySlot"))}
        offered = _as_list(vanilla.resolve(host, "attachments"))
        common = [s for s in offered if s.lower() in slots]
        ok = bool(common)
        what = f"{guest.name} fits {host.name} in slot {', '.join(common)}"
        miss = f"{guest.name} fits no attachment slot of {host.name}."
        if not offered:
            miss += f" {host.name} has no attachments[]"
        elif not ok:  # list the vanilla items that do fit, so the user need not look one up
            items = vanilla.items_for_slots(guest.root, offered)
            listed = "; ".join(f"{s}: {', '.join(items[s]) or '(no vanilla item)'}" for s in offered)
            miss += f" Pass --{opt} with a vanilla item for one of its slots, {listed}"
    elif kind == "magazine":
        mags = _as_list(vanilla.resolve(host, "magazines"))
        ok = guest.name.lower() in {m.lower() for m in mags}
        what = f"{host.name} takes {guest.name}"
        miss = f"{host.name} does not take {guest.name}. Pass --{opt} with one of: {', '.join(mags) or '(none)'}"
    elif kind == "wear":
        ok = fit["slot"].lower() in {s.lower() for s in _as_list(vanilla.resolve(host, "inventorySlot"))}
        what = f"{host.name} is worn in the {fit['slot']} slot"
        miss = (f"{host.name} is not worn in the {fit['slot']} slot. Pass --{fit['host']} with a vanilla class "
                f"whose inventorySlot includes {fit['slot']}")
    elif kind == "cargo":
        size = _numbers(vanilla.resolve(guest, "itemSize"))
        cargo = _numbers(vanilla.resolve(host, "itemsCargoSize"))
        ok = len(size) == 2 and len(cargo) == 2 and (
            (size[0] <= cargo[0] and size[1] <= cargo[1]) or (size[1] <= cargo[0] and size[0] <= cargo[1]))
        what = f"{guest.name} (itemSize {_dims(size)}) fits {host.name} cargo ({_dims(cargo)})"
        miss = (f"{guest.name} (itemSize {_dims(size)}) does not fit {host.name} cargo ({_dims(cargo)}). "
                f"Pass --{opt} with a smaller vanilla item")
    else:
        raise RecipeError(f"unknown fit kind {kind!r} in the recipe file")
    if not ok:
        failures.append(f"{miss}.")
    return {"kind": kind, "ok": ok, "what": what if ok else miss}


def _numbers(value: object) -> list[int]:
    try:
        return [int(float(v)) for v in _as_list(value)]
    except ValueError:
        return []


def _dims(n: list[int]) -> str:
    return "x".join(map(str, n)) if n else "unknown"


# --- output ------------------------------------------------------------------------

def checks_file(res: Result) -> dict:
    data = {"mod": res.mod, "checks": fill(res.recipe["checks"], res.values)}
    behavior.validate_checks(data, behavior.CHECKS_FILENAME)
    return data


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|")


def render_plan(res: Result, workspace_exists: bool, spec_exists: bool) -> str:
    r, v = res.recipe, res.values
    out = [DRAFT_MARK, f"# {res.mod} plan", "",
           f"Draft written by `/dayz-recipe {r['name']}`. `dayz-mod-architect` checks it against the request "
           "and the spec, answers the open questions with the user, and rewrites this file and "
           "`behavior-checks.json` as the final plan. Every vanilla class below was found on P:\\ when the recipe ran.",
           "", f"**Recipe:** {r['title']}. {fill(r['summary'], v)}", ""]
    if not workspace_exists:
        out += [f"`workspace/{res.mod}/` does not exist yet. The orchestrator creates it with "
                f"`/dayz-new-mod {res.mod}` after the plan is approved.", ""]
    if spec_exists:
        out += [f"`workspace/{res.mod}/spec.md` exists. Plan to it and list where this draft differs.", ""]

    out += ["## Classes", "", "| Class | Where | Parent | Notes |", "| --- | --- | --- | --- |"]
    for c in fill(r["classes"], v):
        out.append(f"| `{c['name']}` | {_cell(c['where'])} | `{c['parent']}` | {_cell(c['notes'])} |")

    out += ["", "## Vanilla classes", "", "| Class | Use | Config | Defined at | CfgPatches |",
            "| --- | --- | --- | --- | --- |"]
    for e in res.vanilla:
        out.append(f"| `{e['class']}` | {e['option']} | {e['root']} | `{e['file']}:{e['line']}` | `{e['addon']}` |")
    for e in res.scripts:
        out.append(f"| `{e['symbol']}` | {_cell(e['why'])} | script | `{e['file']}:{e['line']}` | |")
    out += ["", f"Hidden selections of `{v['parent']}`: {v['parent_selections']}."]
    if res.fits:
        out += ["", "## Fit checks", ""] + [f"- [OK] {f['what']}." for f in res.fits]

    out += ["", "## Files", "", "| File | What |", "| --- | --- |"]
    for f in fill(r["files"], v):
        out.append(f"| `{f['path']}` | {_cell(f['what'])} |")

    out += ["", "## Tasks", "", "| Task | Team | Done check | Files | Depends on |", "| --- | --- | --- | --- | --- |"]
    for t in fill(r["tasks"], v):
        files = ", ".join(f"`{p}`" for p in t["files"])
        out.append(f"| {t['id']}: {_cell(t['task'])} (`{t['worker']}`) | {t['team']} | {_cell(t['done'])} | "
                   f"{files} | {', '.join(t['depends']) or 'none'} |")

    out += ["", "## Behavior checks", "", "`behavior-checks.json` beside this file, for `/dayz-gate behavior`:", ""]
    for c in checks_file(res)["checks"]:
        extra = f" with `{c['with']}`" if "with" in c else ""
        out.append(f"- `{c['id']}`: {c['feature']} (`{c['action']}` on `{c['item']}`{extra})")
    out += ["", "## Needs a person in game", ""] + [f"- {n}" for n in fill(r["needs_person"], v)]
    out += ["", "## Open questions", ""] + [f"- {q}" for q in fill(r["questions"], v)]
    return "\n".join(out) + "\n"


def write_plan(res: Result, project: Path, out_dir: Path, force: bool) -> list[Path]:
    present = [out_dir / n for n in PLAN_FILES if (out_dir / n).exists()]
    if present and not force:
        raise RecipeError(f"{present[0]} already exists. Pass --force to replace the plan files, "
                          "or ask dayz-mod-architect to change the plan instead.")
    workspace = project / "workspace" / res.mod
    plan = render_plan(res, workspace.is_dir(), (workspace / "spec.md").is_file())
    data = checks_file(res)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / n for n in PLAN_FILES]
    paths[0].write_text(plan, encoding="utf-8")
    paths[1].write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    paths[2].write_text(json.dumps(report(res), indent=2) + "\n", encoding="utf-8")
    return paths


def report(res: Result) -> dict:
    v = res.values
    return {
        "recipe": res.recipe["name"], "mod": res.mod, "item": res.item,
        "options": {o: v[o] for o in res.recipe["options"]},
        "vanilla": res.vanilla, "scripts": res.scripts, "fits": res.fits, "failures": res.failures,
        "classes": fill(res.recipe["classes"], v), "files": fill(res.recipe["files"], v),
        "tasks": fill(res.recipe["tasks"], v),
        "needs_person": fill(res.recipe["needs_person"], v), "questions": fill(res.recipe["questions"], v),
    }


# --- cli ---------------------------------------------------------------------------

def check_vanilla_root(root: Path) -> None:
    if not (root / "dz").is_dir() or not (root / "scripts").is_dir():
        raise RecipeError(f"no vanilla data at {root} (it needs dz\\ and scripts\\). Mount P: with "
                          "/dayz-workdrive and check it with /dayz-preflight, then run the recipe again.")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Pre-fill dayz-mod-architect's plan from a recipe.")
    parser.add_argument("recipe", help=f"list, or one of: {', '.join(list_recipes())}")
    parser.add_argument("mod", nargs="?", help="Mod name; the plan goes to output/<ModName>-plan/.")
    parser.add_argument("--item", help="Class name of the new item (default from the recipe).")
    for opt in all_option_names():
        parser.add_argument(f"--{opt}", metavar="CLASS", help="Vanilla class; see 'recipe.py list'.")
    parser.add_argument("--project", type=Path, help="Project root (default: the one cached by /dayz-init).")
    parser.add_argument("--out", type=Path, help="Plan folder (default output/<ModName>-plan/ in the project).")
    parser.add_argument("--vanilla", type=Path, default=P_DRIVE, help=r"Vanilla data root (default P:\).")
    parser.add_argument("--force", action="store_true", help="Replace plan files that already exist.")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON after the verdict line.")
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 2

    if args.recipe == "list":
        recipes = [load_recipe(n) for n in list_recipes()]
        if args.json:
            print(json.dumps([{"name": r["name"], "title": r["title"], "summary": r["summary"],
                               "options": {o: s["default"] for o, s in r["options"].items()}} for r in recipes], indent=2))
        else:
            for r in recipes:
                opts = " ".join(f"--{o} {s['default']}" for o, s in r["options"].items())
                print(f"{r['name']:<10} {r['title']}. {r['summary']}\n{'':<10} defaults: {opts}")
        return 0

    try:
        if not args.mod:
            raise RecipeError("give a <ModName> after the recipe")
        recipe = load_recipe(args.recipe)
        chosen = {o: getattr(args, o) for o in all_option_names() if getattr(args, o)}
        check_vanilla_root(args.vanilla)
        if args.project:
            project = args.project.resolve()
        else:
            try:
                project = h.resolve_project_dir()
            except SystemExit:  # resolve_project_dir already printed why on stderr
                raise RecipeError("no usable project: run /dayz-init, or pass --project") from None
        res = build(recipe, args.mod, args.item, chosen, Vanilla(args.vanilla), args.vanilla)
        if not res.ok:
            print("FAIL")
            print(json.dumps(report(res), indent=2) if args.json else
                  "\n".join(f"{h.FAIL}{f}" for f in res.failures) + "\n  Nothing was written.")
            return 1
        out_dir = args.out or project / "output" / f"{args.mod}-plan"
        paths = write_plan(res, project, out_dir, args.force)
    except (RecipeError, behavior.BehaviorError, OSError) as e:
        print("ERROR")
        print(json.dumps({"verdict": "ERROR", "error": str(e)}, indent=2) if args.json else f"  {e}")
        return 2

    print("WROTE")
    if args.json:
        print(json.dumps(dict(report(res), written=[str(p) for p in paths]), indent=2))
        return 0
    for e in res.vanilla:
        print(f"{h.OK}{e['class']} ({e['option']}) {e['root']} at {e['file']}:{e['line']}, addon {e['addon']}")
    for e in res.scripts:
        print(f"{h.OK}{e['symbol']} at {e['file']}:{e['line']}")
    for f in res.fits:
        print(f"{h.OK}{f['what']}")
    for p in paths:
        print(f"{h.OK}Wrote {p}")
    print(f"  Next: have dayz-mod-architect finish {paths[0].name} (it has {len(res.recipe['questions'])} open questions).")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
