"""dayz-edit-types: Add / update / remove an entry in DayZ types.xml.

Upserts or removes a <type name="..."> block, or with --merge checks every
<type> in a pasted chunk and merges them all in one write. When the edit
changes the file, backs it up to <file>.<stamp>.bak first; when nothing
changes, writes nothing. Only the <type> blocks that changed are rewritten;
every other byte of the file (declaration, comments, other blocks, line
endings) is kept as it was.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from datetime import datetime
import os
import re
import shutil
import stat
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

OK = h.OK
WARN = h.WARN
FAIL = h.FAIL

# DayZ defaults for a new <type> entry. 14400 s = 4 h, the most common vanilla loot lifetime (chernarusplus types.xml).
# The key order is the vanilla child order (nominal, lifetime, restock, min, quantmin,
# quantmax, cost), so a new block reads like its neighbours.
DEFAULTS = {
    "nominal": 1,
    "lifetime": 14400,
    "restock": 0,
    "min": 0,
    # -1 means "not a quantity item"; every vanilla <type> carries both tags.
    "quantmin": -1,
    "quantmax": -1,
    "cost": 100,
}
DEFAULT_FLAGS = {
    "count_in_cargo": "0",
    "count_in_hoarder": "0",
    "count_in_map": "1",
    "count_in_player": "0",
    "crafted": "0",
    "deloot": "0",
}


# Vanilla child order of a <type>: tag sits between category and usage
# (chernarusplus types.xml, for example <category name="tools"/><tag name="shelves"/><usage .../>).
CHILD_ORDER = (*DEFAULTS, "flags", "category", "tag", "usage", "value")


def _insert_ordered(parent: ET.Element, el: ET.Element) -> None:
    """Insert el after the last child that comes no later in CHILD_ORDER."""
    rank = CHILD_ORDER.index(el.tag)
    pos = 0
    for i, child in enumerate(parent):
        if child.tag in CHILD_ORDER and CHILD_ORDER.index(child.tag) <= rank:
            pos = i + 1
    parent.insert(pos, el)


def _add_named(parent: ET.Element, tag: str, name: str) -> None:
    """Insert <tag name="name"/> in its vanilla place among the children."""
    el = ET.Element(tag)
    el.set("name", name)
    _insert_ordered(parent, el)


def _set_int_child(parent: ET.Element, tag: str, value: int) -> Optional[tuple[str, str]]:
    """Set <tag>value</tag> on parent. Returns (old, new) for diff reporting, or
    None if there was no change."""
    el = parent.find(tag)
    new = str(value)
    if el is None:
        sub = ET.Element(tag)
        sub.text = new
        _insert_ordered(parent, sub)
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
    _add_named(parent, tag, name)
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
        _add_named(parent, tag, n)
    return (old_names, new_names)


def _ensure_flags(parent: ET.Element) -> None:
    if parent.find("flags") is not None:
        return
    el = ET.SubElement(parent, "flags")
    for k, v in DEFAULT_FLAGS.items():
        el.set(k, v)


def find_type(root: ET.Element, classname: str) -> Optional[ET.Element]:
    r"""The <type> block whose name matches classname ignoring case, or None.

    DayZ class names are case-insensitive: vanilla chernarusplus types.xml lists
    <type name="Bandana_Blackpattern"> (P:\DZ\worlds\chernarusplus\ce\db\types.xml:3036)
    for config class Bandana_BlackPattern (P:\DZ\characters\headgear\config.cpp:3084)
    and Camonet (types.xml:4607) for CamoNet (P:\DZ\gear\camping\config.cpp:9808).
    So `akm` must find the existing AKM block, never add a second one.
    """
    key = classname.casefold()
    return next((t for t in root.findall("type") if (t.get("name") or "").casefold() == key), None)


def upsert(root: ET.Element, classname: str, args: argparse.Namespace) -> tuple[bool, str]:
    """Create or update the <type name="classname"> block.

    Returns (changed, one-line summary).
    """
    type_el = find_type(root, classname)
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
        for tag in args.tag or []:
            ET.SubElement(type_el, "tag").set("name", tag)
        for usage in args.usage or []:
            ET.SubElement(type_el, "usage").set("name", usage)
        for value in args.value or []:
            ET.SubElement(type_el, "value").set("name", value)
        summary = ", ".join(
            f"{tag}={type_el.findtext(tag)}" for tag in ("nominal", "min", "lifetime", "cost")
        )
        return True, f"Added <type name=\"{classname}\"> {summary}"

    classname = type_el.get("name")  # report the file's own spelling
    changes: list[str] = []
    for tag in ("nominal", "min", "lifetime", "restock", "quantmin", "quantmax", "cost"):
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
            old, new = diff
            removed = [n for n in old if n not in new]
            line = f"{tag} [{', '.join(old)}] -> [{', '.join(new)}]"
            if removed:
                line += f" (removed {', '.join(removed)})"
            changes.append(line)

    if not changes:
        return False, f"<type name=\"{classname}\"> already matches; no change"
    return True, f"Updated <type name=\"{classname}\">: " + ", ".join(changes)


def min_exceeds_nominal(root: ET.Element, classname: str) -> Optional[tuple[int, int]]:
    """(min, nominal) when the entry's min is above its nominal, else None."""
    type_el = find_type(root, classname)
    if type_el is None:
        return None
    try:
        lo, hi = int(type_el.findtext("min", "0")), int(type_el.findtext("nominal", "0"))
    except ValueError:
        return None  # a hand-edited non-number is left for the user to fix
    return (lo, hi) if lo > hi else None


