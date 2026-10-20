"""dayz-split-types: Split a monolithic types.xml into categorized files.

Wraps DayZ-n-Chill/DayZ-TypeSplitterPro (vendored under vendor/typeSplitter.py).
Original tool: https://github.com/DayZ-n-Chill/DayZ-TypeSplitterPro

The upstream script uses `__file__` to locate types.xml in its own directory,
so we copy it next to the user's types.xml at runtime, run it, then clean up.
The upstream script only logs its errors (it always exits 0), so the wrapper
verifies the result itself before reporting success.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT = REPO_ROOT / ".claude" / "skills" / "dayz-preflight" / "preflight.py"
VENDORED_SCRIPT = Path(__file__).resolve().parent / "vendor" / "typeSplitter.py"

OK = "[OK]   "
INFO = "[INFO] "
FAIL = "[FAIL] "


def gate_on_preflight() -> None:
    if not PREFLIGHT.exists():
        sys.exit(f"{FAIL} dayz-preflight not found at {PREFLIGHT.relative_to(REPO_ROOT)}")
    result = subprocess.run([sys.executable, str(PREFLIGHT)])
    if result.returncode != 0:
        sys.exit(result.returncode)


def backup_once(path: Path) -> None:
    """Copy path to path.bak unless a backup already exists.

    Keeping the first backup means a rerun can't replace the original file's
    backup with an already-split (or already-rewritten) version.
    """
    backup = path.with_name(path.name + ".bak")
    if backup.exists():
        print(f"{INFO} Kept existing backup: {backup}")
        return
    shutil.copy2(path, backup)
    print(f"{OK} Backup: {backup}")


def non_empty_category_files(types_subdir: Path) -> list[str]:
    """Names of category files that contain at least one <type> entry."""
    names = []
    for path in sorted(types_subdir.glob("*.xml")):
        if ET.parse(path).getroot().find("type") is not None:
            names.append(path.name)
    return names


def cfgeconomycore_type_files(cfgeconomycore: Path) -> set[str]:
    """File names listed under <ce folder="types"> in cfgeconomycore.xml."""
    root = ET.parse(cfgeconomycore).getroot()
    return {
        f.get("name", "")
        for ce in root.findall("ce")
        if ce.get("folder") == "types"
        for f in ce.findall("file")
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split monolithic types.xml into categorized files via DayZ-TypeSplitterPro."
    )
    parser.add_argument("types_xml", type=Path, help="Path to types.xml (typically <mission>/db/types.xml).")
    args = parser.parse_args()

    gate_on_preflight()
    print()

    types_xml = args.types_xml.resolve()
    if not types_xml.exists():
        sys.exit(f"{FAIL} {types_xml} not found.")
    if types_xml.name != "types.xml":
        sys.exit(f"{FAIL} Expected a file named 'types.xml', got {types_xml.name}")

    db_dir = types_xml.parent  # upstream script uses os.path.dirname(__file__) for the working dir
    mission_dir = db_dir.parent  # upstream script looks for cfgeconomycore.xml in parent of script_dir
    cfgeconomycore = mission_dir / "cfgeconomycore.xml"
    if not cfgeconomycore.exists():
        sys.exit(
            f"{FAIL} cfgeconomycore.xml not found at {cfgeconomycore}\n"
            "       The splitter needs cfgeconomycore.xml in the parent of types.xml's dir.\n"
            "       Standard DayZ layout: <mission>/cfgeconomycore.xml + <mission>/db/types.xml"
        )

    if not VENDORED_SCRIPT.exists():
        sys.exit(f"{FAIL} Vendored splitter missing at {VENDORED_SCRIPT}")

    backup_once(types_xml)
    backup_once(cfgeconomycore)

    # Copy the vendored splitter next to types.xml so its __file__ resolves into db_dir.
    runtime_copy = db_dir / "_typeSplitter_runtime.py"
    shutil.copy2(VENDORED_SCRIPT, runtime_copy)
    try:
        result = subprocess.run([sys.executable, str(runtime_copy)], cwd=str(db_dir))
    finally:
        runtime_copy.unlink(missing_ok=True)
    if result.returncode != 0:
        print(f"{FAIL} typeSplitter exited {result.returncode}", file=sys.stderr)
        return 1

    types_subdir = db_dir / "types"
    if not types_subdir.is_dir():
        print(f"{FAIL} Splitter ran but {types_subdir} was not created.", file=sys.stderr)
        return 1

    expected = non_empty_category_files(types_subdir)
    print()
    print(f"{OK} Split into {len(expected)} non-empty category files in {types_subdir}")
    for name in expected:
        print(f"        {name}")

    try:
        listed = cfgeconomycore_type_files(cfgeconomycore)
    except ET.ParseError as e:
        print(f"{FAIL} {cfgeconomycore} is not valid XML after the split: {e}", file=sys.stderr)
        return 1
    missing = sorted(set(expected) - listed)
    if missing:
        print(
            f"{FAIL} {cfgeconomycore} does not reference: {', '.join(missing)}\n"
            "       See the typeSplitter log above. The original is in cfgeconomycore.xml.bak.",
            file=sys.stderr,
        )
        return 1
    print(f"{OK} Updated {cfgeconomycore}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
