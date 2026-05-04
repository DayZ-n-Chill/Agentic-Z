"""dayz-import-mod: Link an existing external mod folder into workspace/<ModName>/.

Creates a directory link at workspace/<ModName> pointing at the source folder
(no copy, no move) and a matching P:\\<ModName>\\ junction so the rest of the
DayZ skills work on it. Then scans for missing scaffold pieces (config.cpp,
$PBOPREFIX$, workbench/dayz.gproj) and prompts y/N per piece, delegating
writes to dayz-add-scaffold.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

# .../.claude/skills/dayz-import-mod/import_mod.py -> repo root is parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE = REPO_ROOT / "workspace"
NEW_MOD = REPO_ROOT / ".claude" / "skills" / "dayz-new-mod" / "new_mod.py"
ADD_SCAFFOLD = REPO_ROOT / ".claude" / "skills" / "dayz-add-scaffold" / "add_scaffold.py"
P_DRIVE = Path("P:\\")

OK = "[OK]   "
INFO = "[INFO] "
WARN = "[WARN] "
FAIL = "[FAIL] "

# Pieces we check at import time. Each tuple: (key, relative-path-in-mod, why-it-matters).
# Keep this short - only the pieces the rest of the toolchain explicitly needs.
# /dayz-add-scaffold can add the rest (skeleton, README) later if the user wants.
SCAFFOLD_CHECKS = (
    ("config", "config.cpp", "needed for /dayz-build-pbo"),
    ("prefix", "$PBOPREFIX$", "needed for /dayz-build-pbo"),
    ("workbench", "workbench/dayz.gproj", "needed for /dayz-launch-workbench --mod"),
)


def _load_new_mod_module():
    spec = importlib.util.spec_from_file_location("dayz_new_mod_module", NEW_MOD)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load dayz-new-mod module at {NEW_MOD}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_nm = _load_new_mod_module()


def resolve_source(cli_value: str | None) -> Path:
    """Resolve source path from CLI flag or interactive prompt."""
    raw = cli_value
    if not raw:
        if not sys.stdin.isatty():
            sys.exit(
                f"{FAIL} --source is required when stdin is not a TTY.\n"
                "       Re-run with --source <path-to-existing-mod-folder>."
            )
        try:
            raw = input("Path to existing mod folder: ").strip()
        except EOFError:
            raw = ""
        if not raw:
            sys.exit(f"{FAIL} No source path provided.")

    # Refuse UNC paths up-front: junctions can't target them on Windows.
    if raw.startswith("\\\\") or raw.startswith("//"):
        sys.exit(
            f"{FAIL} UNC path not supported: {raw}\n"
            "       Junctions can only target local paths on Windows."
        )

    expanded = os.path.expanduser(raw)
    source = Path(expanded).resolve()
    if not source.exists():
        sys.exit(f"{FAIL} Source path does not exist: {source}")
    if not source.is_dir():
        sys.exit(f"{FAIL} Source path is not a directory: {source}")

    workspace_resolved = WORKSPACE.resolve()
    try:
        source.relative_to(workspace_resolved)
    except ValueError:
        pass  # not inside workspace - good
    else:
        sys.exit(
            f"{FAIL} Source path is inside this repo's workspace/: {source}\n"
            "       Imports must come from outside workspace/. If your mod is\n"
            "       already there, the toolchain can use it directly - no import needed."
        )

    return source


def derive_modname(source: Path, name_override: str | None) -> str:
    """Use --name if given, else the source folder's basename. Validate either way."""
    name = name_override or source.name
    if not _nm.NAME_PATTERN.match(name):
        if name_override:
            sys.exit(
                f"{FAIL} Invalid mod name: {name!r}\n"
                "       Must start with a letter; letters, digits, underscores only; max 64 chars."
            )
        sys.exit(
            f"{FAIL} Could not derive a valid mod name from source folder {source.name!r}\n"
            "       Pass --name <ValidName> (must match [A-Za-z][A-Za-z0-9_]{0,63})."
        )
    return name


def check_workspace_target(workspace_target: Path) -> None:
    if os.path.lexists(workspace_target):
        try:
            rel = workspace_target.relative_to(REPO_ROOT)
        except ValueError:
            rel = workspace_target
        sys.exit(
            f"{FAIL} {rel} already exists. Refusing to clobber.\n"
            "       Pick a different name with --name <NewName>, or remove the\n"
            "       existing entry first via /dayz-clean-workspace --mod <Name>."
        )


def detect_missing_pieces(source: Path) -> list[tuple[str, str, str]]:
    """Return the SCAFFOLD_CHECKS entries whose files are missing in source."""
    missing = []
    for key, rel, why in SCAFFOLD_CHECKS:
        if not (source / rel).exists():
            missing.append((key, rel, why))
    return missing