def quantmin_exceeds_quantmax(root: ET.Element, classname: str) -> Optional[tuple[int, int]]:
    """(quantmin, quantmax) when both are set (not -1) and quantmin is above quantmax, else None."""
    type_el = find_type(root, classname)
    if type_el is None:
        return None
    try:
        lo, hi = int(type_el.findtext("quantmin", "-1")), int(type_el.findtext("quantmax", "-1"))
    except ValueError:
        return None  # a hand-edited non-number is left for the user to fix
    return (lo, hi) if lo != -1 and hi != -1 and lo > hi else None


def half_set_quant(el: ET.Element) -> Optional[str]:
    r"""A warning when exactly one of quantmin and quantmax is -1, else None.

    -1 on both means "not a quantity item"; a quantity item sets both. No
    vanilla entry mixes them: all 2382 / 2391 / 2404 entries with both tags in
    P:\DZ\worlds\{chernarusplus,enoch,sakhal}\ce\db\types.xml have both -1 or
    both set (counted with ElementTree). A missing or non-number tag is left to
    the other checks.
    """
    try:
        qmin, qmax = int(el.findtext("quantmin").strip()), int(el.findtext("quantmax").strip())
    except (AttributeError, ValueError):
        return None
    if (qmin == -1) == (qmax == -1):
        return None
    return (f"quantmin is {qmin} but quantmax is {qmax}; vanilla sets both to -1 "
            "(not a quantity item) or both to 0 to 100")


def non_blank(text: str) -> str:
    """argparse type for ClassName, --category, --usage, --value and --tag: a
    name that is not empty or only whitespace (the merge check rejects those too)."""
    if not text.strip():
        raise argparse.ArgumentTypeError("must not be empty")
    return text


def quant_value(text: str) -> int:
    """argparse type for --quantmin / --quantmax: -1 (not a quantity item) or 0 to 100,
    the same rule the merge check applies."""
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid int value: {text!r}")
    if value != -1 and not 0 <= value <= 100:
        raise argparse.ArgumentTypeError(f"must be -1 or 0 to 100, got {value}")
    return value


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
    type_el = find_type(root, classname)
    if type_el is None:
        return False, f"<type name=\"{classname}\"> not found; no change"
    root.remove(type_el)
    return True, f"Removed <type name=\"{type_el.get('name')}\">"


def duplicate_names(root: ET.Element) -> list[str]:
    """<type> names that appear more than once ignoring case (see find_type),
    sorted, each as its first block spells it."""
    first: dict[str, str] = {}
    counts: Counter = Counter()
    for t in root.findall("type"):
        name = t.get("name")
        if name is None:
            continue
        first.setdefault(name.casefold(), name)
        counts[name.casefold()] += 1
    return sorted(first[key] for key, n in counts.items() if n > 1)


