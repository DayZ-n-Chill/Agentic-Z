"""dayz-split-types: Split a monolithic types.xml into categorized files.

Wraps DayZ-n-Chill/DayZ-TypeSplitterPro (vendored under vendor/typeSplitter.py).
Original tool: https://github.com/DayZ-n-Chill/DayZ-TypeSplitterPro

The upstream script uses `__file__` to locate types.xml in its own directory,
so we copy it next to the user's types.xml at runtime, run it, then clean up.
The upstream script only logs its errors (it always exits 0), so the wrapper
verifies the result itself before reporting success.

Every run first makes timestamped backups of types.xml, cfgeconomycore.xml and
any existing types/ folder (which upstream deletes and regenerates).

Upstream writes <ce folder="types">, but the CE resolves the folder attribute
relative to the mission root, while the files land in <mission>/db/types/. The
wrapper rewrites the attribute to the real relative path (db/types), restores
any other <ce> blocks the formatter dropped, and replaces db/types.xml with an
empty <types/> stub so the server (which always loads db/types.xml) does not
load every type twice.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

VENDORED_SCRIPT = Path(__file__).resolve().parent / "vendor" / "typeSplitter.py"

INFO = "[INFO] "


def backup(path: Path, stamp: str) -> Path:
    """Copy a file or folder to <name>.<stamp>.bak beside it and return the copy.

    A counter is appended if that name is taken, so a rerun within the same
    second still gets its own backup.
    """
    dest = path.with_name(f"{path.name}.{stamp}.bak")
    n = 2
    while dest.exists():
        dest = path.with_name(f"{path.name}.{stamp}-{n}.bak")
        n += 1
    if path.is_dir():
        shutil.copytree(path, dest)
    else:
        shutil.copy2(path, dest)
    print(f"{h.OK} Backup: {dest}")
    return dest


def type_count(types_xml: Path) -> int:
    """Number of <type> entries in a types file."""
    return len(ET.parse(types_xml).getroot().findall("type"))


def non_empty_category_files(types_subdir: Path) -> list[str]:
    """Names of category files that contain at least one <type> entry."""
    names = []
    for path in sorted(types_subdir.glob("*.xml")):
        if ET.parse(path).getroot().find("type") is not None:
            names.append(path.name)
    return names


def cfgeconomycore_type_files(cfgeconomycore: Path, folder: str) -> set[str]:
    """File names listed under <ce folder="<folder>"> in cfgeconomycore.xml."""
    root = ET.parse(cfgeconomycore).getroot()
    return {
        f.get("name", "")
        for ce in root.findall("ce")
        if ce.get("folder") == folder
        for f in ce.findall("file")
    }


def fix_cfgeconomycore(cfgeconomycore: Path, original: Path, folder: str) -> None:
    """Point the splitter's <ce> blocks at `folder` and restore other <ce> blocks.

    Upstream writes folder="types" (wrong: the CE reads the folder relative to
    the mission root) and its formatter keeps only <classes>/<rootclass> and
    <defaults>, so any <ce> block the user had is gone. Those are copied back
    from the pre-split backup, except ones for `folder` itself.
    """
    tree = ET.parse(cfgeconomycore)
    root = tree.getroot()
    for ce in root.findall("ce"):
        if ce.get("folder") == "types":
            ce.set("folder", folder)
    for ce in ET.parse(original).getroot().findall("ce"):
        if ce.get("folder") != folder:
            root.append(ce)
    ET.indent(root, space="\t")
    tree.write(cfgeconomycore, encoding="UTF-8", xml_declaration=True)


def missing_listed_files(cfgeconomycore: Path, mission_dir: Path) -> list[str]:
    """<ce> file entries whose file does not exist at <mission>/<folder>/<name>."""
    root = ET.parse(cfgeconomycore).getroot()
    return [
        f"{ce.get('folder')}/{f.get('name')}"
        for ce in root.findall("ce")
        for f in ce.findall("file")
        if not (mission_dir / ce.get("folder", "") / f.get("name", "")).is_file()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split monolithic types.xml into categorized files via DayZ-TypeSplitterPro."
    )
    parser.add_argument("types_xml", type=Path, help="Path to types.xml (typically <mission>/db/types.xml).")
    args = parser.parse_args()

    h.gate_on_preflight()
    print()

    types_xml = args.types_xml.resolve()
    if not types_xml.exists():
        sys.exit(f"{h.FAIL} {types_xml} not found.")
    if types_xml.name != "types.xml":
        sys.exit(f"{h.FAIL} Expected a file named 'types.xml', got {types_xml.name}")

    db_dir = types_xml.parent  # upstream script uses os.path.dirname(__file__) for the working dir
    mission_dir = db_dir.parent  # upstream script looks for cfgeconomycore.xml in parent of script_dir
    cfgeconomycore = mission_dir / "cfgeconomycore.xml"
    if not cfgeconomycore.exists():
        sys.exit(
            f"{h.FAIL} cfgeconomycore.xml not found at {cfgeconomycore}\n"
            "       The splitter needs cfgeconomycore.xml in the parent of types.xml's dir.\n"
            "       Standard DayZ layout: <mission>/cfgeconomycore.xml + <mission>/db/types.xml"
        )

    try:
        entries = type_count(types_xml)
    except ET.ParseError as e:
        sys.exit(f"{h.FAIL} {types_xml} is not valid XML: {e}")
    if entries == 0:
        sys.exit(
            f"{h.FAIL} {types_xml} has no <type> entries; it looks already split.\n"
            "       Restore it from a types.xml.<stamp>.bak backup to split again."
        )

    if not VENDORED_SCRIPT.exists():
        sys.exit(f"{h.FAIL} Vendored splitter missing at {VENDORED_SCRIPT}")

    types_subdir = db_dir / "types"
    folder = types_subdir.relative_to(mission_dir).as_posix()  # "db/types"
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    types_backup = backup(types_xml, stamp)
    core_backup = backup(cfgeconomycore, stamp)
    if types_subdir.is_dir():
        backup(types_subdir, stamp)

    # Copy the vendored splitter next to types.xml so its __file__ resolves into db_dir.
    runtime_copy = db_dir / "_typeSplitter_runtime.py"
    shutil.copy2(VENDORED_SCRIPT, runtime_copy)
    try:
        result = subprocess.run([sys.executable, str(runtime_copy)], cwd=str(db_dir))
    finally:
        runtime_copy.unlink(missing_ok=True)
    if result.returncode != 0:
        print(f"{h.FAIL} typeSplitter exited {result.returncode}", file=sys.stderr)
        return 1

    if not types_subdir.is_dir():
        print(f"{h.FAIL} Splitter ran but {types_subdir} was not created.", file=sys.stderr)
        return 1

    expected = non_empty_category_files(types_subdir)
    print()
    print(f"{h.OK} Split into {len(expected)} non-empty category files in {types_subdir}")
    for name in expected:
        print(f"        {name}")

    try:
        fix_cfgeconomycore(cfgeconomycore, core_backup, folder)
        listed = cfgeconomycore_type_files(cfgeconomycore, folder)
        dangling = missing_listed_files(cfgeconomycore, mission_dir)
    except ET.ParseError as e:
        print(f"{h.FAIL} {cfgeconomycore} is not valid XML after the split: {e}", file=sys.stderr)
        return 1
    missing = sorted(set(expected) - listed)
    if missing:
        print(
            f"{h.FAIL} {cfgeconomycore} does not reference: {', '.join(missing)}\n"
            f"       See the typeSplitter log above. The original is in {core_backup.name}.",
            file=sys.stderr,
        )
        return 1
    print(f'{h.OK} Updated {cfgeconomycore} (<ce folder="{folder}">)')
    for entry in dangling:
        print(f"{h.WARN} {cfgeconomycore.name} lists {entry}, which does not exist")

    # The server always loads db/types.xml; leaving the full file would load every
    # type twice. An empty stub keeps the file valid; the original is in the backup.
    types_xml.write_text(
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n<types>\n</types>\n',
        encoding="utf-8",
    )
    print(
        f"{h.OK} Emptied {types_xml.name}: its {entries} entries now load from {folder}/ "
        f"(original kept in {types_backup.name})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