def prompt_yn(prompt: str) -> bool:
    if not sys.stdin.isatty():
        return False
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def run_add_scaffold(modname: str, piece: str) -> int:
    """Shell out to /dayz-add-scaffold for the named piece. Inherits stdio."""
    # Flush so the parent's lines are committed before the subprocess writes,
    # otherwise Windows interleaves them in unhelpful order.
    sys.stdout.flush()
    return subprocess.run(
        [sys.executable, str(ADD_SCAFFOLD), modname, "--piece", piece]
    ).returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import an existing DayZ mod folder by linking it into workspace/."
    )
    parser.add_argument("--source", help="Path to existing mod folder.")
    parser.add_argument("--name", help="Override the mod name (defaults to source basename).")
    scaffold_group = parser.add_mutually_exclusive_group()
    scaffold_group.add_argument(
        "--scaffold",
        action="store_true",
        help="Auto-yes: scaffold every missing piece into the source folder.",
    )
    scaffold_group.add_argument(
        "--no-scaffold",
        action="store_true",
        help="Auto-no: never write into the source folder.",
    )
    args = parser.parse_args()

    _nm.gate_on_preflight()
    print()

    source = resolve_source(args.source)
    print(f"{OK} Source validated: {source}")

    modname = derive_modname(source, args.name)
    print(f"{INFO} {'Mod name (override)' if args.name else 'Derived mod name'}: {modname}")

    workspace_target = WORKSPACE / modname
    p_drive_link = P_DRIVE / modname

    check_workspace_target(workspace_target)
    # Reuses dayz-new-mod's stale-junction auto-clean / refuse-on-mismatch logic,
    # comparing the existing P:\<Name>\ target against our workspace path.
    _nm.check_or_clean_p_drive_link(p_drive_link, workspace_target)

    WORKSPACE.mkdir(exist_ok=True)

    # workspace/<Name> -> source
    try:
        kind_ws = _nm.make_dir_link(source, workspace_target)
    except Exception as e:
        sys.exit(
            f"{FAIL} Failed to create workspace link {workspace_target} -> {source}: {e}"
        )
    try:
        rel_ws = workspace_target.relative_to(REPO_ROOT)
    except ValueError:
        rel_ws = workspace_target
    print(f"{OK} {rel_ws} -> {source} ({kind_ws})")

    # P:\<Name> -> workspace/<Name>
    # Matching dayz-new-mod's pattern: P:\ junction goes through workspace, so
    # /dayz-clean-workspace's existing junction-target check works unchanged.
    try:
        kind_p = _nm.make_dir_link(workspace_target, p_drive_link)
    except Exception as e:
        # Roll back the workspace link so the next attempt is clean.
        try:
            if os.name == "nt":
                subprocess.run(
                    ["cmd", "/c", "rmdir", str(workspace_target)],
                    check=False, capture_output=True, text=True,
                )
            else:
                workspace_target.unlink()
        except Exception:
            pass
        sys.exit(
            f"{FAIL} Failed to create P:\\{modname} junction: {e}\n"
            "       Workspace link rolled back."
        )
    try:
        target_disp = workspace_target.relative_to(REPO_ROOT)
    except ValueError:
        target_disp = workspace_target
    print(f"{OK} P:\\{modname} -> {target_disp} ({kind_p})")

    # Scaffolding check
    print()
    print("Scaffolding check:")
    for key, rel, why in SCAFFOLD_CHECKS:
        if (source / rel).exists():
            print(f"  {OK} {rel} present")
        else:
            print(f"  {WARN} {rel} missing ({why})")

    missing = detect_missing_pieces(source)
    if missing:
        print()
        for key, rel, _why in missing:
            if args.no_scaffold:
                print(f"  {INFO} skipping {rel} (--no-scaffold)")
                continue
            if args.scaffold:
                add_yn = True
            elif sys.stdin.isatty():
                add_yn = prompt_yn(f"  Add {rel} to your source folder? [y/N]: ")
            else:
                sys.exit(
                    f"\n{FAIL} Missing scaffold pieces and stdin is not a TTY.\n"
                    "       Re-run with --scaffold (write all missing) or --no-scaffold (link only)."
                )
            if add_yn:
                rc = run_add_scaffold(modname, key)
                if rc != 0:
                    return rc

    print()
    print("Next steps:")
    print(f"  - Open in Workbench: /dayz-launch-workbench --mod {modname}")
    print(f"  - Build: /dayz-build-pbo {modname}")
    print(f"  - Remove the import (keeps your source intact): /dayz-clean-workspace --mod {modname}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
