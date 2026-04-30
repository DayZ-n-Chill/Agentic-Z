"""dayz-types-edit: Add / update / remove an entry in DayZ types.xml.

Upserts a <type name="..."> block. Backs up to <file>.bak before writing.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT = REPO_ROOT / ".claude" / "skills" / "dayz-preflight" / "preflight.py"

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "

# DayZ defaults for a new <type> entry. 3888000s = 45 days (vanilla typical).
DEFAULTS = {
    "nominal": 1,
    "min": 0,
    "lifetime": 3888000,
    "restock": 0,
    "cost": 100,
}
DEFAULT_FLAGS = {
    "count_in_cargo": "1",
    "count_in_hoarder": "1",
    "count_in_map": "1",
    "count_in_player": "0",
    "crafted": "0",
    "deloot": "0",
}


def _load_preflight():
    spec = importlib.util.spec_from_file_location("dayz_preflight_module", PREFLIGHT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load preflight at {PREFLIGHT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_load_preflight()  # ensure preflight module is importable


def gate_on_preflight() -> None:
    if not PREFLIGHT.exists():
        sys.exit(f"{FAIL} dayz-preflight not found at {PREFLIGHT.relative_to(REPO_ROOT)}")
    result = subprocess.run([sys.executable, str(PREFLIGHT)])
    if result.returncode != 0:
        sys.exit(result.returncode)


def _set_int_child(parent: ET.Element, tag: str, value: int) -> Optional[tuple[str, str]]:
    """Set <tag>value</tag> on parent. Returns (old, new) for diff reporting, or
    None if there was no change."""
    el = parent.find(tag)
    new = str(value)
    if el is None:
        sub = ET.SubElement(parent, tag)
        sub.text = new
        return ("(none)", new)
    old = (el.text or "").strip()
    if old == new:
        return None
    el.text = new
    return (old, new)


def _set_named_singleton(parent: ET.Element, tag: str, name: str) -> Optional[tuple[str, str]]:
    """Set <tag name="name"/> on parent (replacing any existing of same tag)."""
    existing = parent.findall(tag)
    old = existing[0].get("name", "") if existing else "(none)"
    if existing and len(existing) == 1 and existing[0].get("name") == name:
        return None
    for e in existing:
        parent.remove(e)
    el = ET.SubElement(parent, tag)
    el.set("name", name)
    return (old, name)


def _set_named_multi(parent: ET.Element, tag: str, names: list[str]) -> Optional[tuple[list[str], list[str]]]:
    """Replace all <tag name="X"/> children with one per name in `names`."""
    existing = parent.findall(tag)
    old_names = sorted(e.get("name", "") for e in existing)
    new_names = sorted(set(names))
    if old_names == new_names:
        return None
    for e in existing:
        parent.remove(e)
    for n in new_names:
        el = ET.SubElement(parent, tag)
        el.set("name", n)
    return (old_names, new_names)


def _ensure_flags(parent: ET.Element) -> None:
    if parent.find("flags") is not None:
        return
    el = ET.SubElement(parent, "flags")
    for k, v in DEFAULT_FLAGS.items():
        el.set(k, v)


def upsert(root: ET.Element, classname: str, args: argparse.Namespace) -> str:
    """Create or update the <type name="classname"> block. Returns a one-line summary."""
    type_el = next((t for t in root.findall("type") if t.get("name") == classname), None)
    is_new = type_el is None
    if is_new:
        type_el = ET.SubElement(root, "type")
        type_el.set("name", classname)
        # Seed required int children with defaults
        for tag, default in DEFAULTS.items():
            value = getattr(args, tag, None)
            ET.SubElement(type_el, tag).text = str(value if value is not None else default)
        _ensure_flags(type_el)
        if args.category:
            sub = ET.SubElement(type_el, "category")
            sub.set("name", args.category)
        for usage in args.usage or []:
            ET.SubElement(type_el, "usage").set("name", usage)
        for value in args.value or []:
            ET.SubElement(type_el, "value").set("name", value)
        for tag in args.tag or []:
            ET.SubElement(type_el, "tag").set("name", tag)
        return (
            f"Added <type name=\"{classname}\"> "
            f"nominal={args.nominal or DEFAULTS['nominal']}, "
            f"min={args.min or DEFAULTS['min']}, "
            f"lifetime={args.lifetime or DEFAULTS['lifetime']}, "
            f"cost={args.cost or DEFAULTS['cost']}"
        )

    changes: list[str] = []
    for tag in ("nominal", "min", "lifetime", "restock", "cost"):
        value = getattr(args, tag, None)
        if value is None:
            continue
        diff = _set_int_child(type_el, tag, value)
        if diff:
            changes.append(f"{tag} {diff[0]} -> {diff[1]}")
    if args.category:
        diff = _set_named_singleton(type_el, "category", args.category)
        if diff:
            changes.append(f"category {diff[0]} -> {diff[1]}")
    for tag, names in (("usage", args.usage), ("value", args.value), ("tag", args.tag)):
        if names is None:
            continue
        diff = _set_named_multi(type_el, tag, names)
        if diff:
            changes.append(f"{tag}s {diff[0]} -> {diff[1]}")

    if not changes:
        return f"<type name=\"{classname}\"> already matches; no change"
    return f"Updated <type name=\"{classname}\">: " + ", ".join(changes)


def remove(root: ET.Element, classname: str) -> str:
    type_el = next((t for t in root.findall("type") if t.get("name") == classname), None)
    if type_el is None:
        return f"<type name=\"{classname}\"> not found; no change"
    root.remove(type_el)
    return f"Removed <type name=\"{classname}\">"


def main() -> int:
    parser = argparse.ArgumentParser(description="Upsert / remove an entry in DayZ types.xml.")
    parser.add_argument("path", type=Path, help="Path to types.xml.")
    parser.add_argument("classname", help="Class name (the `name` attribute of the <type> block).")
    parser.add_argument("--remove", action="store_true", help="Remove the entry instead of upserting.")
    parser.add_argument("--nominal", type=int)
    parser.add_argument("--min", type=int)
    parser.add_argument("--lifetime", type=int)
    parser.add_argument("--restock", type=int)
    parser.add_argument("--cost", type=int)
    parser.add_argument("--category")
    parser.add_argument("--usage", action="append", help="Repeatable. Replaces all existing usages.")
    parser.add_argument("--value", action="append", help="Repeatable. Replaces all existing values.")
    parser.add_argument("--tag", action="append", help="Repeatable. Replaces all existing tags.")
    args = parser.parse_args()

    gate_on_preflight()
    print()

    if not args.path.exists():
        sys.exit(f"{FAIL} {args.path} not found.")
    try:
        tree = ET.parse(args.path)
    except ET.ParseError as e:
        sys.exit(f"{FAIL} Could not parse {args.path}: {e}")
    root = tree.getroot()

    if args.remove:
        msg = remove(root, args.classname)
    else:
        msg = upsert(root, args.classname, args)
    print(f"{OK} {msg}")

    backup = args.path.with_suffix(args.path.suffix + ".bak")
    shutil.copy2(args.path, backup)
    print(f"{OK} Backup: {backup}")

    tree.write(args.path, encoding="utf-8", xml_declaration=True)
    print(f"{OK} Wrote {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
