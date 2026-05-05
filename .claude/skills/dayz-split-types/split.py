"""dayz-split-types: Split a monolithic types.xml into 18 categorized files.

Wraps DayZ-n-Chill/DayZ-TypeSplitterPro (vendored under vendor/typeSplitter.py).
Original tool: https://github.com/DayZ-n-Chill/DayZ-TypeSplitterPro

The upstream script uses `__file__` to locate types.xml in its own directory,
so we copy it next to the user's types.xml at runtime, run it, then clean up.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT = REPO_ROOT / ".claude" / "skills" / "dayz-preflight" / "preflight.py"
VENDORED_SCRIPT = Path(__file__).resolve().parent / "vendor" / "typeSplitter.py"

OK = "[OK]   "
FAIL = "[FAIL] "


def gate_on_preflight() -> None:
    if not PREFLIGHT.exists():
        sys.exit(f"{FAIL} dayz-preflight not found at {PREFLIGHT.relative_to(REPO_ROOT)}")
    result = subprocess.run([sys.executable, str(PREFLIGHT)])
    if result.returncode != 0:
        sys.exit(result.returncode)


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

    # Always back up types.xml ourselves, regardless of upstream DEBUG_MODE behavior.
    backup = types_xml.with_suffix(".xml.bak")
    shutil.copy2(types_xml, backup)
    print(f"{OK} Backup: {backup}")

    # Copy the vendored splitter next to types.xml so its __file__ resolves into db_dir.
    runtime_copy = db_dir / "_typeSplitter_runtime.py"
    shutil.copy2(VENDORED_SCRIPT, runtime_copy)
    try:
        result = subprocess.run([sys.executable, str(runtime_copy)], cwd=str(db_dir))
        if result.returncode != 0:
            sys.exit(f"{FAIL} typeSplitter exited {result.returncode}")
    finally:
        runtime_copy.unlink(missing_ok=True)

    types_subdir = db_dir / "types"
    if types_subdir.exists():
        files = sorted(p.name for p in types_subdir.iterdir() if p.suffix == ".xml")
        print()
        print(f"{OK} Split into {len(files)} files in {types_subdir}")
        for f in files:
            print(f"        {f}")
    else:
        print(f"{FAIL} Splitter ran but {types_subdir} was not created.")
        return 1
    print(f"{OK} Updated {cfgeconomycore}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
