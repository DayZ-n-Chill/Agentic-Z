"""dayz-import-mod: Link an existing external mod folder into workspace/<ModName>/.

Creates a directory link at workspace/<ModName> pointing at the source folder
(no copy, no move) and a matching P:\\<ModName>\\ junction so the rest of the
DayZ skills work on it. Then scans for missing scaffold pieces (config.cpp,
$PBOPREFIX$, workbench/dayz.gproj) and prompts y/N per piece, writing each
accepted piece with dayz-add-scaffold's writer, called in-process so
/dayz-preflight runs once.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

# PROJECT_DIR is the user's project (where workspace/ and .claude/local-memory/ live).
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
WORKSPACE = PROJECT_DIR / "workspace"
NEW_MOD = h.SKILLS_DIR / "dayz-new-mod" / "new_mod.py"
ADD_SCAFFOLD = h.SKILLS_DIR / "dayz-add-scaffold" / "add_scaffold.py"
P_DRIVE = Path("P:\\")

OK, WARN, FAIL = h.OK, h.WARN, h.FAIL
INFO = "[INFO] "

# Pieces checked at import time: (add-scaffold piece, path in mod, why it matters).
# Only what the rest of the toolchain needs; /dayz-add-scaffold can add the
# skeleton and README later.
SCAFFOLD_CHECKS = (
    ("config", "config.cpp", "needed for /dayz-build-pbo"),
    ("prefix", "$PBOPREFIX$", "needed for /dayz-build-pbo"),
    ("workbench", "workbench/dayz.gproj", "needed for /dayz-launch-workbench --mod"),
)

_nm = h.load_module("dayz_new_mod_module", NEW_MOD)
_scaffold = h.load_module("dayz_add_scaffold_module", ADD_SCAFFOLD)


def _display(path: Path) -> Path:
    try:
        return path.relative_to(PROJECT_DIR)
    except ValueError:
        return path


def resolve_source(cli_value: str | None) -> Path:
    """Resolve the source path from the CLI flag or an interactive prompt."""
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

    # Junctions can't target UNC paths on Windows.
    if raw.startswith("\\\\") or raw.startswith("//"):
        sys.exit(
            f"{FAIL} UNC path not supported: {raw}\n"
            "       Junctions can only target local paths on Windows."
        )

    source = Path(os.path.expanduser(raw)).resolve()
    if not source.exists():
        sys.exit(f"{FAIL} Source path does not exist: {source}")
    if not source.is_dir():
        sys.exit(f"{FAIL} Source path is not a directory: {source}")

    try:
        source.relative_to(WORKSPACE.resolve())
    except ValueError:
        return source  # outside workspace: good
    sys.exit(
        f"{FAIL} Source path is inside this project's workspace/: {source}\n"
        "       Imports must come from outside workspace/. For a mod already in\n"
        "       workspace/<Name>/, create its P:\\<Name> link and any missing pieces with:\n"
        "         /dayz-add-scaffold <Name> --piece junction\n"
        "         /dayz-add-scaffold <Name>"
    )


def derive_modname(source: Path, name_override: str | None) -> str:
    """Use --name if given, else the source folder's basename. Validate either way."""
    name = name_override or source.name
    if _nm.NAME_PATTERN.match(name):
        return name
    if name_override:
        sys.exit(
            f"{FAIL} Invalid mod name: {name!r}\n"
            "       Must start with a letter; letters, digits, underscores only; max 64 chars."
        )
    sys.exit(
        f"{FAIL} Could not derive a valid mod name from source folder {source.name!r}\n"
        "       Pass --name <ValidName> (must match [A-Za-z][A-Za-z0-9_]{0,63})."
    )


def check_workspace_target(workspace_target: Path) -> None:
    if os.path.lexists(workspace_target):
        sys.exit(
            f"{FAIL} {_display(workspace_target)} already exists. Refusing to clobber.\n"
            "       Pick a different name with --name <NewName>, or remove the\n"
            "       existing entry first via /dayz-clean-workspace --mod <Name>."
        )


def detect_missing_pieces(source: Path) -> list[tuple[str, str, str]]:
    """Return the SCAFFOLD_CHECKS entries whose files are missing in source."""
    return [check for check in SCAFFOLD_CHECKS if not (source / check[1]).exists()]


def require_scaffold_decision(
    missing: list[tuple[str, str, str]], scaffold: bool, no_scaffold: bool, interactive: bool
) -> None:
    """Exit before anything is linked when pieces are missing, nobody can be
    asked, and neither --scaffold nor --no-scaffold says what to do."""
    if missing and not (scaffold or no_scaffold or interactive):
        names = ", ".join(rel for _key, rel, _why in missing)
        sys.exit(
            f"{FAIL} Missing scaffold pieces ({names}) and stdin is not a TTY.\n"
            "       Re-run with --scaffold (write all missing) or --no-scaffold (link only)."
        )


