"""Write the count fixes that sync.py found into the wiki files, in place.

Only problems that carry a `fix` (a (start, end, replacement) span within one
line) are applied; everything else is left for a hand edit. Each file is read
and written with its own line endings, and only the fixed spans change.
"""
from __future__ import annotations

import os
import tempfile
from collections import defaultdict
from pathlib import Path


class ReadError(Exception):
    """A wiki file to fix could not be read, or changed since the check."""


class Stopped(KeyboardInterrupt):
    """Ctrl+C during --apply; the message says what state the wiki was left in."""


def write_atomic(path: Path, text: str) -> None:
    """Replace path with text, so a failed write never empties or cuts the file short.

    The text goes to a temporary file in the same folder, which then replaces the
    original in one step; on any error the temporary file is removed and the
    original is untouched.
    """
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    os.close(fd)  # reopened as text below; an open handle would block the cleanup on Windows
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.chmod(tmp, path.stat().st_mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def apply_to_text(text: str, fixes: list[tuple[int, tuple[int, int, str]]]) -> str:
    """Apply (1-based line, (start, end, replacement)) fixes to text."""
    lines = text.split("\n")
    # Right to left within a line, so earlier spans keep their offsets.
    for line_no, (start, end, new) in sorted(fixes, key=lambda f: (f[0], f[1][0]), reverse=True):
        line = lines[line_no - 1]
        lines[line_no - 1] = line[:start] + new + line[end:]
    return "\n".join(lines)


def apply_fixes(repo_root: Path, problems: list, dry_run: bool = False) -> int:
    """Apply every fixable problem; print one line per change. Returns the number of changes."""
    by_file: dict[str, list] = defaultdict(list)
    for p in problems:
        if p.fix is not None:
            by_file[p.file].append(p)
    if not by_file:
        print("Nothing to fix automatically.")
        return 0
    # Build every fixed file before writing any. Each write is atomic, so a failed
    # write leaves its file untouched, and the files already replaced are put back,
    # so an error never leaves the wiki half-fixed.
    planned: list[tuple[Path, str, str]] = []  # (path, original text, fixed text)
    changes: list[tuple[str, str, str, int]] = []  # (file:line, old, new, column)
    for rel, fixes in sorted(by_file.items()):
        path = repo_root / rel
        try:
            text = path.read_text(encoding="utf-8", newline="")
        except (OSError, UnicodeDecodeError) as e:
            raise ReadError(f"could not read {rel}: {getattr(e, 'strerror', None) or e}") from e
        lines = text.split("\n")
        for p in sorted(fixes, key=lambda p: (p.line, p.fix[0])):
            start, end, new = p.fix
            if lines[p.line - 1][start:end] != p.old:
                # An editor saved the file after the check; these offsets may now point at other text.
                raise ReadError(f"{rel} changed since the check; run again")
            changes.append((f"{rel}:{p.line}", lines[p.line - 1][start:end], new, start + 1))
        planned.append((path, text, apply_to_text(text, [(p.line, p.fix) for p in fixes])))
    written: list[tuple[Path, str]] = []
    all_written = False
    try:
        if not dry_run:
            for path, original, fixed in planned:
                # Listed before the write, so a stop just after it still puts the file back.
                written.append((path, original))
                write_atomic(path, fixed)
            all_written = True
        verb = "would change" if dry_run else "changed"
        for where, old, new, column in changes:
            print(f"{where}: {verb} {old} -> {new} (column {column})")
        total = sum(len(f) for f in by_file.values())
        print(f"{'Would apply' if dry_run else 'Applied'} {total} fix(es) in {len(by_file)} file(s).")
    except BaseException as first:
        if all_written:
            # Every fix is already in place; only the printout was cut short.
            if isinstance(first, KeyboardInterrupt):
                raise Stopped("stopped after writing the fixes") from first
            raise
        # Any stop (an OSError, or Ctrl+C between two writes) puts back the files
        # already replaced. A failure while putting one back is attached to the
        # first error instead of hiding it, and the other files are still tried.
        failed = []
        for path, original in written:
            try:
                write_atomic(path, original)
            except OSError as e:
                failed.append(path)
                first.add_note(f"could not put back {path}: {e}")
        if isinstance(first, KeyboardInterrupt):
            if failed:
                raise Stopped(f"stopped; could not put back {', '.join(map(str, failed))}") from first
            raise Stopped("stopped; the wiki files were put back" if written else "stopped; nothing was written") from first
        raise
    return total
