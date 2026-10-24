"""dayz-server-kit: zip what a server owner needs to run a mod.

  server_kit.py <ModName> [--mission <folder or instance>] [--deps CF ...] [--out <folder>] [--json]
  server_kit.py --mod-dir <folder> [same options]

Writes output/<ModName>-release/<ModName>-server-kit.zip with:

  <ModName>_ce/types.xml     a types entry for every spawnable class
  cfgeconomycore-lines.xml   the <ce> block that loads that file
  load-order.txt             the -mod= order, dependencies first
  keys/<name>.bikey          the public keys, never a .biprivatekey
  README.txt                 what each file is for

Types entries come from, in order: the mod's own types files (any *.xml under
the mod folder whose root is <types>), then the --mission's db/types.xml and
every types file its cfgeconomycore.xml lists. A spawnable class found in
neither gets a placeholder entry with nominal and min 0, so it does not spawn
until the owner tunes it. Classes, scope, dependencies and keys come from
/dayz-release-pack's mod_facts().

Exit codes: 0 written (warnings allowed), 2 error.
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
SKILLS_DIR = HERE.parent
sys.path.insert(0, str(SKILLS_DIR / "_shared"))
import skill_helpers as h  # noqa: E402

rp = h.load_module("dayz_server_kit_release_pack", SKILLS_DIR / "dayz-release-pack" / "release_pack.py")
ReleaseError = rp.ReleaseError

PRIVATE_SUFFIX = ".biprivatekey"
SKIP_DIRS = {".git", "Addons", "addons", "Keys", "keys", "output"}

# Placeholder entry, in the element order of the vanilla db/types.xml. nominal 0
# and min 0 keep the item out of the loot economy until the owner sets real values.
PLACEHOLDER = """    <type name="{name}">
        <nominal>0</nominal>
        <lifetime>14400</lifetime>
        <restock>0</restock>
        <min>0</min>
        <quantmin>-1</quantmin>
        <quantmax>-1</quantmax>
        <cost>100</cost>
        <flags count_in_cargo="0" count_in_hoarder="0" count_in_map="1" count_in_player="0" crafted="0" deloot="0"/>
    </type>"""


def _types_root(path: Path) -> Optional[ET.Element]:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return None
    return root if root.tag == "types" else None


def mod_types_files(mod_dir: Path) -> list[Path]:
    out = []
    for path in sorted(mod_dir.rglob("*.xml")):
        rel = path.relative_to(mod_dir).parts
        if set(rel[:-1]) & SKIP_DIRS:
            continue
        if _types_root(path) is not None:
            out.append(path)
    return out


def mission_types_files(mission: Path) -> list[Path]:
    """db/types.xml plus every type="types" file cfgeconomycore.xml lists, relative to the mission root."""
    files = [mission / "db" / "types.xml"]
    core = mission / "cfgeconomycore.xml"
    if core.is_file():
        try:
            root = ET.parse(core).getroot()
        except ET.ParseError as e:
            raise ReleaseError(f"{core} does not parse: {e}") from e
        for ce in root.findall("ce"):
            for f in ce.findall("file"):
                if f.get("type") == "types" and f.get("name"):
                    files.append(mission / ce.get("folder", "") / f.get("name"))
    return [f for f in files if f.is_file()]


def resolve_mission(value: Optional[str], roots: list[Path]) -> Optional[Path]:
    """A mission folder, or a test server instance name under <root>/.server/<instance>/mission/.

    The first root that holds the instance wins.
    """
    if not value:
        return None
    path = Path(value)
    if path.is_dir():
        return path.resolve()
    for root in roots:
        if (root / ".server" / value / "mission").is_dir():
            return root / ".server" / value / "mission"
    raise ReleaseError(f"--mission {value!r} is not a folder or a .server/<instance>/ test server")


def instance_roots(mod_dir_given: bool, mod_dir: Path) -> list[Path]:
    """Where a --mission instance name is looked up.

    <ModName> form: the cached project the mod lives in. --mod-dir form: the
    current folder, then the project cached by /dayz-init, if any.
    """
    if not mod_dir_given:
        return [mod_dir.parents[1]]
    roots = [Path.cwd()]
    cached = h.load_module("dayz_init_state_module", h.DAYZ_INIT_STATE).cached_project_root()
    if cached is not None and cached.is_dir():
        roots.append(cached.resolve())
    return roots


def collect_types(facts: dict, mod_dir: Path, mission: Optional[Path]) -> tuple[list[str], dict]:
    """(the <type> blocks as XML text, where each came from)."""
    blocks: list[str] = []
    seen: set[str] = set()
    sources = {"mod": [], "mission": [], "placeholder": []}

    def add(element: ET.Element, source: str) -> None:
        name = element.get("name", "")
        if not name or name.lower() in seen:
            return
        seen.add(name.lower())
        ET.indent(element, space="    ", level=1)
        element.tail = None
        blocks.append("    " + ET.tostring(element, encoding="unicode").rstrip())
        sources[source].append(name)

    for path in mod_types_files(mod_dir):
        for element in _types_root(path).findall("type"):
            add(element, "mod")
    wanted = {c["name"].lower() for c in facts["spawnable"]}
    for path in mission_types_files(mission) if mission else []:
        root = _types_root(path)
        for element in root.findall("type") if root is not None else []:
            if element.get("name", "").lower() in wanted:
                add(element, "mission")
    for c in facts["spawnable"]:
        if c["name"].lower() not in seen:
            seen.add(c["name"].lower())
            blocks.append("    <!-- placeholder values: tune before going live -->\n" + PLACEHOLDER.format(name=c["name"]))
            sources["placeholder"].append(c["name"])
    return blocks, sources


def types_xml(blocks: list[str]) -> str:
    body = "\n".join(blocks)
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<types>\n' + (body + "\n" if body else "") + "</types>\n"


def economycore_lines(mod: str) -> str:
    return (
        f"<!-- Add this block inside <economycore> in the mission's cfgeconomycore.xml. -->\n"
        f"<!-- The folder is relative to the mission folder: put {mod}_ce/ next to db/. -->\n"
        f'<ce folder="{mod}_ce">\n'
        f'    <file name="types.xml" type="types" />\n'
        f"</ce>\n"
    )


def load_order_txt(facts: dict) -> str:
    order = rp.load_order(facts)
    out = [f"Load order for @{facts['mod']}", ""]
    out += [f"{i}. {m}" for i, m in enumerate(order, 1)]
    out += ["", "Launch line:", f"  -mod={';'.join(order)}", ""]
    if facts["non_vanilla_addons"]:
        out.append("config.cpp requires these addons from other mods: " + ", ".join(facts["non_vanilla_addons"]) + ".")
        if not facts["deps"]:
            out.append("Load the mods that ship them before this one.")
        out.append("")
    return "\n".join(out)


def readme_txt(facts: dict, sources: dict, keys: list[str]) -> str:
    mod = facts["mod"]
    out = [
        f"Server kit for {mod}",
        "",
        f"{mod}_ce/types.xml: loot entries for the mod's items. Copy the {mod}_ce folder into your mission folder.",
        f"cfgeconomycore-lines.xml: paste the block inside <economycore> in the mission's cfgeconomycore.xml.",
        "load-order.txt: the order for the -mod= launch parameter.",
    ]
    if keys:
        out.append("keys/: copy each .bikey into the server's keys folder.")
    else:
        out.append("No .bikey is included. Get the key from the mod author before you enable signature checks.")
    if sources["placeholder"]:
        out += ["", "These entries hold placeholder values (nominal 0, so they do not spawn yet). Tune them:"]
        out += [f"  {name}" for name in sources["placeholder"]]
    out.append("")
    return "\n".join(out)


def server_kit(mod: str, mod_dir: Path, out_dir: Path, mission: Optional[Path] = None,
               deps: Optional[list[str]] = None, p_mods: Optional[Path] = rp.P_MODS) -> dict:
    facts = rp.mod_facts(mod, mod_dir, deps, p_mods)
    blocks, sources = collect_types(facts, mod_dir, mission)
    keys = [Path(k) for k in facts["keys"]]  # .bikey only; mod_facts never lists a private key here
    members = {
        f"{mod}_ce/types.xml": types_xml(blocks).encode("utf-8"),
        "cfgeconomycore-lines.xml": economycore_lines(mod).encode("utf-8"),
        "load-order.txt": load_order_txt(facts).encode("utf-8"),
        "README.txt": readme_txt(facts, sources, [k.name for k in keys]).encode("utf-8"),
    }
    for key in keys:
        members[f"keys/{key.name}"] = key.read_bytes()
    # The one rule this kit must never break: a private key would let anyone sign PBOs as the author.
    if any(name.lower().endswith(PRIVATE_SUFFIX) for name in members):
        raise ReleaseError("refusing to zip a .biprivatekey")
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{mod}-server-kit.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
    warnings = list(facts["warnings"])
    if sources["placeholder"]:
        warnings.append(f"placeholder-types: {sources['placeholder']} have no types entry in the mod"
                        + ("" if mission else " (pass --mission to copy real ones)")
                        + "; the kit holds placeholders that do not spawn")
    return {
        "mod": mod,
        "zip": str(zip_path),
        "files": sorted(members),
        "types": sources,
        "load_order": rp.load_order(facts),
        "keys": [k.name for k in keys],
        "mission": str(mission) if mission else None,
        "warnings": warnings,
    }


def render_text(report: dict) -> str:
    t = report["types"]
    out = [f"[OK]   Wrote {report['zip']}"]
    out += [f"       {name}" for name in report["files"]]
    out.append(f"       types: {len(t['mod'])} from the mod, {len(t['mission'])} from the mission, "
               f"{len(t['placeholder'])} placeholders; load order {';'.join(report['load_order'])}")
    out += [f"[WARN] {w}" for w in report["warnings"]]
    return "\n".join(out)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Zip the types entries, cfgeconomycore lines, load order and public keys for server owners.")
    parser.add_argument("mod", nargs="?", help="Mod name under workspace/ in the project cached by /dayz-init.")
    parser.add_argument("--mod-dir", type=Path, help="Use this folder instead (its name is the mod name).")
    parser.add_argument("--mission", help="Mission folder, or a test server instance name, to copy real types entries from.")
    parser.add_argument("--deps", nargs="+", default=[], metavar="MOD", help="Dependency mods in load order (CF or @CF).")
    parser.add_argument("--out", type=Path, help="Output folder. Default output/<ModName>-release/.")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON.")
    try:
        args = parser.parse_args(argv)
        if not args.mod and not args.mod_dir:
            parser.error("give a <ModName> or --mod-dir")
    except SystemExit as e:
        return 0 if e.code == 0 else 2
    try:
        mod, mod_dir, out_dir = rp.resolve_mod(args.mod, args.mod_dir, args.out)
        mission = resolve_mission(args.mission, instance_roots(bool(args.mod_dir), mod_dir) if args.mission else [])
        report = server_kit(mod, mod_dir, out_dir, mission, args.deps)
    except (ReleaseError, OSError, ValueError) as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"[FAIL] {e}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2) if args.json else render_text(report))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
