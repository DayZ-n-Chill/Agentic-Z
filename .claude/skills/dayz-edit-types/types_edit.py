"""dayz-edit-types: Add / update / remove an entry in DayZ types.xml.

Upserts or removes a <type name="..."> block. When the edit changes the file,
backs it up to <file>.bak first; when nothing changes, writes nothing.
Comments survive the round trip; the file is re-indented with 4 spaces.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
from collections import Counter
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

OK = h.OK
WARN = h.WARN
FAIL = h.FAIL

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


def upsert(root: ET.Element, classname: str, args: argparse.Namespace) -> tuple[bool, str]:
    """Create or update the <type name="classname"> block.

    Returns (changed, one-line summary).
    """
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
        if args.category is not None:
            sub = ET.SubElement(type_el, "category")
            sub.set("name", args.category)
        for usage in args.usage or []:
            ET.SubElement(type_el, "usage").set("name", usage)
        for value in args.value or []:
            ET.SubElement(type_el, "value").set("name", value)
        for tag in args.tag or []:
            ET.SubElement(type_el, "tag").set("name", tag)
        summary = ", ".join(
            f"{tag}={type_el.findtext(tag)}" for tag in ("nominal", "min", "lifetime", "cost")
        )
        return True, f"Added <type name=\"{classname}\"> {summary}"

    changes: list[str] = []
    for tag in ("nominal", "min", "lifetime", "restock", "cost"):
        value = getattr(args, tag, None)
        if value is None:
            continue
        diff = _set_int_child(type_el, tag, value)
        if diff:
            changes.append(f"{tag} {diff[0]} -> {diff[1]}")
    if args.category is not None:
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
        return False, f"<type name=\"{classname}\"> already matches; no change"
    return True, f"Updated <type name=\"{classname}\">: " + ", ".join(changes)


def min_exceeds_nominal(root: ET.Element, classname: str) -> Optional[tuple[int, int]]:
    """(min, nominal) when the entry's min is above its nominal, else None."""
    type_el = next((t for t in root.findall("type") if t.get("name") == classname), None)
    if type_el is None:
        return None
    try:
        lo, hi = int(type_el.findtext("min", "0")), int(type_el.findtext("nominal", "0"))
    except ValueError:
        return None  # a hand-edited non-number is left for the user to fix
    return (lo, hi) if lo > hi else None


def non_negative_int(text: str) -> int:
    """argparse type: an int >= 0 (counts, seconds and cost are never negative)."""
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid int value: {text!r}")
    if value < 0:
        raise argparse.ArgumentTypeError(f"must be 0 or more, got {value}")
    return value


def remove(root: ET.Element, classname: str) -> tuple[bool, str]:
    """Delete the <type name="classname"> block. Returns (changed, summary)."""
    type_el = next((t for t in root.findall("type") if t.get("name") == classname), None)
    if type_el is None:
        return False, f"<type name=\"{classname}\"> not found; no change"
    root.remove(type_el)
    return True, f"Removed <type name=\"{classname}\">"


def duplicate_names(root: ET.Element) -> list[str]:
    """<type> names that appear more than once, sorted."""
    counts = Counter(t.get("name") for t in root.findall("type"))
    return sorted(name for name, n in counts.items() if name is not None and n > 1)


def check_types_root(root: ET.Element, path: Path, classname: str) -> None:
    """Refuse a file that is not a types.xml or whose target entry is ambiguous.

    Other files under a mission's db/ (events.xml, globals.xml) parse fine but
    have a different root, and an edit would graft a <type> into them. A name
    listed twice cannot be edited safely: only the first block would change.
    """
    if root.tag != "types":
        sys.exit(f"{FAIL} {path} has root element <{root.tag}>, not <types>; refusing to edit it.")
    dups = duplicate_names(root)
    if classname in dups:
        sys.exit(
            f"{FAIL} {path} has more than one <type name=\"{classname}\">.\n"
            "       Merge them by hand into one block, then rerun."
        )
    if dups:
        print(f"{WARN} {path} lists these types more than once: {', '.join(dups)}")


def parse_types(path: Path) -> ET.ElementTree:
    """Parse types.xml keeping comments (the default parser drops them)."""
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    return ET.parse(path, parser=parser)


def write_types(tree: ET.ElementTree, path: Path) -> None:
    """Write types.xml re-indented with 4 spaces, with an XML declaration."""
    ET.indent(tree, space="    ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Upsert / remove an entry in DayZ types.xml.")
    parser.add_argument("path", type=Path, help="Path to types.xml.")
    parser.add_argument("classname", help="Class name (the `name` attribute of the <type> block).")
    parser.add_argument(
        "--remove", action="store_true",
        help="Remove the entry instead of upserting. Field flags (--nominal, --usage, ...) are ignored.",
    )
    parser.add_argument("--nominal", type=non_negative_int)
    parser.add_argument("--min", type=non_negative_int)
    parser.add_argument("--lifetime", type=non_negative_int)
    parser.add_argument("--restock", type=non_negative_int)
    parser.add_argument("--cost", type=non_negative_int)
    parser.add_argument("--category")
    parser.add_argument("--usage", action="append", help="Repeatable. Replaces all existing usages.")
    parser.add_argument("--value", action="append", help="Repeatable. Replaces all existing values.")
    parser.add_argument("--tag", action="append", help="Repeatable. Replaces all existing tags.")
    args = parser.parse_args()

    h.gate_on_preflight()
    print()

    if not args.path.exists():
        sys.exit(f"{FAIL} {args.path} not found.")
    try:
        tree = parse_types(args.path)
    except ET.ParseError as e:
        sys.exit(f"{FAIL} Could not parse {args.path}: {e}")
    root = tree.getroot()
    check_types_root(root, args.path, args.classname)

    if args.remove:
        changed, msg = remove(root, args.classname)
    else:
        changed, msg = upsert(root, args.classname, args)
        if args.min is not None or args.nominal is not None:
            bad = min_exceeds_nominal(root, args.classname)
            if bad:
                sys.exit(
                    f"{FAIL} min ({bad[0]}) would be greater than nominal ({bad[1]}) for {args.classname}.\n"
                    f"       Pass values with min <= nominal. {args.path} was not changed."
                )
    print(f"{OK} {msg}")
    if not changed:
        return 0

    backup = args.path.with_suffix(args.path.suffix + ".bak")
    shutil.copy2(args.path, backup)
    print(f"{OK} Backup: {backup}")

    write_types(tree, args.path)
    print(f"{OK} Wrote {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