def check_types_root(root: ET.Element, path: Path, classname: str) -> None:
    """Refuse a file that is not a types.xml or whose target entry is ambiguous.

    Other files under a mission's db/ (events.xml, globals.xml) parse fine but
    have a different root, and an edit would graft a <type> into them. A name
    listed twice cannot be edited safely: only the first block would change.
    """
    if root.tag != "types":
        sys.exit(f"{FAIL} {path} has root element <{root.tag}>, not <types>; refusing to edit it.")
    dups = duplicate_names(root)
    if classname.casefold() in {d.casefold() for d in dups}:
        sys.exit(
            f"{FAIL} {path} has more than one <type name=\"{classname}\">.\n"
            "       Merge them by hand into one block, then rerun."
        )
    if dups:
        print(f"{WARN} {path} lists these types more than once: {', '.join(dups)}")


# The children every vanilla <type> has. A missing one is a warning: the
# economy loads the entry, but it is easy to have dropped one by accident.
STANDARD_CHILDREN = ("nominal", "lifetime", "restock", "min", "quantmin", "quantmax", "cost", "flags")
INT_CHILDREN = ("nominal", "lifetime", "restock", "min", "cost")
NAMED_CHILDREN = ("category", "usage", "value", "tag")
FLAG_NAMES = tuple(DEFAULT_FLAGS)

# The mission files that define the names a <type> may use. They sit next to
# db/ in every vanilla mission; a name they do not define is ignored by the
# Central Economy.
LIMITS_FILE = "cfglimitsdefinition.xml"
LIMITS_USER_FILE = "cfglimitsdefinitionuser.xml"
# Section of cfglimitsdefinition.xml (and of the user file) for each child tag.
LIMITS_SECTIONS = {"category": "categories", "usage": "usageflags", "value": "valueflags", "tag": "tags"}


def load_limits(types_path: Path) -> Optional[dict[str, dict[str, set[str]]]]:
    """Names defined by <types.xml>/../../cfglimitsdefinition.xml, as
    {"name": {tag: names}, "user": {tag: group names}}. The user file is
    optional: without it the "user" key is left out and user= is not checked. Returns None (after a note) when the main file is absent or
    cannot be read, so the check is skipped."""
    mission = types_path.resolve().parent.parent
    main_file = mission / LIMITS_FILE
    if not main_file.is_file():
        print(f"{OK} No {LIMITS_FILE} at {main_file}; category, usage, value and tag names not checked.")
        return None
    limits: dict[str, dict[str, set[str]]] = {"name": {}, "user": {}}
    for kind, file, child in (("name", main_file, None), ("user", mission / LIMITS_USER_FILE, "user")):
        if not file.is_file():
            del limits[kind]  # no user file: user= groups are not checked
            continue
        try:
            root = ET.parse(file).getroot()
        except ET.ParseError as e:
            print(f"{WARN} Could not parse {file}: {e}; names not checked against it.")
            if kind == "name":
                return None
            del limits[kind]
            continue
        for tag, section in LIMITS_SECTIONS.items():
            limits[kind][tag] = {
                el.get("name") for el in root.findall(f"{section}/{child or tag}") if el.get("name")
            }
    return limits


def undefined_limit_names(el: ET.Element, limits: dict[str, dict[str, set[str]]]) -> list[str]:
    """One message per category, usage, value or tag name of a <type> that the
    mission's limits files do not define. name= is checked against
    cfglimitsdefinition.xml, user= against the user file's groups."""
    problems = []
    for child in el:
        if child.tag not in LIMITS_SECTIONS:
            continue
        for attr, file in (("name", LIMITS_FILE), ("user", LIMITS_USER_FILE)):
            value = child.get(attr)
            if value and attr in limits and value not in limits[attr].get(child.tag, set()):
                problems.append(f'{child.tag} {attr} "{value}" is not defined in {file}')
    return problems


_DECL_RE = re.compile(r"^\s*<\?xml[^>]*\?>", re.IGNORECASE)
_TYPES_TAG_RE = re.compile(r"</?types\b[^>]*>", re.IGNORECASE)


