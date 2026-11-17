#!/usr/bin/env python3
"""Pin a complete Pack commit into a task-local capture plus one derived adapter.

This is not a universal launcher. It materializes git blobs, writes one
versioned discovery adapter, and grades a probe transcript. It does not
isolate a host's global skill catalog.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import stat as statmod
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = 1
DEFAULT_SKILL = "dayz-mod-workflow"
SHORT_COMMIT_LEN = 7
PROBE_DIRNAME = "probe"
ADAPTER_ROOT = Path(".agents") / "skills"
MANIFEST_NAME = "manifest.json"
RECEIPT_NAME = "receipt.json"
COMMANDS_NAME = "commands.json"
CANARY_PREFIX = "CANARY:"
SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
ALLOWED_GIT_MODES = {"100644", "100755"}
CONSUMER_PROMPT = (
    "Execute its runtime canary. Read only the source SKILL.md and named "
    "references allowed by the loaded adapter; return only the canary value."
)
CODEX_MODEL = "gpt-5.6-sol"
CURSOR_MODEL = "cursor-grok-4.6-xhigh"
CURSOR_SERVED_MODEL_LABEL = "Cursor Grok 4.6 Extra High"
CURSOR_SERVED_MODEL_MAP = {
    CURSOR_SERVED_MODEL_LABEL: CURSOR_MODEL,
}
CURSOR_PROGRAM_NAME = "cursor-agent.cmd"
FILE_ATTRIBUTE_REPARSE_POINT = 0x400

O_BINARY = getattr(os, "O_BINARY", 0)

NAME_PATH_RE = re.compile(
    r"(?im)^[ \t-]*name:\s*[\"']?([A-Za-z0-9][A-Za-z0-9._-]*)[\"']?[ \t]*\r?\n"
    r"(?:[ \t]+[^\n]*\r?\n){0,8}?"
    r"[ \t]*path:\s*[\"']?([^\r\n]+?)[\"']?[ \t]*$",
)
PATH_NAME_RE = re.compile(
    r"(?im)^[ \t-]*path:\s*[\"']?([^\r\n]+?)[\"']?[ \t]*\r?\n"
    r"(?:[ \t]+[^\n]*\r?\n){0,8}?"
    r"[ \t]*name:\s*[\"']?([A-Za-z0-9][A-Za-z0-9._-]*)[\"']?[ \t]*$",
)
ADAPTER_PATH_RE = re.compile(
    r"(?i)(?P<path>(?:[A-Za-z]:)?[^\s\"']*?[\\/]\.agents[\\/]skills[\\/]"
    r"(?P<alias>[A-Za-z0-9][A-Za-z0-9._-]*)[\\/]SKILL\.md)"
)
RELATIVE_ADAPTER_RE = re.compile(
    r"(?i)(?:^|[\s\"'`:(])(?P<path>\.agents[\\/]skills[\\/]"
    r"(?P<alias>[A-Za-z0-9][A-Za-z0-9._-]*)[\\/]SKILL\.md)"
)
SKILL_ROOT_RE = re.compile(
    r"(?im)^[ \t-]*`?(r\d+)`?[ \t]*=[ \t]*`?([^`\r\n]+?)`?[ \t]*$"
)
SKILL_FILE_RE = re.compile(
    r"(?im)^[ \t-]*([A-Za-z0-9][A-Za-z0-9._-]*)\s*:.*?\bfile:\s*`?([^`\r\n]+?)`?(?:\s*\)[ \t]*)?$"
)
ROOT_ALIAS_RE = re.compile(r"^(r\d+)/(.*)$")


class PinError(Exception):
    def __init__(self, code: str, message: str, *, path: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.path = path

    def as_finding(self) -> dict[str, object]:
        return {
            "code": self.code,
            "severity": "error",
            "path": self.path,
            "message": self.message,
        }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.new("sha1", header + data, usedforsecurity=False).hexdigest()


def posix_path(value: str) -> str:
    return value.replace("\\", "/")


def is_absolute_path_string(value: str) -> bool:
    text = posix_path(value.strip())
    if text.startswith("/") or text.startswith("//"):
        return True
    return bool(re.match(r"^[A-Za-z]:/", text)) or Path(value).is_absolute()


def exact_path_key(value: str | Path) -> str:
    normalized = os.path.normpath(str(value))
    if os.name == "nt":
        normalized = os.path.normcase(normalized)
    return posix_path(normalized)


def is_link_or_reparse(path: Path) -> bool:
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if statmod.S_ISLNK(st.st_mode):
        return True
    attrs = int(getattr(st, "st_file_attributes", 0) or 0)
    return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)


def link_kind(path: Path) -> str:
    try:
        if path.is_symlink() or statmod.S_ISLNK(os.lstat(path).st_mode):
            return "SYMLINK"
    except OSError:
        return "SYMLINK"
    return "REPARSE"


def is_regular_nonlink(path: Path) -> bool:
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if statmod.S_ISLNK(st.st_mode):
        return False
    attrs = int(getattr(st, "st_file_attributes", 0) or 0)
    if attrs & FILE_ATTRIBUTE_REPARSE_POINT:
        return False
    return statmod.S_ISREG(st.st_mode)


def cursor_program() -> str:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return str(Path(local) / "cursor-agent" / CURSOR_PROGRAM_NAME)
    return str(Path("cursor-agent") / CURSOR_PROGRAM_NAME)


def cursor_argv(probe_root: Path, prompt: str) -> list[str]:
    return [
        "--mode",
        "ask",
        "--trust",
        "--workspace",
        str(probe_root),
        "--output-format",
        "stream-json",
        "--model",
        CURSOR_MODEL,
        "-p",
        prompt,
    ]


def codex_exec_argv(probe_root: Path, prompt: str) -> list[str]:
    return [
        "codex",
        "exec",
        "--json",
        "--ephemeral",
        "-s",
        "read-only",
        "-C",
        str(probe_root),
        "-m",
        CODEX_MODEL,
        prompt,
    ]


def parse_skill_roots(text: str) -> dict[str, str]:
    roots: dict[str, str] = {}
    for match in SKILL_ROOT_RE.finditer(text):
        roots[match.group(1)] = match.group(2).strip().strip("`'\"")
    return roots


def iter_json_strings(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
        return found
    if isinstance(value, list):
        for item in value:
            found.extend(iter_json_strings(item))
        return found
    if isinstance(value, dict):
        for nested in value.values():
            found.extend(iter_json_strings(nested))
    return found


def cursor_served_label(init: object) -> str | None:
    if not isinstance(init, dict):
        return None
    if str(init.get("type", "")) != "system":
        return None
    if str(init.get("subtype", "")) != "init":
        return None
    label = str(init.get("model", "")).strip()
    return label or None


def resolve_catalog_path(path: str, probe_root: Path, skill_roots: Mapping[str, str]) -> str:
    raw = posix_path(path.strip().strip("`'\" "))
    aliased = ROOT_ALIAS_RE.match(raw)
    if aliased and aliased.group(1) in skill_roots:
        root = posix_path(skill_roots[aliased.group(1)]).rstrip("/")
        raw = f"{root}/{aliased.group(2)}"
    if not is_absolute_path_string(raw):
        raw = posix_path(str(probe_root / raw))
    return exact_path_key(raw)


def expected_adapter_key(probe_root: Path, alias: str) -> str:
    return exact_path_key(probe_root / ADAPTER_ROOT / alias / "SKILL.md")


def list_probe_files(probe_root: Path) -> tuple[list[str], list[tuple[str, str]]]:
    files: list[str] = []
    links: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(probe_root, topdown=True, followlinks=False):
        current = Path(dirpath)
        rel_dir = current.relative_to(probe_root)
        if rel_dir.parts[:1] == (".git",):
            dirnames[:] = []
            continue
        kept: list[str] = []
        for name in dirnames:
            child = current / name
            rel = posix_path(str(child.relative_to(probe_root)))
            if name == ".git" or rel == ".git" or rel.startswith(".git/"):
                continue
            if is_link_or_reparse(child):
                links.append((rel, link_kind(child)))
                continue
            kept.append(name)
        dirnames[:] = kept
        for name in filenames:
            child = current / name
            rel = posix_path(str(child.relative_to(probe_root)))
            if rel == ".git" or rel.startswith(".git/"):
                continue
            if is_link_or_reparse(child):
                links.append((rel, link_kind(child)))
                continue
            files.append(rel)
    return sorted(files), links


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, *, path: str = "") -> dict[str, object]:
    return {
        "code": code,
        "severity": "error",
        "path": path,
        "message": message,
    }


def make_report(
    command: str,
    verdict: str,
    findings: Iterable[dict[str, object]],
    **artifacts: object,
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "verdict": verdict,
        "findings": list(findings),
        "artifacts": artifacts,
    }


def git_run(
    root: Path,
    args: list[str],
    *,
    input_bytes: bytes | None = None,
    check: bool = True,
    extra_env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        input=input_bytes,
        capture_output=True,
        check=False,
        env=env,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.decode("utf-8", "replace").strip()
        raise PinError(
            "GIT-FAILED",
            f"git {' '.join(args)} failed: {stderr or result.returncode}",
            path=str(root),
        )
    return result


def git_text(root: Path, *args: str) -> str:
    return git_run(root, list(args)).stdout.decode("utf-8", "strict").strip()


def git_bytes(root: Path, *args: str) -> bytes:
    return git_run(root, list(args)).stdout


def is_unsafe_relpath(value: str) -> bool:
    if not value or "\0" in value:
        return True
    if "\\" in value or value.startswith("/") or value.startswith("~"):
        return True
    if Path(value).is_absolute() or Path(value).drive:
        return True
    parts = Path(posix_path(value)).parts
    if any(part in {"", ".", ".."} for part in parts):
        return True
    if parts and parts[0] == ".git":
        return True
    return False


def paths_disjoint(left: Path, right: Path) -> bool:
    left_r = left.resolve()
    right_r = right.resolve()
    try:
        left_r.relative_to(right_r)
        return False
    except ValueError:
        pass
    try:
        right_r.relative_to(left_r)
        return False
    except ValueError:
        return True


def normalize_skill_name(skill: str) -> str:
    name = skill.strip()
    if not SKILL_NAME_RE.fullmatch(name):
        raise PinError(
            "UNSAFE-SKILL",
            "Skill must be a single lowercase hyphenated name, not a path.",
            path=skill,
        )
    return name


def short_commit(commit: str) -> str:
    return commit[:SHORT_COMMIT_LEN].lower()


def alias_for(skill: str, commit: str) -> str:
    return f"{skill}-{short_commit(commit)}"


def original_skill_posix(skill: str) -> str:
    return f"skills/{skill}/SKILL.md"


def references_prefix(skill: str) -> str:
    return f"skills/{skill}/references/"


def canary_line(nonce: str) -> str:
    return f"{CANARY_PREFIX}{nonce}"


def require_clean_source(source: Path) -> None:
    status = git_run(source, ["status", "--porcelain=v1", "-z"]).stdout
    if status:
        raise PinError(
            "DIRTY-SOURCE",
            "Source worktree is dirty; refuse to pin from a mixed tree.",
            path=str(source),
        )


def resolve_commit(source: Path, commit: str) -> str:
    resolved = git_text(source, "rev-parse", "--verify", f"{commit}^{{commit}}")
    if not re.fullmatch(r"[0-9a-f]{40}", resolved):
        raise PinError("NOT-A-COMMIT", f"Commit did not resolve to a full SHA: {commit}.")
    return resolved


def source_tree(source: Path, commit: str) -> str:
    return git_text(source, "rev-parse", "--verify", f"{commit}^{{tree}}")


def parse_ls_tree(payload: bytes) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for raw in payload.split(b"\0"):
        if not raw:
            continue
        try:
            meta, path_b = raw.split(b"\t", 1)
            mode, obj_type, sha = meta.decode("ascii").split()
        except ValueError as error:
            raise PinError("TREE-INVALID", f"Unreadable ls-tree entry: {error}.") from error
        path = path_b.decode("utf-8")
        entries.append(
            {
                "mode": mode,
                "type": obj_type,
                "sha": sha,
                "path": path,
            }
        )
    return entries


def list_commit_blobs(source: Path, commit: str) -> list[dict[str, str]]:
    payload = git_bytes(source, "ls-tree", "-r", "-z", "--full-tree", commit)
    entries = parse_ls_tree(payload)
    if not entries:
        raise PinError("EMPTY-TREE", "Commit tree has no blobs to capture.")
    checked: list[dict[str, str]] = []
    for entry in entries:
        path = entry["path"]
        if is_unsafe_relpath(path):
            raise PinError("TRAVERSAL", f"Tree path is not a safe relative path: {path}.", path=path)
        if entry["type"] == "commit" or entry["mode"] == "160000":
            raise PinError("SUBMODULE", f"Commit tree contains a gitlink: {path}.", path=path)
        if entry["mode"] == "120000" or entry["type"] == "link":
            raise PinError("SYMLINK", f"Commit tree contains a symlink: {path}.", path=path)
        if entry["type"] != "blob" or entry["mode"] not in ALLOWED_GIT_MODES:
            raise PinError(
                "UNSUPPORTED-MODE",
                f"Unsupported tree entry {entry['mode']} {entry['type']} at {path}.",
                path=path,
            )
        if not re.fullmatch(r"[0-9a-f]{40}", entry["sha"]):
            raise PinError("BLOB-MISMATCH", f"Tree entry SHA is not a blob id: {path}.", path=path)
        checked.append(entry)
    return checked


def cat_blobs(source: Path, shas: Iterable[str]) -> dict[str, bytes]:
    unique = sorted(set(shas))
    if not unique:
        return {}
    payload = b"".join(f"{sha}\n".encode("ascii") for sha in unique)
    result = git_run(source, ["cat-file", "--batch"], input_bytes=payload)
    stdout = result.stdout
    offset = 0
    blobs: dict[str, bytes] = {}
    for sha in unique:
        header_end = stdout.find(b"\n", offset)
        if header_end < 0:
            raise PinError("BLOB-MISMATCH", f"cat-file header missing for {sha}.")
        header = stdout[offset:header_end].decode("ascii")
        offset = header_end + 1
        parts = header.split()
        if len(parts) < 3 or parts[0] != sha:
            raise PinError("BLOB-MISMATCH", f"cat-file header mismatch: {header}.")
        if parts[1] == "missing":
            raise PinError("BLOB-MISMATCH", f"Blob {sha} is missing from the source object store.")
        size = int(parts[2])
        data = stdout[offset : offset + size]
        if len(data) != size:
            raise PinError("BLOB-MISMATCH", f"Truncated blob {sha}.")
        offset += size
        if offset < len(stdout) and stdout[offset : offset + 1] == b"\n":
            offset += 1
        if git_blob_sha1(data) != sha:
            raise PinError("BLOB-MISMATCH", f"Blob bytes do not hash to {sha}.")
        if len(data) != size:
            raise PinError("SIZE-MISMATCH", f"Blob {sha} size mismatch.")
        blobs[sha] = data
    return blobs


def write_bytes_exclusive(path: Path, data: bytes, *, mode: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | O_BINARY
    permission = 0o755 if mode == "100755" else 0o644
    try:
        fd = os.open(path, flags, permission)
    except FileExistsError as error:
        raise PinError("OUTPUT-COLLISION", f"Capture path already exists: {path}.", path=str(path)) from error
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def capture_digest(files: Iterable[Mapping[str, object]]) -> str:
    digest = hashlib.sha256()
    for item in sorted(files, key=lambda row: str(row["path"])):
        digest.update(str(item["path"]).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(item["sha256"]).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def adapter_relpath(alias: str) -> str:
    return posix_path(str(ADAPTER_ROOT / alias / "SKILL.md"))


def render_adapter(*, alias: str, skill: str, commit: str, nonce: str) -> str:
    original = original_skill_posix(skill)
    refs = references_prefix(skill)
    return (
        f"---\n"
        f"name: {alias}\n"
        f"description: >\n"
        f"  DERIVED task-local runtime adapter for {skill} pinned at {short_commit(commit)}.\n"
        f"  Not the original skill. Folder name matches this frontmatter name.\n"
        f"  Read the immutable captured SKILL.md this adapter names.\n"
        f"---\n"
        f"\n"
        f"# DERIVED adapter — `{alias}`\n"
        f"\n"
        f"This file is **DERIVED**. It is not byte-identical to the captured\n"
        f"skill and must not replace it. The immutable original in this capture is:\n"
        f"\n"
        f"`{original}`\n"
        f"\n"
        f"Load this alias, then read that original `SKILL.md` and any reference it\n"
        f"names under `{refs}` in **this capture**. Resolve every named dependency\n"
        f"against the captured tree. Do not read a receipt, oracle, or a global\n"
        f"skills copy.\n"
        f"\n"
        f"## Runtime canary\n"
        f"\n"
        f"If this derived adapter was the skill you loaded, return exactly one line:\n"
        f"\n"
        f"{canary_line(nonce)}\n"
    )


def probe_git_env() -> dict[str, str]:
    return {
        "GIT_AUTHOR_NAME": "skill-runtime-pin",
        "GIT_AUTHOR_EMAIL": "skill-runtime-pin@invalid",
        "GIT_COMMITTER_NAME": "skill-runtime-pin",
        "GIT_COMMITTER_EMAIL": "skill-runtime-pin@invalid",
    }


def init_probe_git(probe_root: Path) -> None:
    git_run(probe_root, ["init", "-q"])
    git_run(probe_root, ["config", "core.autocrlf", "false"])
    git_run(probe_root, ["config", "core.symlinks", "false"])
    git_run(probe_root, ["config", "core.filemode", "false"])


def store_blob(probe_root: Path, data: bytes) -> str:
    stored = git_run(
        probe_root, ["hash-object", "-w", "--stdin"], input_bytes=data
    ).stdout.decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", stored):
        raise PinError("BLOB-MISMATCH", f"hash-object did not return a blob id: {stored}.")
    return stored


def commit_capture_index(probe_root: Path, source_tree_sha: str, source_commit: str) -> str:
    tree = git_text(probe_root, "write-tree")
    if tree != source_tree_sha:
        raise PinError(
            "TREE-MISMATCH",
            f"Captured git tree {tree} does not match source tree {source_tree_sha}.",
        )
    commit = git_run(
        probe_root,
        ["commit-tree", tree, "-m", f"skill-runtime-pin capture of {source_commit}"],
        extra_env=probe_git_env(),
    ).stdout.decode("ascii").strip()
    git_run(probe_root, ["update-ref", "HEAD", commit])
    return tree


def stage_capture_index(probe_root: Path, entries: list[dict[str, str]]) -> None:
    lines = "".join(f"{item['mode']} {item['sha']}\t{item['path']}\n" for item in entries)
    git_run(probe_root, ["update-index", "--index-info"], input_bytes=lines.encode("utf-8"))


def materialize(
    *,
    source: Path,
    commit: str,
    task_root: Path,
    skill: str = DEFAULT_SKILL,
) -> dict[str, object]:
    source = source.resolve()
    task_root = task_root.resolve()
    skill = normalize_skill_name(skill)
    if task_root.exists():
        raise PinError(
            "OUTPUT-COLLISION",
            "Task root already exists; refuse to overwrite.",
            path=str(task_root),
        )
    if not paths_disjoint(source, task_root):
        raise PinError(
            "OUTPUT-COLLISION",
            "Task root must sit entirely outside the source tree.",
            path=str(task_root),
        )
    inside = git_run(source, ["rev-parse", "--is-inside-work-tree"], check=False)
    if inside.returncode != 0 or inside.stdout.strip() != b"true":
        raise PinError("NOT-A-COMMIT", "Source is not a git repository.", path=str(source))
    require_clean_source(source)
    commit_sha = resolve_commit(source, commit)
    tree_sha = source_tree(source, commit_sha)
    entries = list_commit_blobs(source, commit_sha)
    original = original_skill_posix(skill)
    original_entry = next((item for item in entries if item["path"] == original), None)
    if original_entry is None:
        raise PinError("MISSING-SKILL", f"Commit does not contain {original}.", path=original)
    alias = alias_for(skill, commit_sha)
    adapter_path = adapter_relpath(alias)
    if any(item["path"] == adapter_path for item in entries):
        raise PinError(
            "OUTPUT-COLLISION",
            "Capture already contains the adapter path; refuse to overwrite.",
            path=adapter_path,
        )

    task_root.mkdir(parents=True, exist_ok=False)
    probe_root = task_root / PROBE_DIRNAME
    probe_root.mkdir()
    init_probe_git(probe_root)

    blobs = cat_blobs(source, (item["sha"] for item in entries))
    files: list[dict[str, object]] = []
    for entry in entries:
        data = blobs[entry["sha"]]
        target = probe_root / entry["path"]
        if not paths_disjoint(probe_root / ".git", target) and (
            posix_path(entry["path"]) == ".git" or posix_path(entry["path"]).startswith(".git/")
        ):
            raise PinError("TRAVERSAL", f"Refusing to write into .git: {entry['path']}.", path=entry["path"])
        write_bytes_exclusive(target, data, mode=entry["mode"])
        stored = store_blob(probe_root, data)
        if stored != entry["sha"]:
            raise PinError(
                "BLOB-MISMATCH",
                f"Probe hash-object {stored} does not match source blob {entry['sha']}.",
                path=entry["path"],
            )
        digest = sha256_bytes(data)
        if git_blob_sha1(target.read_bytes()) != entry["sha"]:
            raise PinError("BLOB-MISMATCH", f"Written bytes diverged from blob {entry['sha']}.", path=entry["path"])
        if len(data) != target.stat().st_size:
            raise PinError("SIZE-MISMATCH", f"Written size diverged for {entry['path']}.", path=entry["path"])
        files.append(
            {
                "path": entry["path"],
                "git_mode": entry["mode"],
                "git_blob": entry["sha"],
                "sha256": digest,
                "bytes": len(data),
            }
        )
    stage_capture_index(probe_root, entries)
    probe_tree = commit_capture_index(probe_root, tree_sha, commit_sha)
    before = capture_digest(files)

    nonce = secrets.token_hex(16)
    adapter_body = render_adapter(alias=alias, skill=skill, commit=commit_sha, nonce=nonce)
    adapter_bytes = adapter_body.encode("utf-8")
    write_bytes_exclusive(probe_root / adapter_path, adapter_bytes, mode="100644")
    after = capture_digest(files)
    if after != before:
        raise PinError("MUTATION", "Capture digest changed while writing the derived adapter.")
    original_file = next(item for item in files if item["path"] == original)
    original_disk = (probe_root / original).read_bytes()
    if sha256_bytes(original_disk) != original_file["sha256"]:
        raise PinError("MUTATION", "Original SKILL.md was modified while writing the adapter.", path=original)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "source_commit": commit_sha,
        "source_tree": tree_sha,
        "probe_tree": probe_tree,
        "skill": skill,
        "alias": alias,
        "original_skill_path": original,
        "original_git_blob": original_entry["sha"],
        "original_sha256": original_file["sha256"],
        "original_bytes": original_file["bytes"],
        "adapter_path": adapter_path,
        "adapter_kind": "DERIVED",
        "adapter_sha256": sha256_bytes(adapter_bytes),
        "adapter_bytes": len(adapter_bytes),
        "transformation": (
            "Single versioned discovery adapter; captured SKILL.md is unmodified; "
            "canary nonce lives in the adapter and the receipt, never in the assembled consumer prompt."
        ),
        "capture_sha256_before": before,
        "capture_sha256_after": after,
        "files": files,
        "consumers": {
            "codex": {
                "model": CODEX_MODEL,
                "home_isolated_by_ignore_user_config": False,
                "catalog_exclusive": False,
            },
            "cursor": {
                "model": CURSOR_MODEL,
                "catalog_exclusive": False,
                "adapter_byte_identical": False,
            },
        },
    }
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "alias": alias,
        "nonce": nonce,
        "canary": canary_line(nonce),
        "original_skill_path": original,
        "original_git_blob": original_entry["sha"],
        "original_sha256": original_file["sha256"],
        "original_bytes": original_file["bytes"],
        "source_commit": commit_sha,
        "probe_root": str(probe_root),
        "adapter_path": adapter_path,
        "allowed_read_prefixes": [original, references_prefix(skill)],
        "forbidden_outside_probe": True,
    }
    write_json(task_root / MANIFEST_NAME, manifest)
    write_json(task_root / RECEIPT_NAME, receipt)
    return make_report(
        "materialize",
        "PASS",
        [],
        task_root=str(task_root),
        probe_root=str(probe_root),
        alias=alias,
        source_commit=commit_sha,
        original_sha256=original_file["sha256"],
        capture_sha256=after,
    )


def load_pin(task_root: Path) -> tuple[dict[str, Any], dict[str, Any], Path]:
    task_root = task_root.resolve()
    manifest_path = task_root / MANIFEST_NAME
    receipt_path = task_root / RECEIPT_NAME
    probe_root = task_root / PROBE_DIRNAME
    if not manifest_path.is_file() or not receipt_path.is_file() or not probe_root.is_dir():
        raise PinError("PIN-MISSING", "Task root is not a complete skill-runtime-pin output.", path=str(task_root))
    manifest = load_json(manifest_path)
    receipt = load_json(receipt_path)
    recorded = str(receipt.get("probe_root", "") or "")
    if recorded and Path(recorded).resolve() != probe_root:
        raise PinError(
            "PIN-MISSING",
            "Receipt probe_root does not match task-local probe/.",
            path=str(receipt_path),
        )
    return manifest, receipt, probe_root


def verify_capture(task_root: Path) -> dict[str, object]:
    manifest, receipt, probe_root = load_pin(task_root)
    findings: list[dict[str, object]] = []
    files = list(manifest.get("files") or [])
    if not files:
        raise PinError("PIN-MISSING", "Manifest has no captured files.")
    by_path = {str(item["path"]): item for item in files}
    adapter_rel = str(manifest["adapter_path"])
    original_rel = str(manifest["original_skill_path"])
    expected_paths = set(by_path)
    expected_paths.add(adapter_rel)
    physical, links = list_probe_files(probe_root)
    for rel, kind in links:
        findings.append(finding(kind, f"Probe contains a link that was not followed: {rel}.", path=rel))
    for rel in sorted(set(physical) - expected_paths):
        findings.append(finding("EXTRA-FILE", f"Probe contains an unexpected file: {rel}.", path=rel))
    for relative, item in by_path.items():
        target = probe_root / relative
        if is_link_or_reparse(target):
            findings.append(
                finding(link_kind(target), f"Captured path is a link: {relative}.", path=relative)
            )
            continue
        if not is_regular_nonlink(target):
            findings.append(finding("REMOVAL", f"Captured file is missing: {relative}.", path=relative))
            continue
        data = target.read_bytes()
        digest = sha256_bytes(data)
        blob = git_blob_sha1(data)
        if len(data) != int(item["bytes"]):
            findings.append(finding("SIZE-MISMATCH", f"Captured size changed: {relative}.", path=relative))
        if digest != item["sha256"]:
            findings.append(finding("MISMATCH", f"Captured SHA-256 changed: {relative}.", path=relative))
        if blob != item["git_blob"]:
            findings.append(finding("BLOB-MISMATCH", f"Captured git blob changed: {relative}.", path=relative))
    adapter = probe_root / adapter_rel
    original = probe_root / original_rel
    if is_link_or_reparse(adapter):
        findings.append(finding(link_kind(adapter), "Derived adapter is a link.", path=adapter_rel))
    elif not is_regular_nonlink(adapter):
        findings.append(finding("REMOVAL", "Derived adapter is missing.", path=adapter_rel))
    else:
        adapter_bytes = adapter.read_bytes()
        if sha256_bytes(adapter_bytes) != manifest["adapter_sha256"]:
            findings.append(finding("MUTATION", "Derived adapter was mutated.", path=adapter_rel))
        try:
            text = adapter_bytes.decode("utf-8")
        except UnicodeError:
            findings.append(finding("ADAPTER-INVALID", "Adapter is not UTF-8.", path=adapter_rel))
            text = ""
        alias = str(manifest["alias"])
        if f"name: {alias}" not in text.splitlines()[0:12]:
            findings.append(finding("ADAPTER-INVALID", "Adapter frontmatter name does not match the alias.", path=adapter_rel))
        if adapter.parent.name != alias:
            findings.append(finding("ADAPTER-INVALID", "Adapter folder does not match the alias.", path=adapter_rel))
        if receipt.get("canary") not in text:
            findings.append(finding("ADAPTER-INVALID", "Adapter does not contain the receipt canary.", path=adapter_rel))
        if original_rel not in text:
            findings.append(finding("ADAPTER-INVALID", "Adapter does not point at the captured original SKILL.md.", path=adapter_rel))
        if CANARY_PREFIX in CONSUMER_PROMPT:
            findings.append(finding("PROMPT-CONTAINS-NONCE", "Internal prompt constant leaked a canary."))
    if is_link_or_reparse(original):
        findings.append(finding(link_kind(original), "Original SKILL.md is a link.", path=original_rel))
    elif not is_regular_nonlink(original):
        findings.append(finding("REMOVAL", "Original SKILL.md is missing.", path=original_rel))
    else:
        original_bytes = original.read_bytes()
        if sha256_bytes(original_bytes) != manifest["original_sha256"]:
            findings.append(finding("MUTATION", "Original SKILL.md is not the captured bytes.", path=original_rel))
        if git_blob_sha1(original_bytes) != manifest["original_git_blob"]:
            findings.append(finding("BLOB-MISMATCH", "Original SKILL.md git blob diverged.", path=original_rel))
    if receipt.get("nonce") and canary_line(str(receipt["nonce"])) != receipt.get("canary"):
        findings.append(finding("ADAPTER-INVALID", "Receipt nonce/canary pair is inconsistent."))
    if receipt.get("canary", "").startswith(CANARY_PREFIX) and str(receipt.get("canary", "")).replace(CANARY_PREFIX, "") in CONSUMER_PROMPT:
        findings.append(finding("PROMPT-CONTAINS-NONCE", "Assembled consumer prompt constant contains the nonce."))
    current = capture_digest(files)
    if current != manifest.get("capture_sha256_before") or current != manifest.get("capture_sha256_after"):
        findings.append(finding("MUTATION", "Capture digest does not match the sealed before/after hashes."))
    if (task_root / RECEIPT_NAME).is_relative_to(probe_root):
        findings.append(finding("RECEIPT-IN-PROBE", "Receipt must live outside probe-root."))
    verdict = "FAIL" if findings else "PASS"
    return make_report(
        "verify",
        verdict,
        findings,
        alias=manifest.get("alias"),
        source_commit=manifest.get("source_commit"),
        capture_sha256=current,
        adapter_kind=manifest.get("adapter_kind"),
        physical_files=len(physical),
    )


def consumer_prompt(alias: str, *, style: str) -> str:
    if style == "codex":
        return f"${alias} {CONSUMER_PROMPT}"
    if style == "cursor":
        return f"/{alias} {CONSUMER_PROMPT}"
    raise PinError("UNSUPPORTED-CONSUMER", f"Unknown consumer style: {style}.")


def assemble_commands(task_root: Path, consumer: str) -> dict[str, object]:
    verified = verify_capture(task_root)
    if verified["verdict"] != "PASS":
        raise PinError("PREFLIGHT-FAILED", "Capture failed verify; refuse to assemble a probe.")
    manifest, receipt, probe_root = load_pin(task_root)
    alias = str(manifest["alias"])
    nonce = str(receipt["nonce"])
    wanted = ("codex", "cursor") if consumer == "all" else (consumer,)
    commands: dict[str, object] = {}
    for name in wanted:
        prompt = consumer_prompt(alias, style=name)
        if nonce in prompt or receipt["canary"] in prompt:
            raise PinError("PROMPT-CONTAINS-NONCE", "Assembled prompt contained the canary nonce.")
        if name == "codex":
            argv = codex_exec_argv(probe_root, prompt)
            commands[name] = {
                "cwd": str(probe_root),
                "program": "codex",
                "argv": argv,
                "inspect": {
                    "argv": ["codex", "debug", "prompt-input", "runtime-catalog-probe"],
                    "require_alias_entries": 1,
                    "require_adapter_path": str(probe_root / str(manifest["adapter_path"])),
                },
                "exec": {"argv": argv},
                "prompt": prompt,
                "requested_model": CODEX_MODEL,
                "limits": {
                    "ignore_user_config_isolates_home": False,
                    "catalog_exclusive": False,
                    "codex_emits_system_init": False,
                    "served_model_observed": False,
                    "status": "DESIGN",
                },
            }
        elif name == "cursor":
            argv = cursor_argv(probe_root, prompt)
            commands[name] = {
                "cwd": str(probe_root),
                "program": cursor_program(),
                "argv": argv,
                "prompt": prompt,
                "flags": {
                    "mode": "ask",
                    "trust": True,
                    "workspace": str(probe_root),
                    "output_format": "stream-json",
                    "model": CURSOR_MODEL,
                    "prompt": prompt,
                },
                "limits": {
                    "catalog_exclusive": False,
                    "adapter_byte_identical": False,
                    "status": "DESIGN",
                },
            }
        else:
            raise PinError("UNSUPPORTED-CONSUMER", f"Unknown consumer: {name}.")
    write_json(task_root / COMMANDS_NAME, {"schema_version": SCHEMA_VERSION, "commands": commands})
    return make_report(
        "assemble",
        "PASS",
        [],
        commands=commands,
        prompt_contains_nonce=False,
        status="DESIGN",
    )


def _json_skill_entries(value: object) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, list):
        for item in value:
            found.extend(_json_skill_entries(item))
        return found
    if isinstance(value, dict):
        name = value.get("name") or value.get("skill") or value.get("id")
        path = value.get("path") or value.get("file") or value.get("skill_path")
        if isinstance(name, str) and isinstance(path, str) and Path(path).name.lower() == "skill.md":
            found.append((name, path))
        for nested in value.values():
            found.extend(_json_skill_entries(nested))
    return found


def extract_text_skill_entries(text: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for match in NAME_PATH_RE.finditer(text):
        entries.append((match.group(1), match.group(2).strip()))
    for match in PATH_NAME_RE.finditer(text):
        entries.append((match.group(2), match.group(1).strip()))
    for match in SKILL_FILE_RE.finditer(text):
        entries.append((match.group(1), match.group(2).strip()))
    for match in ADAPTER_PATH_RE.finditer(text):
        entries.append((match.group("alias"), match.group("path")))
    for match in RELATIVE_ADAPTER_RE.finditer(text):
        entries.append((match.group("alias"), match.group("path")))
    unique: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for name, path in entries:
        key = (name, posix_path(path))
        if key in seen:
            continue
        seen.add(key)
        unique.append((name, path))
    return unique


def catalog_blocks(text: str) -> list[tuple[dict[str, str], list[tuple[str, str]]]]:
    stripped = text.lstrip()
    loaded = None
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError:
            loaded = None
    if loaded is None:
        return [(parse_skill_roots(text), extract_text_skill_entries(text))]
    blocks: list[tuple[dict[str, str], list[tuple[str, str]]]] = []
    structured = _json_skill_entries(loaded)
    if structured:
        blocks.append(({}, structured))
    for blob in iter_json_strings(loaded):
        roots = parse_skill_roots(blob)
        entries = extract_text_skill_entries(blob)
        if roots or entries:
            blocks.append((roots, entries))
    if not blocks:
        blocks.append(({}, []))
    return blocks


def extract_skill_entries(text: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for _roots, block_entries in catalog_blocks(text):
        for name, path in block_entries:
            key = (name, posix_path(path))
            if key in seen:
                continue
            seen.add(key)
            entries.append((name, path))
    return entries


def path_is_adapter(
    path: str,
    probe_root: Path,
    alias: str,
    skill_roots: Mapping[str, str] | None = None,
) -> bool:
    return resolve_catalog_path(path, probe_root, skill_roots or {}) == expected_adapter_key(
        probe_root, alias
    )


def inspect_prompt_input(task_root: Path, prompt_input: Path) -> dict[str, object]:
    verified = verify_capture(task_root)
    if verified["verdict"] != "PASS":
        raise PinError("PREFLIGHT-FAILED", "Capture failed verify; refuse to inspect a catalog dump.")
    manifest, _receipt, probe_root = load_pin(task_root)
    alias = str(manifest["alias"])
    text = prompt_input.read_text(encoding="utf-8")
    blocks = catalog_blocks(text)
    alias_entries: list[tuple[str, str, Mapping[str, str]]] = []
    merged_roots: dict[str, str] = {}
    all_entries = 0
    for roots, entries in blocks:
        merged_roots.update(roots)
        all_entries += len(entries)
        for name, path in entries:
            if name == alias:
                alias_entries.append((name, path, roots))
    adapter_hits: list[tuple[str, str]] = []
    seen_adapter: set[str] = set()
    expected = expected_adapter_key(probe_root, alias)
    for name, path, roots in alias_entries:
        if not path_is_adapter(path, probe_root, alias, roots):
            continue
        if expected in seen_adapter:
            continue
        seen_adapter.add(expected)
        adapter_hits.append((name, path))
    findings: list[dict[str, object]] = []
    if len(adapter_hits) != 1:
        findings.append(
            finding(
                "CATALOG-ALIAS-COUNT",
                f"Expected exactly 1 catalog entry for {alias} at the derived adapter path; found {len(adapter_hits)}.",
            )
        )
    for name, path, roots in alias_entries:
        if not path_is_adapter(path, probe_root, alias, roots):
            findings.append(
                finding(
                    "CATALOG-ALIAS-PATH",
                    f"Alias {alias} catalog path is not the derived adapter: {path}.",
                    path=path,
                )
            )
    verdict = "FAIL" if findings else "PASS"
    return make_report(
        "inspect-prompt",
        verdict,
        findings,
        alias=alias,
        alias_entries=[{"name": name, "path": path} for name, path in adapter_hits],
        other_entries=all_entries - len(alias_entries),
        skill_roots=merged_roots,
    )


def read_path_key(raw: str, probe_root: Path) -> str:
    text = posix_path(raw.strip())
    if is_absolute_path_string(text):
        return exact_path_key(text)
    return exact_path_key(probe_root / text)


def relative_under_probe(key: str, probe_root: Path) -> str | None:
    prefix = exact_path_key(probe_root).rstrip("/") + "/"
    if not key.startswith(prefix):
        return None
    return key[len(prefix) :]


def is_allowed_read(raw: str, probe_root: Path, skill: str, adapter_rel: str) -> bool:
    key = read_path_key(raw, probe_root)
    relative = relative_under_probe(key, probe_root)
    if relative is None or is_unsafe_relpath(relative):
        return False
    if relative == exact_path_key(original_skill_posix(skill)):
        return True
    if relative == exact_path_key(adapter_rel):
        return True
    prefix = exact_path_key(references_prefix(skill).rstrip("/")) + "/"
    return relative.startswith(prefix)


def original_consumed(
    *,
    tool_reads: list[str],
    injected: list[Mapping[str, object]],
    probe_root: Path,
    original_rel: str,
    original_sha256: str,
) -> bool:
    expected = exact_path_key(probe_root / original_rel)
    for raw in tool_reads:
        if read_path_key(raw, probe_root) == expected:
            return True
    for item in injected:
        path = str(item.get("path", ""))
        digest = str(item.get("sha256", "")).lower()
        if read_path_key(path, probe_root) == expected and digest == original_sha256.lower():
            return True
    return False


def grade_transcript(task_root: Path, transcript_path: Path) -> dict[str, object]:
    verified = verify_capture(task_root)
    if verified["verdict"] != "PASS":
        raise PinError("PREFLIGHT-FAILED", "Capture failed verify; refuse to grade a probe.")
    manifest, receipt, probe_root = load_pin(task_root)
    payload = load_json(transcript_path)
    if not isinstance(payload, dict):
        raise PinError("TRANSCRIPT-INVALID", "Transcript root must be an object.")
    consumer = str(payload.get("consumer", "")).strip().lower()
    stdout = str(payload.get("stdout", ""))
    tool_reads = [str(item) for item in payload.get("tool_reads", [])]
    injected = list(payload.get("injected_bodies") or [])
    canary = str(receipt["canary"]).strip()
    findings: list[dict[str, object]] = []
    if consumer not in {"cursor", "codex"}:
        findings.append(finding("CONSUMER-MISSING", "Transcript must name consumer cursor or codex."))
    if payload.get("exit_code") != 0:
        findings.append(finding("EXIT-CODE", "Normalized reception requires exit_code 0."))
    if stdout.strip() != canary:
        findings.append(
            finding(
                "CANARY-MISMATCH",
                "stdout.strip() must equal the receipt canary and nothing else.",
            )
        )
    if consumer == "cursor":
        expected_argv = cursor_argv(probe_root, consumer_prompt(str(manifest["alias"]), style="cursor"))
    elif consumer == "codex":
        expected_argv = codex_exec_argv(probe_root, consumer_prompt(str(manifest["alias"]), style="codex"))
    else:
        expected_argv = []
    observed_argv = payload.get("argv")
    if not isinstance(observed_argv, list):
        findings.append(finding("ARGV-MISSING", "Transcript argv must be the assembled consumer argv list."))
    elif [str(item) for item in observed_argv] != expected_argv:
        findings.append(finding("ARGV-MISMATCH", "Transcript argv does not match the assembled consumer argv."))
    requested_model = CURSOR_MODEL if consumer == "cursor" else CODEX_MODEL if consumer == "codex" else ""
    served_model_observed = False
    served_model = ""
    if consumer == "cursor":
        label = cursor_served_label(payload.get("system_init"))
        if label is None:
            findings.append(
                finding(
                    "CURSOR-INIT-MISSING",
                    "Cursor reception requires the raw system/init event (type=system, subtype=init).",
                )
            )
        elif CURSOR_SERVED_MODEL_MAP.get(label) != CURSOR_MODEL:
            findings.append(
                finding(
                    "CURSOR-INIT-MODEL",
                    f"Served model label {label!r} is not the closed mapping to {CURSOR_MODEL}.",
                )
            )
        else:
            served_model_observed = True
            served_model = label
    elif consumer == "codex":
        if payload.get("system_init") not in (None, {}, False):
            findings.append(
                finding(
                    "CODEX-INIT-INVENTED",
                    "Codex CLI does not emit system/init; do not treat one as a served-model event.",
                )
            )
        if payload.get("served_model"):
            findings.append(
                finding(
                    "CODEX-SERVED-MODEL-INVENTED",
                    "Codex CLI does not emit a served-model event in this pin; record the requested model via argv.",
                )
            )
        served_model_observed = False
        requested_model = CODEX_MODEL
    skill = str(manifest["skill"])
    adapter_rel = str(manifest["adapter_path"])
    original_rel = str(manifest["original_skill_path"])
    forbidden: list[str] = []
    receipt_key = exact_path_key(task_root / RECEIPT_NAME)
    manifest_key = exact_path_key(task_root / MANIFEST_NAME)
    for raw in tool_reads:
        key = read_path_key(raw, probe_root)
        if key in {receipt_key, manifest_key}:
            forbidden.append(raw)
            findings.append(finding("FORBIDDEN-READ", "Probe read the receipt or manifest oracle.", path=raw))
            continue
        if not is_allowed_read(raw, probe_root, skill, adapter_rel):
            forbidden.append(raw)
            findings.append(
                finding(
                    "FORBIDDEN-READ",
                    f"Probe read a path outside the capture original/refs: {raw}.",
                    path=raw,
                )
            )
    consumed = original_consumed(
        tool_reads=tool_reads,
        injected=injected,
        probe_root=probe_root,
        original_rel=original_rel,
        original_sha256=str(manifest["original_sha256"]),
    )
    if not consumed:
        findings.append(
            finding(
                "NONCE-WITHOUT-ORIGINAL",
                "Canary is not evidence by itself; the original captured SKILL.md was not consumed.",
            )
        )
    verdict = "FAIL" if findings else "PASS"
    return make_report(
        "grade",
        verdict,
        findings,
        original_consumed=consumed,
        canary_matched=stdout.strip() == canary,
        tool_reads=tool_reads,
        forbidden_reads=forbidden,
        zero_tool_calls=len(tool_reads) == 0,
        consumer=consumer,
        requested_model=requested_model,
        served_model=served_model,
        served_model_observed=served_model_observed,
        limits={
            "codex_emits_system_init": False,
            "served_model_observed": served_model_observed if consumer == "cursor" else False,
        },
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="runtime_pin.py")
    commands = parser.add_subparsers(dest="command", required=True)

    materialize_cmd = commands.add_parser("materialize")
    materialize_cmd.add_argument("--source", required=True, type=Path)
    materialize_cmd.add_argument("--commit", required=True)
    materialize_cmd.add_argument("--task-root", required=True, type=Path)
    materialize_cmd.add_argument("--skill", default=DEFAULT_SKILL)

    verify_cmd = commands.add_parser("verify")
    verify_cmd.add_argument("--task-root", required=True, type=Path)

    assemble_cmd = commands.add_parser("assemble")
    assemble_cmd.add_argument("--task-root", required=True, type=Path)
    assemble_cmd.add_argument("--consumer", required=True, choices=("codex", "cursor", "all"))

    inspect_cmd = commands.add_parser("inspect-prompt")
    inspect_cmd.add_argument("--task-root", required=True, type=Path)
    inspect_cmd.add_argument("--prompt-input", required=True, type=Path)

    grade_cmd = commands.add_parser("grade")
    grade_cmd.add_argument("--task-root", required=True, type=Path)
    grade_cmd.add_argument("--transcript", required=True, type=Path)
    return parser


def dispatch(args: argparse.Namespace) -> dict[str, object]:
    if args.command == "materialize":
        return materialize(
            source=args.source,
            commit=args.commit,
            task_root=args.task_root,
            skill=args.skill,
        )
    if args.command == "verify":
        return verify_capture(args.task_root)
    if args.command == "assemble":
        return assemble_commands(args.task_root, args.consumer)
    if args.command == "inspect-prompt":
        return inspect_prompt_input(args.task_root, args.prompt_input)
    if args.command == "grade":
        return grade_transcript(args.task_root, args.transcript)
    raise PinError("UNSUPPORTED-COMMAND", f"Unknown command: {args.command}.")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
        report = dispatch(args)
    except PinError as error:
        report = make_report("error", "FAIL", [error.as_finding()])
        sys.stdout.buffer.write(canonical_json(report))
        return 1
    sys.stdout.buffer.write(canonical_json(report))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