def prompt_yn(prompt: str) -> bool:
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def add_missing_pieces(
    target: Path,
    modname: str,
    missing: list[tuple[str, str, str]],
    scaffold: bool,
    no_scaffold: bool,
    author: str | None = None,
) -> int:
    """Offer each missing piece and write the accepted ones with /dayz-add-scaffold's writer.

    `author` is the --author value; it is resolved (flag, cache, prompt) only
    if config.cpp is written. Runs after both links exist. A failed write
    leaves the links in place (the import itself succeeded), names what failed
    and how to retry, and returns 1.
    """
    get_author = _scaffold.lazy_author(author)
    failed: list[str] = []
    for key, rel, _why in missing:
        if no_scaffold:
            print(f"  {INFO} skipping {rel} (--no-scaffold)")
            continue
        # require_scaffold_decision guaranteed a TTY when neither flag is set.
        if not (scaffold or prompt_yn(f"  Add {rel} to your source folder? [y/N]: ")):
            continue
        try:
            _scaffold.add_piece(key, target, modname, get_author)
        except (OSError, SystemExit) as e:
            # SystemExit: resolve_author found no author handle (non-TTY, nothing cached).
            print(f"  {FAIL} Could not add {rel}: {e.code if isinstance(e, SystemExit) else e}")
            failed.append(key)
    if not failed:
        return 0
    print()
    print(f"{FAIL} The import links are in place, but {len(failed)} scaffold piece(s) were not written.")
    for key in failed:
        print(f"       Retry: /dayz-add-scaffold {modname} --piece {key}")
    print(f"       Or undo the import (keeps your source intact): /dayz-clean-workspace --mod {modname}")
    return 1


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
    parser.add_argument(
        "--author",
        help="Author handle for a scaffolded config.cpp (cached for future runs, as in /dayz-new-mod).",
    )
    args = parser.parse_args()

    h.gate_on_preflight()
    print()

    source = resolve_source(args.source)
    print(f"{OK} Source validated: {source}")

    modname = derive_modname(source, args.name)
    print(f"{INFO} {'Mod name (override)' if args.name else 'Derived mod name'}: {modname}")

    workspace_target = WORKSPACE / modname
    p_drive_link = P_DRIVE / modname

    check_workspace_target(workspace_target)
    missing = detect_missing_pieces(source)
    require_scaffold_decision(missing, args.scaffold, args.no_scaffold, sys.stdin.isatty())
    # Reuses dayz-new-mod's stale-junction auto-clean / refuse-on-mismatch logic.
    _nm.check_or_clean_p_drive_link(p_drive_link, workspace_target)

    WORKSPACE.mkdir(exist_ok=True)

    try:
        kind_ws = _nm.make_dir_link(source, workspace_target)
    except (OSError, subprocess.CalledProcessError) as e:
        sys.exit(f"{FAIL} Failed to create workspace link {workspace_target} -> {source}: {e}")
    print(f"{OK} {_display(workspace_target)} -> {source} ({kind_ws})")

    # P:\<Name> -> workspace/<Name>, the same shape /dayz-new-mod creates, so
    # /dayz-clean-workspace's junction-target check works unchanged.
    try:
        kind_p = _nm.make_dir_link(workspace_target, p_drive_link)
    except (OSError, subprocess.CalledProcessError) as e:
        try:
            _nm._remove_link(workspace_target)
            rollback = "Workspace link rolled back."
        except (OSError, subprocess.CalledProcessError):
            rollback = f"Could not roll back {workspace_target}; remove it with: cmd /c rmdir \"{workspace_target}\""
        sys.exit(f"{FAIL} Failed to create {p_drive_link} junction: {e}\n       {rollback}")
    print(f"{OK} {p_drive_link} -> {_display(workspace_target)} ({kind_p})")

    # Same rule as /dayz-new-mod: importing here makes this the active project.
    _nm.sync_project_cache()

    print()
    print("Scaffolding check:")
    for _key, rel, why in SCAFFOLD_CHECKS:
        if (source / rel).exists():
            print(f"  {OK} {rel} present")
        else:
            print(f"  {WARN} {rel} missing ({why})")

    if missing:
        print()
        rc = add_missing_pieces(
            workspace_target, modname, missing, args.scaffold, args.no_scaffold, args.author
        )
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