def parse_chunk(text: str) -> list[ET.Element]:
    """The <type> elements of a pasted chunk: bare <type> blocks, or a whole
    <types> file, with or without an XML declaration. Raises ET.ParseError."""
    body = _TYPES_TAG_RE.sub("", _DECL_RE.sub("", text))
    root = ET.fromstring(f"<types>{body}</types>")
    stray = sorted({el.tag for el in root if el.tag != "type"})
    if stray:
        raise ET.ParseError(f"the chunk holds <{'>, <'.join(stray)}> where only <type> blocks belong")
    return root.findall("type")


def _int_text(el: ET.Element, tag: str) -> Optional[int]:
    text = el.findtext(tag)
    return None if text is None else int(text.strip())


def validate_type(el: ET.Element) -> tuple[list[str], list[str]]:
    """(errors, warnings) for one <type>. Any error stops the merge."""
    errors: list[str] = []
    warnings: list[str] = []
    if not (el.get("name") or "").strip():
        return ["a <type> has no name attribute"], warnings
    for tag in STANDARD_CHILDREN:
        if el.find(tag) is None:
            warnings.append(f"no <{tag}>")
    numbers: dict[str, int] = {}
    for tag in INT_CHILDREN + ("quantmin", "quantmax"):
        try:
            value = _int_text(el, tag)
        except ValueError:
            errors.append(f"<{tag}> is not a whole number: {el.findtext(tag)!r}")
            continue
        if value is None:
            continue
        numbers[tag] = value
        if tag in INT_CHILDREN and value < 0:
            errors.append(f"<{tag}> is negative ({value})")
    if "min" in numbers and "nominal" in numbers and numbers["min"] > numbers["nominal"]:
        errors.append(f"min ({numbers['min']}) is greater than nominal ({numbers['nominal']})")
    for tag in ("quantmin", "quantmax"):
        value = numbers.get(tag)
        if value is not None and value != -1 and not 0 <= value <= 100:
            errors.append(f"<{tag}> must be -1 or 0 to 100, got {value}")
    qmin, qmax = numbers.get("quantmin", -1), numbers.get("quantmax", -1)
    if qmin != -1 and qmax != -1 and qmin > qmax:
        errors.append(f"quantmin ({qmin}) is greater than quantmax ({qmax})")
    half = half_set_quant(el)
    if half:
        warnings.append(half)
    flags = el.find("flags")
    if flags is not None:
        for key, value in flags.attrib.items():
            if key not in FLAG_NAMES:
                warnings.append(f"unknown flag {key}")
            elif value not in ("0", "1"):
                errors.append(f"flag {key} must be 0 or 1, got {value!r}")
    for child in el:
        if child.tag in NAMED_CHILDREN and not (child.get("name") or "").strip():
            errors.append(f"<{child.tag}> has no name attribute")
        elif child.tag not in STANDARD_CHILDREN + NAMED_CHILDREN:
            warnings.append(f"unknown element <{child.tag}>")
    return errors, warnings


def _canonical(el: ET.Element) -> tuple:
    """Content of an element, ignoring whitespace, comments and child order."""
    children = sorted(_canonical(c) for c in el if isinstance(c.tag, str))
    return (el.tag, tuple(sorted(el.attrib.items())), (el.text or "").strip(), tuple(children))


def _int_diff(old: ET.Element, new: ET.Element) -> list[str]:
    changes = []
    for tag in INT_CHILDREN + ("quantmin", "quantmax"):
        a = (old.findtext(tag) or "").strip() or "(none)"
        b = (new.findtext(tag) or "").strip() or "(none)"
        if a != b:
            changes.append(f"{tag} {a} -> {b}")
    return changes


def merge(root: ET.Element, chunk: list[ET.Element]) -> tuple[bool, list[str]]:
    """Merge checked <type> blocks into root: a new name is appended, a known
    name has its block replaced in place, an identical block is left alone.
    Returns (changed, one line per entry)."""
    changed = False
    lines: list[str] = []
    for new in chunk:
        children = list(root)
        old = find_type(root, new.get("name"))
        if old is not None:
            new.set("name", old.get("name"))  # keep the file's spelling; names ignore case
        name = new.get("name")
        if old is None:
            root.append(new)
            lines.append(f"Added <type name=\"{name}\">")
            changed = True
        elif _canonical(old) == _canonical(new):
            lines.append(f"<type name=\"{name}\"> already matches; no change")
        else:
            diff = _int_diff(old, new)
            index = children.index(old)
            root.remove(old)
            root.insert(index, new)
            detail = ": " + ", ".join(diff) if diff else " (its lists or flags changed)"
            lines.append(f"Replaced <type name=\"{name}\">{detail}")
            changed = True
    return changed, lines


