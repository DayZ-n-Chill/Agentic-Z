from __future__ import annotations

import hashlib
import json
import subprocess
import os
from pathlib import Path

import pytest

# scripts/dev/knowledge-pack: the folder that holds the packctl package.
PACK_ROOT = Path(__file__).resolve().parents[2]
# The Agentic-Z repository root.
REPO_ROOT = PACK_ROOT.parents[2]
# Optional: a checkout of the original pack tree. A few tests check files that
# only exist in that tree (its .gitattributes, promotion map targets and so on).
SOURCE_ROOT_ENV = "KP_SOURCE_ROOT"


def tree_roots() -> list[Path]:
    """Roots that may hold the files a test expects, best match first."""
    roots: list[Path] = []
    override = os.environ.get(SOURCE_ROOT_ENV)
    if override:
        roots.append(Path(override))
    roots.append(REPO_ROOT)
    return roots


def locate_tree_file(relative: str) -> Path | None:
    """Find a file named by its path in the original pack tree.

    Looks in the override checkout first, then in this repository, where the
    original tools/ folder lives at scripts/tools/.
    """
    for root in tree_roots():
        candidates = [relative]
        if relative.startswith("tools/"):
            candidates.insert(0, "scripts/" + relative)
        for candidate in candidates:
            path = root / candidate
            if path.exists():
                return path
    return None


def require_tree_file(relative: str) -> Path:
    """Like locate_tree_file, but skips the calling test when nothing is found."""
    path = locate_tree_file(relative)
    if path is None:
        pytest.skip(
            f"{relative} is not in this repository; set {SOURCE_ROOT_ENV} to a "
            "checkout of the original pack tree to run this test"
        )
    return path


def require_tree_root(*relatives: str) -> Path:
    """Return the first root that holds every listed path, or skip the test."""
    for root in tree_roots():
        if all((root / relative).exists() for relative in relatives):
            return root
    pytest.skip(
        f"{', '.join(relatives)} not found in this repository; set "
        f"{SOURCE_ROOT_ENV} to a checkout of the original pack tree"
    )


ZERO_COMMIT = "0" * 40
ZERO_HASH = "0" * 64


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def source(
    source_id: str = "pack",
    *,
    revision: str = ZERO_COMMIT,
    license_id: str = "MIT",
) -> dict[str, object]:
    return {
        "source_id": source_id,
        "kind": "authored",
        "revision": revision,
        "license": license_id,
    }


def artifact(
    root: Path,
    path: str,
    *,
    role: str = "payload",
    license_id: str = "MIT",
    decisions: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    output_hash = sha256_file(root / path)
    inputs = decisions or [
        {
            "source_id": "pack",
            "source_revision": ZERO_COMMIT,
            "source_path": path,
            "source_hash": output_hash,
            "license": license_id,
            "verification_level": "offline_tested",
            "decision": "adopt",
            "decision_evidence": "Fixture source and output are byte-identical.",
        }
    ]
    value: dict[str, object] = {
        "artifact_id": path.replace("/", "-").replace(".", "-"),
        "output_path": path,
        "distribution_role": role,
        "license": license_id,
        "verification_level": "offline_tested",
        "routing_artifact_id": "fixture",
        "hash_policy": "sha256",
        "output_hash": output_hash,
        "inputs": inputs,
    }
    if role == "repo_only":
        value["distribution_reason"] = "Test support, not release payload."
    return value


def self_map_artifact() -> dict[str, object]:
    return {
        "artifact_id": "source-map",
        "output_path": "sources/source-map.json",
        "distribution_role": "repo_only",
        "distribution_reason": "Self-referential provenance contract.",
        "license": "MIT",
        "verification_level": "offline_tested",
        "routing_artifact_id": "fixture",
        "hash_policy": "self_exempt",
        "inputs": [
            {
                "source_id": "pack",
                "source_revision": ZERO_COMMIT,
                "source_path": "source-map.contract",
                "source_hash": ZERO_HASH,
                "license": "MIT",
                "verification_level": "offline_tested",
                "decision": "adopt",
                "decision_evidence": "Fixture contract generates the self-exempt map.",
            }
        ],
    }


def make_source_map(
    root: Path,
    paths: list[str],
    *,
    role_overrides: dict[str, str] | None = None,
    license_overrides: dict[str, str] | None = None,
) -> dict[str, object]:
    role_overrides = role_overrides or {}
    license_overrides = license_overrides or {}
    artifacts = [
        artifact(
            root,
            path,
            role=role_overrides.get(path, "payload"),
            license_id=license_overrides.get(path, "MIT"),
        )
        for path in paths
        if path != "sources/source-map.json"
    ]
    artifacts.append(self_map_artifact())
    return {
        "schema_version": 1,
        "baseline_commit": ZERO_COMMIT,
        "claim_baseline_commit": ZERO_COMMIT,
        "release_id": "fixture",
        "dayz_build": "1.29.0.163451",
        "sources": [source()],
        "artifacts": artifacts,
        "excluded_inputs": [],
        "generated_artifacts": [
            {
                "artifact_id": "release-manifest",
                "output_path": "manifest.json",
                "generator": "packctl.builder",
                "license": "MIT",
            }
        ],
    }


@pytest.fixture
def repo_factory(tmp_path: Path):
    def factory(
        files: dict[str, str] | None = None,
        *,
        payload: set[str] | None = None,
        initialize_git: bool = True,
    ) -> Path:
        root = tmp_path / "repo"
        root.mkdir()
        initial = {
            "LICENSE": "MIT License\n",
            "README.md": "# Fixture\n",
        }
        initial.update(files or {})
        for relative, content in initial.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")

        claims = {
            "schema_version": 1,
            "claim_baseline_commit": ZERO_COMMIT,
            "claims": [],
        }
        write_json(root / "sources/claims.json", claims)

        all_paths = sorted(
            str(path.relative_to(root)).replace("\\", "/")
            for path in root.rglob("*")
            if path.is_file()
        )
        role_overrides = {
            path: "repo_only"
            for path in all_paths
            if payload is not None and path not in payload
        }
        source_map = make_source_map(
            root,
            all_paths + ["sources/source-map.json"],
            role_overrides=role_overrides,
        )
        write_json(root / "sources/source-map.json", source_map)

        if initialize_git:
            run_git(root, "init", "-q")
            run_git(root, "config", "user.email", "fixture@example.invalid")
            run_git(root, "config", "user.name", "Fixture")
            run_git(root, "add", ".")
            run_git(root, "commit", "-qm", "fixture")
        return root

    return factory
