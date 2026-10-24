"""clean-repo: remove all template-managed artifacts before pushing changes.

Orchestrator. Discovers every `<domain>-clean-workspace` skill under
.claude/skills/, runs each one's clean.py with --include-server --dry-run to
build a combined plan and its plan ID (a hash of every child's dry-run stdout
and stderr, plus the path, size and mtime of every versioned file under the
project's .server/), asks for confirmation, then runs each with
--include-server --yes. --keep-server drops --include-server so every child
leaves .server/ in place.

The approved plan is pinned: --plan <ID> refuses (exit 3) when the fresh dry
run no longer matches the ID the user approved, and after an interactive yes
the dry run is repeated and compared before anything is removed. A cached
project that is not this checkout is refused (exit 2) unless --other-project
is passed.

Each domain owns its own cleanup logic; this skill just runs them all.

Maintainer rules: keep domain-specific knowledge out of this file (it belongs
in each <domain>-clean-workspace skill), and pass children nothing beyond
--include-server plus --dry-run or --yes, the contract every child accepts
(PYTHONIOENCODING=utf-8 is set in their environment so captured dry-run output
decodes the same way every run). The one allowed exception: cached_project()
reads /dayz-init's cached project to name it in the prompt, to refuse a
project that is not this checkout, and to ask git which files under its
.server/ are versioned (versioned_server_files), so the plan can warn before
removing them and pin their state in the plan ID. When git cannot answer, a
removal that includes .server/ is refused (exit 1) and a dry run warns, since
those files could neither be listed nor pinned.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "


def cached_project() -> Path | None:
    """The project root cached by /dayz-init, which the children clean. None when nothing is cached.

    Children resolve their project through dayz-init/state.py with the same
    working directory and environment, so this names the folder they will clean.
    Exceptions from state.py propagate; main() turns them into a [FAIL] line.
    """
    state_py = SKILLS_DIR / "dayz-init" / "state.py"
    if not state_py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("clean_repo_dayz_init_state", state_py)
    if spec is None or spec.loader is None:
        return None
    state = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(state)
    root = state.cached_project_root()
    return root.resolve() if root else None


class ServerCheckError(Exception):
    """git could not list the versioned files under .server/."""


def versioned_server_files(project: Path) -> list[str]:
    """Files under <project>/.server/ that git tracks or would track (not ignored).

    The template ignores all of .server/, but a clone may add .gitignore
    exceptions to version its serverDZ.cfg or mission/ edits, so these are the
    files --include-server would delete that the user may have versioned. Empty when .server/ is absent. Raises ServerCheckError when git
    cannot be run or exits non-zero (for example, the project is not a git repo).
    """
    if not (project / ".server").is_dir():
        return []
    cmd = ["git", "-C", str(project), "ls-files", "--cached", "--others", "--exclude-standard", "--", ".server"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as e:
        raise ServerCheckError(f"git could not be run: {e}") from e
    if result.returncode != 0:
        detail = (result.stderr or "").strip() or "no error text"
        raise ServerCheckError(f"git exited {result.returncode}: {detail}")
    return [line for line in result.stdout.splitlines() if line]


def server_stamp(project: Path, files: list[str]) -> bytes:
    """Path, size and mtime of each versioned .server/ file, hashed into the plan ID.

    Children list .server/ as a single item, so without this an added or edited
    mission file or serverDZ.cfg would leave the plan ID unchanged.
    """
    parts = []
    for rel in sorted(files):
        try:
            st = (project / rel).stat()
            parts.append(f"{rel}|{st.st_size}|{st.st_mtime_ns}")
        except OSError:
            parts.append(f"{rel}|missing")
    return "\n".join(parts).encode("utf-8")


def same_path(a: Path, b: Path) -> bool:
    return os.path.normcase(str(a.resolve())) == os.path.normcase(str(b.resolve()))


def find_cleanup_skills(skills_dir: Path | None = None) -> list[Path]:
    """Return every <domain>-clean-workspace skill folder containing a clean.py.

    Folders starting with `_` (like _shared/) are skipped: they're helpers,
    not skills.
    """
    root = skills_dir or SKILLS_DIR
    return [
        child
        for child in sorted(root.iterdir())
        if child.is_dir()
        and not child.name.startswith("_")
        and child.name.endswith("-clean-workspace")
        and (child / "clean.py").is_file()
    ]


def confirm(prompt: str = "Proceed? [y/N]: ") -> bool:
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def child_env() -> dict[str, str]:
    return {**os.environ, "PYTHONIOENCODING": "utf-8"}


def dry_run_plan(
    skills: list[Path], include_server: bool = True, show: bool = True, stamp: bytes = b""
) -> tuple[list[str], str]:
    """Run each skill's clean.py with [--include-server] --dry-run.

    Returns (names that failed, plan ID). The plan ID is a short hash of the
    server mode, `stamp` (server_stamp of the versioned .server/ files) and
    every child's dry-run stdout and stderr, so any change to what would be
    removed changes the ID. With show=False the output is only hashed, not
    printed (the re-check before removal).
    """
    failed: list[str] = []
    digest = hashlib.sha256(b"include-server" if include_server else b"keep-server")
    digest.update(b"\0" + stamp + b"\0")
    server_flag = ["--include-server"] if include_server else []
    for skill in skills:
        if show:
            print()
            print(f"=== /{skill.name} (--dry-run) ===")
            sys.stdout.flush()
        cmd = [sys.executable, str(skill / "clean.py"), *server_flag, "--dry-run"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=child_env())
        out = result.stdout or b""
        err = result.stderr or b""
        if show:
            sys.stdout.write(out.decode("utf-8", "replace"))
            sys.stdout.flush()
            sys.stderr.write(err.decode("utf-8", "replace"))
            sys.stderr.flush()
        digest.update(skill.name.encode("utf-8") + b"\0" + out + b"\0" + err + b"\0")
        if result.returncode != 0:
            failed.append(skill.name)
    return failed, digest.hexdigest()[:12]


def run_children(skills: list[Path], include_server: bool = True) -> list[str]:
    """Run each skill's clean.py with [--include-server] --yes. Return names that failed."""
    failed: list[str] = []
    server_flag = ["--include-server"] if include_server else []
    for skill in skills:
        print()
        print(f"=== /{skill.name} (--yes) ===")
        sys.stdout.flush()
        cmd = [sys.executable, str(skill / "clean.py"), *server_flag, "--yes"]
        if subprocess.run(cmd, env=child_env()).returncode != 0:
            failed.append(skill.name)
    return failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Remove all template-managed artifacts across every domain."
    )
    parser.add_argument("--yes", action="store_true", help="Skip the interactive confirmation prompt.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the combined plan (each domain cleanup with --dry-run) and its plan ID, then stop.",
    )
    parser.add_argument(
        "--keep-server",
        action="store_true",
        help="Keep .server/ (test-server configs, missions, logs): do not pass --include-server to the children.",
    )
    parser.add_argument(
        "--plan",
        metavar="ID",
        help="Plan ID printed by an earlier --dry-run. Refuse (exit 3) if the current plan differs. Not valid with --dry-run.",
    )
    parser.add_argument(
        "--other-project",
        action="store_true",
        help="Allow cleaning the project cached by /dayz-init when it is not this checkout.",
    )
    args = parser.parse_args(argv)

    if args.dry_run and args.plan is not None:
        print(
            f"{FAIL}--plan checks an approved plan before removal and cannot be combined with --dry-run. "
            "Nothing was run.",
            file=sys.stderr,
        )
        return 2

    if not args.dry_run and not args.yes and not sys.stdin.isatty():
        print(f"{FAIL}Refusing to proceed without --yes when stdin is not a TTY.", file=sys.stderr)
        return 2

    skills = find_cleanup_skills()
    if not skills:
        print(f"{OK}No domain cleanup skills found.")
        return 0

    try:
        project = cached_project()
    except Exception as e:  # state.py is another skill's code: any failure there stops cleanly
        print(
            f"{FAIL}Could not read the project cached by /dayz-init ({type(e).__name__}: {e}). "
            "Nothing was run. Run /dayz-init to repair the cache, then try again.",
            file=sys.stderr,
        )
        return 1
    other = project is not None and not same_path(project, REPO_ROOT)
    if other and not args.dry_run and not args.other_project:
        print(
            f"{FAIL}Cleanup would target the cached project {project}, not this checkout {REPO_ROOT}. "
            "Nothing was run. Run /dayz-init in the checkout you mean to clean, or pass "
            "--other-project to clean the cached project anyway.",
            file=sys.stderr,
        )
        return 2
    if other:
        print(f"{WARN}Cleanup targets the cached project {project}, not this checkout {REPO_ROOT}")
    print(f"Plan from {len(skills)} cleanup skill(s): {', '.join('/' + s.name for s in skills)}")
    include_server = not args.keep_server

    def server_state() -> tuple[list[str], bytes]:
        files = versioned_server_files(project) if project and include_server else []
        return files, server_stamp(project, files) if files else b""

    server_error = None
    try:
        versioned, stamp = server_state()
    except ServerCheckError as e:
        if not args.dry_run:
            print(
                f"{FAIL}Could not check which files under {project / '.server'} git versions ({e}), "
                "so serverDZ.cfg and mission edits there could be removed unseen. Nothing was run. "
                "Make git work in that project, or pass --keep-server to leave .server/ in place.",
                file=sys.stderr,
            )
            return 1
        server_error = e
        versioned, stamp = [], b""
    failed, plan_id = dry_run_plan(skills, include_server, stamp=stamp)
    print()
    if failed:
        print(f"{FAIL}Dry run failed for: {', '.join(failed)}. Nothing was removed.", file=sys.stderr)
        return 1
    if versioned:
        shown = ", ".join(versioned[:5]) + (f" and {len(versioned) - 5} more" if len(versioned) > 5 else "")
        print(
            f"{WARN}.server/ holds {len(versioned)} file(s) git tracks or keeps trackable "
            f"(serverDZ.cfg, mission edits) that this removes: {shown}. Pass --keep-server to keep them."
        )
    if server_error is not None:
        print(
            f"{WARN}Could not check which files under {project / '.server'} git versions ({server_error}). "
            "A removal run that includes .server/ will refuse until git works there."
        )
    print(f"Plan ID: {plan_id}")
    if args.dry_run:
        print(f"{OK}Dry run complete. Nothing was removed.")
        if server_error is not None:
            print("       Make git work in that project, or rerun with --dry-run --keep-server for a plan that keeps .server/.")
            return 0
        flags = ["--yes", "--plan", plan_id]
        if args.keep_server:
            flags.append("--keep-server")
        if other:
            flags.append("--other-project")
        print(f'       To remove exactly this plan, run: python "{Path(__file__).resolve()}" {" ".join(flags)}')
        return 0

    if args.plan is not None and args.plan.strip().lower() != plan_id:
        print(
            f"{FAIL}The plan changed since it was approved (approved {args.plan}, now {plan_id}). "
            "Nothing was removed. Show the new plan above and ask again.",
            file=sys.stderr,
        )
        return 3

    if not args.yes:
        where = f" from {project}" if project else ""
        if not confirm(f"Remove everything listed above{where}? [y/N]: "):
            print("Aborted. Nothing was removed.")
            return 0
        # Time passed at the prompt: remove only if the plan is still the one shown.
        try:
            failed, now_id = dry_run_plan(skills, include_server, show=False, stamp=server_state()[1])
        except ServerCheckError:
            failed, now_id = ["the .server/ git check"], ""
        if failed or now_id != plan_id:
            now = "a failed check" if failed else now_id
            print(
                f"{FAIL}The plan changed while waiting for confirmation (shown {plan_id}, now {now}). "
                "Nothing was removed. Run /clean-repo again.",
                file=sys.stderr,
            )
            return 3

    failed = run_children(skills, include_server)
    print()
    if failed:
        print(f"{FAIL}{len(failed)} cleanup skill(s) failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"{OK}All cleanup skills completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