def check_chunk(chunk: list[ET.Element], root: ET.Element, path: Path) -> list[str]:
    """Validate every entry of a chunk and exit listing all errors if there are any.
    Returns the warnings, one line each."""
    if not chunk:
        sys.exit(f"{FAIL} The chunk has no <type> blocks; {path} was not changed.")
    errors: list[str] = []
    warnings: list[str] = []
    first: dict[str, str] = {}
    counts: Counter = Counter()
    for el in chunk:
        if el.get("name"):
            first.setdefault(el.get("name").casefold(), el.get("name"))
            counts[el.get("name").casefold()] += 1
    for key in sorted(k for k, c in counts.items() if c > 1):
        errors.append(f"{first[key]}: listed {counts[key]} times in the chunk (names ignore case)")
    file_dups = {d.casefold() for d in duplicate_names(root)}
    for el in chunk:
        name = el.get("name") or "(no name)"
        errs, warns = validate_type(el)
        if name.casefold() in file_dups:
            errs.append(f"{path} already has more than one <type name=\"{name}\">; merge them by hand first")
        errors += [f"{name}: {e}" for e in errs]
        warnings += [f"{name}: {w}" for w in warns]
    if errors:
        sys.exit(
            f"{FAIL} The chunk has {len(errors)} problem(s); {path} was not changed.\n"
            + "\n".join(f"       {e}" for e in errors)
        )
    return warnings


COMMENT_RE = re.compile(r"<!--(.*?)-->", re.DOTALL)
# What may stand before the root element: the XML declaration, a DOCTYPE,
# processing instructions, comments and whitespace.
PROLOG_RE = re.compile(r"\A(?:\s+|<\?.*?\?>|<!DOCTYPE[^>]*>|<!--.*?-->)*", re.DOTALL)


# The encoding="..." of an XML declaration, read from the raw bytes (the
# declaration itself is ASCII in every ASCII-compatible encoding).
ENCODING_DECL_RE = re.compile(rb"""\s*<\?xml\b[^>]*?\bencoding\s*=\s*["']([A-Za-z0-9._-]+)["']""")


def declared_encoding(source: bytes) -> str:
    """The encoding the file declares, as the XML parser reads it: a UTF-16
    byte-order mark wins, then encoding="..." in the declaration, else UTF-8."""
    if source.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16"
    m = ENCODING_DECL_RE.match(source.removeprefix(b"\xef\xbb\xbf"))
    return m.group(1).decode("ascii").lower() if m else "utf-8"


def _decode(source: bytes) -> str:
    """The source text in its declared encoding. utf-8-sig drops the BOM that
    Windows editors (and PowerShell 5.1) often put at the start of the file."""
    enc = declared_encoding(source)
    return source.decode("utf-8-sig" if enc in ("utf-8", "utf8") else enc, errors="replace")


def _outer_comments(path: Path, root_tag: str) -> tuple[list[str], list[str]]:
    """Comments before and after the root element.

    TreeBuilder(insert_comments=True) keeps only comments inside the root, so a
    header such as <!-- MyMod types --> above <types> would be lost on write.
    """
    text = _decode(path.read_bytes())
    prolog = PROLOG_RE.match(text).group(0)
    close = text.rfind(f"</{root_tag}>")
    epilog = text[close + len(root_tag) + 3:] if close >= 0 else ""
    return COMMENT_RE.findall(prolog), COMMENT_RE.findall(epilog)


def parse_types(path: Path) -> ET.ElementTree:
    """Parse types.xml keeping comments, including those outside the root.

    Also records the source bytes and, for each <type> element, its original
    serialization, so write_types can rewrite only the blocks that changed.
    """
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    tree = ET.parse(path, parser=parser)
    tree.outer_comments = _outer_comments(path, tree.getroot().tag)
    tree.source = path.read_bytes()
    tree.originals = [(el, ET.tostring(el)) for el in tree.getroot().findall("type")]
    return tree


# A <type> block in the source text (comments blanked first, so a commented-out
# block is not matched). Types never nest, so the lazy match ends at its own </type>.
TYPE_SPAN_RE = re.compile(r"<type\b[^>]*?/>|<type\b[^>]*>.*?</type\s*>", re.DOTALL)
# ElementTree writes <a b="c" />; vanilla types.xml writes <a b="c"/>.
SELF_CLOSE_RE = re.compile(r"(<[^<>!?][^<>]*?) />")


def _render(el: ET.Element, indent: str, step: str, nl: str) -> str:
    """One <type> block in the file's own style. The first line carries no
    indent (the text before the block already has it)."""
    el = copy.deepcopy(el)
    el.tail = None
    ET.indent(el, space=step)
    text = SELF_CLOSE_RE.sub(r"\1/>", ET.tostring(el, encoding="unicode"))
    return text.replace("\n", nl + indent)


def _line_indent(text: str, pos: int) -> Optional[str]:
    """The whitespace from the start of pos's line to pos, or None if other text is there."""
    head = text[text.rfind("\n", 0, pos) + 1:pos]
    return head if not head.strip() else None


def _splice(tree: ET.ElementTree) -> Optional[str]:
    """The source text with only the changed, added and removed <type> blocks
    rewritten, or None when the source cannot be patched block by block (bytes
    not valid in the declared encoding, a self-closing <types/>, or blocks the
    scan cannot pair up). A UTF-8 BOM stays in the text, so it is written back."""
    try:
        text = tree.source.decode(declared_encoding(tree.source))
    except UnicodeDecodeError:
        return None
    blanked = re.sub(r"<!--.*?-->", lambda m: " " * len(m.group()), text, flags=re.DOTALL)
    root_tag = tree.getroot().tag
    open_m = re.search(rf"<{root_tag}\b[^>]*>", blanked)
    close = blanked.rfind(f"</{root_tag}")
    if open_m is None or open_m.group().endswith("/>") or close < 0:
        return None
    spans = [m.span() for m in TYPE_SPAN_RE.finditer(blanked, open_m.end(), close)]
    if len(spans) != len(tree.originals):
        return None

    nl = "\r\n" if "\r\n" in text else "\n"
    indent = (_line_indent(text, spans[0][0]) if spans else None) or "    "
    step = "    "
    if spans:
        child = re.search(r"\n([ \t]*)<", text[spans[0][0]:spans[0][1]])
        if child and child.group(1).startswith(indent) and len(child.group(1)) > len(indent):
            step = child.group(1)[len(indent):]

    known = {id(el): (i, before) for i, (el, before) in enumerate(tree.originals)}
    kept: set[int] = set()
    ops: list[tuple[int, int, str]] = []  # (start, end, replacement) on the source text
    anchor: Optional[int] = None  # end of the last kept block
    pending: list[ET.Element] = []

    def flush(at_start: Optional[int]) -> None:
        if not pending:
            return
        blocks = [_render(el, indent, step, nl) for el in pending]
        if anchor is not None:
            ops.append((anchor, anchor, "".join(nl + indent + b for b in blocks)))
        elif at_start is not None:
            ops.append((at_start, at_start, "".join(b + nl + indent for b in blocks)))
        else:  # no kept block at all: put them just inside the closing tag
            pos = close
            head = _line_indent(text, pos)
            if head is not None:
                pos -= len(head)
                ops.append((pos, pos, "".join(indent + b + nl for b in blocks)))
            else:
                ops.append((pos, pos, "".join(nl + indent + b for b in blocks) + nl))
        pending.clear()

    for el in tree.getroot().findall("type"):
        if id(el) not in known:
            pending.append(el)
            continue
        i, before = known[id(el)]
        start, end = spans[i]
        flush(start)
        kept.add(i)
        if ET.tostring(el) != before:
            ops.append((start, end, _render(el, _line_indent(text, start) or indent, step, nl)))
        anchor = end
    flush(None)

    for i, (start, end) in enumerate(spans):
        if i in kept:
            continue
        head = _line_indent(text, start)
        if head is not None and text.startswith(nl, end):
            start, end = start - len(head), end + len(nl)
        ops.append((start, end, ""))

    # Apply from the end so earlier offsets stay valid; at a shared start the
    # removal (the longer span) goes first so it never eats an insertion.
    for start, end, repl in sorted(ops, key=lambda op: (op[0], op[1]), reverse=True):
        text = text[:start] + repl + text[end:]
    return text


def write_types(tree: ET.ElementTree, path: Path) -> None:
    """Write types.xml, rewriting only the <type> blocks that changed.

    A tree that cannot be patched block by block (see _splice) is written
    whole, re-indented with 4 spaces, keeping the original XML declaration.
    Either way the bytes are written in the encoding the declaration names, so
    an ISO-8859-1 file stays ISO-8859-1; a character that encoding cannot hold
    is written as a character reference (&#233;).
    """
    raw = getattr(tree, "source", b"")
    encoding = declared_encoding(raw)
    spliced = _splice(tree) if hasattr(tree, "source") else None
    if spliced is not None:
        path.write_bytes(spliced.encode(encoding, errors="xmlcharrefreplace"))
        return
    ET.indent(tree, space="    ")
    before, after = getattr(tree, "outer_comments", ([], []))
    source = _decode(raw)
    decl = re.match(r"\s*(<\?xml\b.*?\?>)", source, re.DOTALL)
    out = (decl.group(1) if decl else '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>') + "\n"
    out += "".join(f"<!--{c}-->\n" for c in before)
    out += SELF_CLOSE_RE.sub(r"\1/>", ET.tostring(tree.getroot(), encoding="unicode"))
    out += "".join(f"\n<!--{c}-->" for c in after)
    path.write_bytes(out.encode(encoding, errors="xmlcharrefreplace"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Upsert / remove an entry in DayZ types.xml.")
    parser.add_argument("path", type=Path, help="Path to types.xml.")
    parser.add_argument("classname", nargs="?", type=non_blank,
                        help="Class name (the `name` attribute of the <type> block).")
    parser.add_argument(
        "--merge", metavar="CHUNK",
        help="Check every <type> in a pasted chunk (a file, or - for stdin) and merge them all.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Check and report the change, write nothing.")
    parser.add_argument(
        "--remove", action="store_true",
        help="Remove the entry instead of upserting. Field flags (--nominal, --usage, ...) are ignored.",
    )
    parser.add_argument("--nominal", type=non_negative_int)
    parser.add_argument("--min", type=non_negative_int)
    parser.add_argument("--lifetime", type=non_negative_int)
    parser.add_argument("--restock", type=non_negative_int)
    parser.add_argument("--quantmin", type=quant_value, help="-1 (not a quantity item) or 0 to 100.")
    parser.add_argument("--quantmax", type=quant_value, help="-1 (not a quantity item) or 0 to 100.")
    parser.add_argument("--cost", type=non_negative_int)
    parser.add_argument("--category", type=non_blank)
    parser.add_argument("--usage", action="append", type=non_blank,
                        help="Repeatable. Sets the usages; any others are removed.")
    parser.add_argument("--value", action="append", type=non_blank,
                        help="Repeatable. Sets the values; any others are removed.")
    parser.add_argument("--tag", action="append", type=non_blank,
                        help="Repeatable. Sets the tags; any others are removed.")
    args = parser.parse_args()
    if (args.classname is None) == (args.merge is None):
        parser.error("give a ClassName, or --merge CHUNK (not both)")

    h.gate_on_preflight()
    print()

    if not args.path.exists():
        sys.exit(f"{FAIL} {args.path} not found.")
    try:
        tree = parse_types(args.path)
    except ET.ParseError as e:
        sys.exit(f"{FAIL} Could not parse {args.path}: {e}")
    root = tree.getroot()

    if args.merge is not None:
        return run_merge(tree, args)

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
        if args.quantmin is not None or args.quantmax is not None:
            bad = quantmin_exceeds_quantmax(root, args.classname)
            if bad:
                sys.exit(
                    f"{FAIL} quantmin ({bad[0]}) would be greater than quantmax ({bad[1]}) for {args.classname}.\n"
                    f"       Pass values with quantmin <= quantmax. {args.path} was not changed."
                )
    print(f"{OK} {msg}")
    if not args.remove:
        target = find_type(root, args.classname)
        half = half_set_quant(target)
        if half:
            print(f"{WARN} {target.get('name')}: {half}. Pass --quantmin and --quantmax together.")
        limits = load_limits(args.path)
        for problem in undefined_limit_names(target, limits) if limits else []:
            print(f"{WARN} {problem}")
    if args.dry_run:
        print(f"{OK} Dry run: {args.path} was not changed.")
    elif changed:
        backup_and_write(tree, args.path)
    return 0


def backup_path(path: Path) -> Path:
    """<name>.<YYYYMMDD-HHMMSS>.bak beside the file, with a counter if that is
    taken, so every changing run keeps its own backup (as /dayz-split-types does)."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = path.with_name(f"{path.name}.{stamp}.bak")
    n = 2
    while dest.exists():
        dest = path.with_name(f"{path.name}.{stamp}-{n}.bak")
        n += 1
    return dest


def _discard(backup: Path) -> bool:
    """Delete a backup this run made. copy2 copies a read-only flag, which
    blocks deletion on Windows, so clear it first. Returns False if it stays."""
    try:
        if backup.exists():
            os.chmod(backup, stat.S_IWRITE | stat.S_IREAD)
            backup.unlink()
        return True
    except OSError:
        return False


def backup_and_write(tree: ET.ElementTree, path: Path) -> None:
    """Back the file up, then write it. A file that is read-only, locked or on a
    full disk stops with a [FAIL] line and exit 1, not a traceback; a backup
    left over from the failed run is removed when the file is unchanged."""
    backup = backup_path(path)
    try:
        shutil.copy2(path, backup)
    except OSError as e:
        _discard(backup)
        sys.exit(f"{FAIL} Could not back up {path} to {backup}: {e.strerror or e}.\n"
                 f"       {path} was not changed.")
    print(f"{OK} Backup: {backup}")
    try:
        write_types(tree, path)
    except OSError as e:
        try:
            unchanged = path.read_bytes() == tree.source
        except OSError:
            unchanged = False
        reason = f"{FAIL} Could not write {path}: {e.strerror or e} (is it read-only or open in another program?)"
        if unchanged and _discard(backup):
            sys.exit(f"{reason}\n       {path} was not changed; the backup this run made was removed.")
        if unchanged:
            sys.exit(f"{reason}\n       {path} was not changed. Could not remove {backup}; delete it by hand.")
        sys.exit(f"{reason}\n       {path} may be partly written. Restore it from {backup}.")
    print(f"{OK} Wrote {path}")


def run_merge(tree: ET.ElementTree, args: argparse.Namespace) -> int:
    """--merge: check every entry of the chunk, then merge them in one write."""
    root = tree.getroot()
    if root.tag != "types":
        sys.exit(f"{FAIL} {args.path} has root element <{root.tag}>, not <types>; refusing to edit it.")
    try:
        if args.merge == "-":
            source = "stdin"
            # Read stdin's bytes as UTF-8, like a chunk file, not in the console code page.
            buffer = getattr(sys.stdin, "buffer", None)
            text = buffer.read().decode("utf-8-sig") if buffer else sys.stdin.read()
        else:
            chunk_path = Path(args.merge)
            if not chunk_path.is_file():
                sys.exit(f"{FAIL} Chunk file {chunk_path} not found.")
            source = str(chunk_path)
            text = chunk_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as e:
        sys.exit(
            f"{FAIL} The chunk from {source} is not UTF-8 ({e.reason} at byte {e.start}).\n"
            f"       Save it as UTF-8 and run again. {args.path} was not changed."
        )
    try:
        chunk = parse_chunk(text)
    except ET.ParseError as e:
        sys.exit(f"{FAIL} Could not parse the chunk: {e}\n       {args.path} was not changed.")
    for warning in check_chunk(chunk, root, args.path):
        print(f"{WARN} {warning}")
    limits = load_limits(args.path)
    for el in chunk if limits else []:
        for problem in undefined_limit_names(el, limits):
            print(f"{WARN} {el.get('name')}: {problem}")
    print(f"{OK} Checked {len(chunk)} <type> entr{'y' if len(chunk) == 1 else 'ies'}")
    changed, lines = merge(root, chunk)
    for line in lines:
        print(f"{OK} {line}")
    if args.dry_run:
        print(f"{OK} Dry run: {args.path} was not changed.")
    elif changed:
        backup_and_write(tree, args.path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
