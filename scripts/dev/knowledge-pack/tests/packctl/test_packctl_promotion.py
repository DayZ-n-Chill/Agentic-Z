from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import types
import uuid
from pathlib import Path

import pytest

from packctl_testlib import require_tree_root, run_git, write_json

import packctl.common as common
from packctl.common import canonical_json_bytes, sha256_bytes, tree_digest
from packctl.promotion import apply_promotion, check_promotion
import packctl.promotion as promotion


REQUIRED_SKILL_TARGETS = ["claude_user_skills", "agents_user_skills"]


def run_promote_process(
    cwd: Path,
    *args: str,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    process_environment = dict(os.environ)
    project_root = str(Path(__file__).resolve().parents[2])
    process_environment["PYTHONPATH"] = (
        project_root
        + os.pathsep
        + process_environment.get("PYTHONPATH", "")
    )
    process_environment.update(environment or {})
    return subprocess.run(
        [sys.executable, "-m", "packctl", "promote", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=process_environment,
    )


def transaction_root(plan: dict[str, object]) -> Path:
    return Path(str(plan["backup_root"])) / str(plan["transaction_id"])


def journal_events(root: Path) -> list[dict[str, object]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "events").glob("*.json"))
    ]


def assert_valid_event_chain(root: Path) -> list[dict[str, object]]:
    events = journal_events(root)
    assert events
    previous_hash = "0" * 64
    for sequence, event in enumerate(events):
        event_path = root / "events" / f"{sequence:08d}.json"
        assert event_path.is_file()
        assert event["schema_version"] == 1
        assert event["sequence"] == sequence
        assert event["transaction_id"] == root.name
        assert event["previous_event_hash"] == previous_hash
        material = dict(event)
        event_hash = str(material.pop("event_hash"))
        assert event_hash == sha256_bytes(canonical_json_bytes(material))
        previous_hash = event_hash
    return events


def seed_every_target_with_pre_state(
    root: Path,
    paths: dict[str, Path],
) -> None:
    commit = run_git(root, "rev-parse", "HEAD")
    specs = [
        ("fixture", "claude_user_skills", paths["claude"] / "demo"),
        ("fixture", "agents_user_skills", paths["agents"] / "demo"),
        (
            "fixture",
            "obsidian_snapshots",
            paths["vault"] / "fixture" / commit,
        ),
        (
            "fixture-root",
            "obsidian_snapshots",
            paths["vault"] / "fixture-root" / commit,
        ),
    ]
    unique_targets: dict[Path, int] = {}
    for _, _, target in specs:
        if target in unique_targets:
            continue
        unique_targets[target] = len(unique_targets)
        target.mkdir(parents=True, exist_ok=True)
        (target / "pre.txt").write_text(
            f"pre-{unique_targets[target]}\n",
            encoding="utf-8",
        )
    commit_test_adjudications(
        root,
        [
            {
                "artifact_id": artifact_id,
                "target_id": target_id,
                "observed_digest": tree_digest(target),
                "reason": "Fixture preimage required by recovery coverage.",
            }
            for artifact_id, target_id, target in specs
        ],
    )
    current_commit = run_git(root, "rev-parse", "HEAD")
    for artifact_id, target_id, target in specs:
        if target_id != "obsidian_snapshots":
            continue
        current = paths["vault"] / artifact_id / current_commit
        current.mkdir(parents=True, exist_ok=True)
        (current / "pre.txt").write_bytes((target / "pre.txt").read_bytes())


def assert_plan_state(
    plan: dict[str, object],
    *,
    state: str,
) -> None:
    digest_key = "before_digest" if state == "PRE" else "after_digest"
    for operation in plan["operations"]:
        target = Path(str(operation["target_path"]))
        assert tree_digest(target) == operation[digest_key]
        for logical_path in operation["logical_target_paths"].values():
            logical = Path(str(logical_path))
            assert (
                os.path.normcase(str(logical.resolve(strict=False)))
                == os.path.normcase(str(target.resolve(strict=False)))
            )
            assert tree_digest(logical) == operation[digest_key]


def start_lock_holder(lock_path: Path) -> subprocess.Popen[str]:
    script = r"""
import os
import sys

path = sys.argv[1]
fd = os.open(path, os.O_RDWR | os.O_CREAT)
if os.fstat(fd).st_size == 0:
    os.write(fd, b"\0")
    os.fsync(fd)
os.lseek(fd, 0, os.SEEK_SET)
if os.name == "nt":
    import msvcrt
    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
else:
    import fcntl
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
sys.stdout.write("ready\n")
sys.stdout.flush()
sys.stdin.readline()
"""
    holder = subprocess.Popen(
        [sys.executable, "-c", script, str(lock_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert holder.stdout is not None
    assert holder.stdout.readline().strip() == "ready"
    return holder


def codes(report: dict[str, object]) -> list[str]:
    return [str(item["code"]) for item in report["findings"]]


def promotion_fixture(
    repo_factory,
    tmp_path: Path,
    *,
    alias_skills: bool = False,
    writable: bool = True,
) -> tuple[Path, Path, Path, Path, dict[str, Path]]:
    root = repo_factory(
        {
            "skills/demo/SKILL.md": (
                "---\nname: demo\ndescription: Promotion fixture.\n---\n# Demo\n"
            )
        },
        payload={"LICENSE", "README.md", "skills/demo/SKILL.md"},
    )
    source_map_path = root / "sources/source-map.json"
    source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
    for item in source_map["artifacts"]:
        item["routing_artifact_id"] = (
            "fixture"
            if str(item["output_path"]).startswith("skills/demo/")
            else "fixture-root"
        )
    write_json(source_map_path, source_map)
    run_git(root, "add", "sources/source-map.json")
    run_git(root, "commit", "-qm", "route fixture artifacts")

    targets_root = tmp_path / "targets"
    claude = targets_root / "claude"
    agents = claude if alias_skills else targets_root / "agents"
    vault = targets_root / "vault"
    backups = targets_root / "backups"
    for path in {claude, agents, vault, backups}:
        path.mkdir(parents=True, exist_ok=True)

    promotion_map = {
        "schema_version": 1,
        "artifacts": [
            {
                "artifact_id": "fixture",
                "repo_path": "skills/demo",
                "artifact_kind": "tree",
                "applicability": "domain_invariant",
                "vault_targets": ["obsidian_snapshots"],
                "skill_target_ids": REQUIRED_SKILL_TARGETS,
            },
            {
                "artifact_id": "fixture-root",
                "repo_path": ".",
                "artifact_kind": "tree",
                "applicability": "governance",
                "vault_targets": ["obsidian_snapshots"],
                "skill_target_ids": [],
                "not_applicable_reason": (
                    "Fixture repository contract is durable vault context, "
                    "not an installed skill."
                ),
            }
        ],
    }
    map_path = tmp_path / "promotion-map.json"
    write_json(map_path, promotion_map)
    config = {
        "schema_version": 1,
        "path_aliases": {},
        "allowed_physical_roots": [str(targets_root)],
        "forbidden_physical_roots": [str(targets_root / "plugins")],
        "backup_root": str(backups),
        "targets": {
            "claude_user_skills": {
                "path": str(claude),
                "ownership": "user_owned",
                "writable": writable,
            },
            "agents_user_skills": {
                "path": str(agents),
                "ownership": "user_owned",
                "writable": writable,
            },
            "obsidian_snapshots": {
                "path": str(vault),
                "ownership": "user_owned",
                "writable": writable,
            },
        },
    }
    config_path = tmp_path / "local-targets.json"
    write_json(config_path, config)
    plan_path = tmp_path / "plan.json"
    return root, map_path, config_path, plan_path, {
        "targets": targets_root,
        "claude": claude,
        "agents": agents,
        "vault": vault,
        "backups": backups,
    }


INSTALLATION_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
INSTALLATION_B = "bbbbbbbb-bbbb-4bbb-9bbb-bbbbbbbbbbbb"


def write_v2_config(config_path: Path, installation_id: str) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["schema_version"] = 2
    config["installation_id"] = installation_id
    write_json(config_path, config)


def backup_entries(paths: dict[str, Path]) -> list[Path]:
    return sorted(paths["backups"].rglob("*"))


def try_dir_link(src: Path, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(src, dest, target_is_directory=True)
        return True
    except OSError:
        # Captured as bytes and never decoded: cmd writes mklink's message in
        # the console code page, the OEM one (cp850 on a Spanish host) unless
        # the console runs UTF-8, and only the return code counts.
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(dest), str(src)],
            capture_output=True,
        )
        return result.returncode == 0


def rewrite_local_targets(
    config_path: Path,
    *,
    allowed: Path,
    dest_root: Path,
) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["allowed_physical_roots"] = [str(allowed)]
    config["forbidden_physical_roots"] = [str(allowed / "plugins")]
    config["backup_root"] = str(dest_root / "backups")
    config["targets"]["claude_user_skills"]["path"] = str(dest_root / "claude")
    config["targets"]["agents_user_skills"]["path"] = str(dest_root / "agents")
    config["targets"]["obsidian_snapshots"]["path"] = str(dest_root / "vault")
    write_json(config_path, config)


def move_fixture_dirs(paths: dict[str, Path], dest_root: Path) -> None:
    dest_root.mkdir(parents=True, exist_ok=True)
    for key in ("claude", "agents", "vault", "backups"):
        destination = dest_root / paths[key].name
        shutil.move(str(paths[key]), str(destination))
        paths[key] = destination


def lock_paths_for_plan(plan: dict[str, object]) -> set[str]:
    return {
        os.path.normcase(str(promotion._lock_path_for_root(root)))
        for root in promotion._lock_roots_for_plan(plan)
    }


def add_file_route(root: Path, map_path: Path) -> None:
    source_map_path = root / "sources/source-map.json"
    source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
    readme = next(
        item
        for item in source_map["artifacts"]
        if item["output_path"] == "README.md"
    )
    readme["routing_artifact_id"] = "fixture-file"
    write_json(source_map_path, source_map)
    run_git(root, "add", "sources/source-map.json")
    run_git(root, "commit", "-qm", "route file fixture")
    promotion_map = json.loads(map_path.read_text(encoding="utf-8"))
    promotion_map["artifacts"].append(
        {
            "artifact_id": "fixture-file",
            "repo_path": "README.md",
            "artifact_kind": "file",
            "applicability": "governance",
            "vault_targets": ["obsidian_snapshots"],
            "skill_target_ids": [],
            "not_applicable_reason": (
                "Fixture file is durable vault context, not a skill."
            ),
        }
    )
    write_json(map_path, promotion_map)


def commit_published_receipt(root: Path, report: dict[str, object], message: str) -> Path:
    receipt_path = Path(str(report["artifacts"]["receipt_path"]))
    run_git(root, "add", receipt_path.relative_to(root).as_posix())
    run_git(root, "commit", "-qm", message)
    return receipt_path


def seed_installed_demo(root: Path, target: Path) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    (target / "SKILL.md").write_bytes(
        (root / "skills/demo/SKILL.md").read_bytes()
    )
    return target


def _append_test_journal_event(
    sealed_transaction: Path,
    events: list[dict[str, object]],
    event_type: str,
    payload: dict[str, object],
) -> None:
    material: dict[str, object] = {
        "schema_version": 1,
        "sequence": len(events),
        "transaction_id": sealed_transaction.name,
        "event_type": event_type,
        "previous_event_hash": (
            str(events[-1]["event_hash"]) if events else "0" * 64
        ),
        "payload": payload,
    }
    event = dict(material)
    event["event_hash"] = sha256_bytes(canonical_json_bytes(material))
    write_json(
        sealed_transaction / "events" / f"{len(events):08d}.json",
        event,
    )
    events.append(event)


def commit_test_receipt(
    root: Path,
    *,
    backup_root: Path,
    target_path: Path,
    name: str,
    target_id: str,
    before_digest: str = "absent",
    after_digest: str,
    completed_at: str,
    seal_journal: bool = True,
    source_commit: str | None = None,
    schema_version: int = 1,
    installation_id: str | None = None,
    bootstrap: bool = False,
    sealed_receipt_path: Path | None = None,
) -> Path:
    if source_commit is None:
        source_commit = run_git(root, "rev-parse", "HEAD")
    receipt_path = root / "promotions" / "receipts" / f"{name}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, object] = {
        "schema_version": schema_version,
        "transaction_id": name,
        "source_commit": source_commit,
        "artifact_ids": ["fixture"],
        "target_ids": [target_id],
        "operations": [
            {
                "artifact_id": "fixture",
                "physical_alias": "physical-0001",
                "logical_target_ids": [target_id],
                "before_digest": before_digest,
                "after_digest": after_digest,
            }
        ],
        "verdict": "PASS",
        "completed_at": completed_at,
    }
    if schema_version == 2:
        receipt["installation_id"] = installation_id
        receipt["bootstrap"] = bootstrap
    receipt_path.write_bytes(canonical_json_bytes(receipt))
    if seal_journal:
        target = target_path.resolve(strict=False)
        backup = backup_root.resolve(strict=True)
        sealed_transaction = backup / name
        (sealed_transaction / "events").mkdir(parents=True)
        plan: dict[str, object] = {
            "schema_version": schema_version,
            "transaction_id": name,
            "source_root": str(root.resolve()),
            "source_commit": source_commit,
            "promotion_map_path": str(root / "promotions/promotion-map.json"),
            "promotion_map_hash": "0" * 64,
            "local_targets_path": str(root / "local-targets.json"),
            "local_targets_hash": "0" * 64,
            "backup_root": str(backup),
            "allowed_physical_roots": [str(backup.parent)],
            "forbidden_physical_roots": [str(backup.parent / "plugins")],
            "receipt_path": str(
                (sealed_receipt_path or receipt_path).resolve(strict=False)
            ),
            "artifact_ids": ["fixture"],
            "target_ids": [target_id],
            "operations": [
                {
                    "artifact_id": "fixture",
                    "artifact_kind": "tree",
                    "source_path": str((root / "skills/demo").resolve()),
                    "source_files": ["SKILL.md"],
                    "target_path": str(target),
                    "logical_target_ids": [target_id],
                    "logical_target_paths": {target_id: str(target)},
                    "before_digest": before_digest,
                    "after_digest": after_digest,
                    "target_role": "skill",
                    "physical_alias": "physical-0001",
                }
            ],
        }
        if schema_version == 2:
            plan["installation_id"] = installation_id
            plan["bootstrap"] = bootstrap
        plan["plan_digest"] = sha256_bytes(canonical_json_bytes(plan))
        write_json(sealed_transaction / "plan.json", plan)
        events: list[dict[str, object]] = []
        _append_test_journal_event(
            sealed_transaction, events, "PENDING",
            {"plan_digest": plan["plan_digest"]},
        )
        if before_digest != after_digest:
            _append_test_journal_event(
                sealed_transaction, events, "STAGE_READY",
                {"physical_alias": "physical-0001", "after_digest": after_digest},
            )
            _append_test_journal_event(
                sealed_transaction, events, "BACKUP_READY",
                {
                    "physical_alias": "physical-0001",
                    "before_digest": before_digest,
                    "existed": before_digest != "absent",
                },
            )
            _append_test_journal_event(
                sealed_transaction, events, "TARGET_PUBLISHED",
                {"physical_alias": "physical-0001", "after_digest": after_digest},
            )
        _append_test_journal_event(
            sealed_transaction, events, "POST_VERIFIED",
            {"operation_count": 1, "logical_target_count": 1},
        )
        _append_test_journal_event(
            sealed_transaction, events, "COMMIT",
            {
                "completed_at": completed_at,
                "receipt_hash": sha256_bytes(receipt_path.read_bytes()),
            },
        )
    run_git(root, "add", receipt_path.relative_to(root).as_posix())
    run_git(root, "commit", "-qm", f"add receipt {name}")
    return receipt_path

def commit_test_adjudications(
    root: Path,
    entries: list[dict[str, str]],
) -> None:
    path = root / "promotions" / "adjudications.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        path,
        {"schema_version": 1, "adjudications": entries},
    )
    run_git(root, "add", path.relative_to(root).as_posix())
    run_git(root, "commit", "-qm", "add promotion adjudications")


def commit_test_adjudication(
    root: Path,
    *,
    target_id: str,
    observed_digest: str,
    reason: str,
) -> None:
    commit_test_adjudications(
        root,
        [
            {
                "artifact_id": "fixture",
                "target_id": target_id,
                "observed_digest": observed_digest,
                "reason": reason,
            }
        ],
    )



def _set_test_target_state(target: Path, value: str) -> str:
    target.mkdir(parents=True, exist_ok=True)
    (target / "state.txt").write_text(value, encoding="utf-8")
    return tree_digest(target)


def test_receipt_history_noop_does_not_explain_later_target_mutation(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = paths["claude"] / "demo"
    root_digest = _set_test_target_state(target, "state-a\n")
    head_digest = _set_test_target_state(target, "state-b\n")
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="e1" * 12, target_id="claude_user_skills",
        before_digest=root_digest, after_digest=head_digest,
        completed_at="2026-07-26T10:00:00+00:00",
    )
    assert _set_test_target_state(target, "state-a\n") == root_digest
    commit_test_adjudication(
        root, target_id="claude_user_skills",
        observed_digest=root_digest,
        reason="Adjudicate the restored root before the no-op promotion.",
    )
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="e2" * 12, target_id="claude_user_skills",
        before_digest=root_digest, after_digest=root_digest,
        completed_at="2026-07-26T11:00:00+00:00",
    )
    assert _set_test_target_state(target, "state-b\n") == head_digest

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-UNEXPLAINED" in codes(report)
    assert not plan_path.exists()


def test_receipt_history_noop_on_unique_head_remains_neutral(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = paths["claude"] / "demo"
    first_digest = _set_test_target_state(target, "state-a\n")
    second_digest = _set_test_target_state(target, "state-b\n")
    head_digest = _set_test_target_state(target, "state-c\n")
    for name, before_digest, after_digest, completed_at in (
        ("e3" * 12, first_digest, second_digest, "2026-07-26T10:00:00+00:00"),
        ("e4" * 12, second_digest, head_digest, "2026-07-26T11:00:00+00:00"),
        ("e5" * 12, head_digest, head_digest, "2026-07-26T12:00:00+00:00"),
    ):
        commit_test_receipt(
            root, backup_root=paths["backups"], target_path=target,
            name=name, target_id="claude_user_skills",
            before_digest=before_digest, after_digest=after_digest,
            completed_at=completed_at,
        )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-HISTORY-AMBIGUOUS" not in codes(report)
    assert "PROMOTION-TARGET-UNEXPLAINED" not in codes(report)
    assert plan_path.is_file()


def test_receipt_history_uses_sealed_time_before_filename_order(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = paths["claude"] / "demo"
    first_digest = _set_test_target_state(target, "first\n")
    head_digest = _set_test_target_state(target, "head\n")
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="f" * 24, target_id="claude_user_skills",
        after_digest=first_digest,
        completed_at="2026-07-25T10:00:00+00:00",
    )
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="a" * 24, target_id="claude_user_skills",
        before_digest=first_digest, after_digest=head_digest,
        completed_at="2026-07-25T11:00:00+00:00",
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-UNEXPLAINED" not in codes(report)
    assert plan_path.is_file()


def test_receipt_history_rejects_restored_superseded_digest(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = paths["claude"] / "demo"
    first_digest = _set_test_target_state(target, "first\n")
    head_digest = _set_test_target_state(target, "head\n")
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="f" * 24, target_id="claude_user_skills",
        after_digest=first_digest,
        completed_at="2026-07-25T10:00:00+00:00",
    )
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="a" * 24, target_id="claude_user_skills",
        before_digest=first_digest, after_digest=head_digest,
        completed_at="2026-07-25T11:00:00+00:00",
    )
    assert _set_test_target_state(target, "first\n") == first_digest

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-UNEXPLAINED" in codes(report)
    assert not plan_path.exists()


def test_receipt_history_allows_distinct_roots_across_transactions(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = paths["claude"] / "demo"
    first_digest = _set_test_target_state(target, "first\n")
    second_digest = _set_test_target_state(target, "second\n")
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="1" * 24, target_id="claude_user_skills",
        after_digest=first_digest,
        completed_at="2026-07-25T10:00:00+00:00",
    )
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="2" * 24, target_id="claude_user_skills",
        after_digest=second_digest,
        completed_at="2026-07-25T11:00:00+00:00",
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-HISTORY-FORK" not in codes(report)
    assert "PROMOTION-TARGET-UNEXPLAINED" not in codes(report)
    assert plan_path.is_file()


def test_receipt_history_return_to_prior_digest_is_not_cycle(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = paths["claude"] / "demo"
    first_digest = _set_test_target_state(target, "first\n")
    second_digest = _set_test_target_state(target, "second\n")
    _set_test_target_state(target, "first\n")
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="3" * 24, target_id="claude_user_skills",
        before_digest=first_digest, after_digest=second_digest,
        completed_at="2026-07-25T10:00:00+00:00",
    )
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="4" * 24, target_id="claude_user_skills",
        before_digest=second_digest, after_digest=first_digest,
        completed_at="2026-07-25T11:00:00+00:00",
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-HISTORY-CYCLE" not in codes(report)
    assert "PROMOTION-TARGET-UNEXPLAINED" not in codes(report)
    assert plan_path.is_file()


def test_later_transaction_can_start_from_distinct_preimage(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = paths["claude"] / "demo"
    first_digest = _set_test_target_state(target, "first\n")
    head_digest = _set_test_target_state(target, "head\n")
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="5" * 24, target_id="claude_user_skills",
        after_digest=first_digest,
        completed_at="2026-07-25T10:00:00+00:00",
    )
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="6" * 24, target_id="claude_user_skills",
        before_digest="e" * 64, after_digest=head_digest,
        completed_at="2026-07-25T11:00:00+00:00",
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-HISTORY-AMBIGUOUS" not in codes(report)
    assert "PROMOTION-TARGET-UNEXPLAINED" not in codes(report)
    assert plan_path.is_file()


@pytest.mark.parametrize(
    ("container", "field"),
    [
        ("root", "transaction_id"),
        ("root", "source_commit"),
        ("root", "artifact_ids"),
        ("root", "target_ids"),
        ("operation", "physical_alias"),
        ("operation", "before_digest"),
    ],
)
def test_receipt_requires_complete_canonical_contract(
    repo_factory,
    tmp_path: Path,
    container: str,
    field: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = seed_installed_demo(root, paths["claude"] / "demo")
    receipt_path = commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="7" * 24, target_id="claude_user_skills",
        after_digest=tree_digest(target),
        completed_at="2026-07-25T10:00:00+00:00",
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if container == "root":
        del receipt[field]
    else:
        del receipt["operations"][0][field]
    write_json(receipt_path, receipt)
    run_git(root, "add", receipt_path.relative_to(root).as_posix())
    run_git(root, "commit", "-qm", f"remove receipt field {field}")

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-INVALID" in codes(report)
    assert not plan_path.exists()


def test_receipt_filename_must_equal_transaction_id(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = seed_installed_demo(root, paths["claude"] / "demo")
    receipt_path = commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="8" * 24, target_id="claude_user_skills",
        after_digest=tree_digest(target),
        completed_at="2026-07-25T10:00:00+00:00",
    )
    renamed = receipt_path.with_name(f'{"9" * 24}.json')
    receipt_path.rename(renamed)
    run_git(root, "add", "-A", "promotions/receipts")
    run_git(root, "commit", "-qm", "mismatch receipt filename")

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-INVALID" in codes(report)
    assert not plan_path.exists()


def test_receipt_without_sealed_journal_fails_closed(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = seed_installed_demo(root, paths["claude"] / "demo")
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="a0" * 12, target_id="claude_user_skills",
        after_digest=tree_digest(target),
        completed_at="2026-07-25T10:00:00+00:00",
        seal_journal=False,
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-UNSEALED" in codes(report)
    assert not plan_path.exists()


def test_receipt_bytes_must_match_commit_receipt_hash(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = seed_installed_demo(root, paths["claude"] / "demo")
    receipt_path = commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="b0" * 12, target_id="claude_user_skills",
        after_digest=tree_digest(target),
        completed_at="2026-07-25T10:00:00+00:00",
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    write_json(receipt_path, receipt)
    run_git(root, "add", receipt_path.relative_to(root).as_posix())
    run_git(root, "commit", "-qm", "reformat sealed receipt bytes")

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-HASH-MISMATCH" in codes(report)
    assert not plan_path.exists()


def test_matching_adjudication_is_the_only_override_for_unsealed_receipt(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = seed_installed_demo(root, paths["claude"] / "demo")
    observed_digest = tree_digest(target)
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="c0" * 12, target_id="claude_user_skills",
        after_digest="f" * 64,
        completed_at="2026-07-25T10:00:00+00:00",
        seal_journal=False,
    )
    commit_test_adjudication(
        root, target_id="claude_user_skills",
        observed_digest=observed_digest,
        reason="Explicitly adjudicate the observed fixture preimage.",
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-UNSEALED" not in codes(report)
    assert plan_path.is_file()


def test_nonmatching_adjudication_does_not_override_unsealed_receipt(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = seed_installed_demo(root, paths["claude"] / "demo")
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="d0" * 12, target_id="claude_user_skills",
        after_digest=tree_digest(target),
        completed_at="2026-07-25T10:00:00+00:00",
        seal_journal=False,
    )
    commit_test_adjudication(
        root, target_id="claude_user_skills",
        observed_digest="e" * 64,
        reason="Deliberately does not match the observed fixture preimage.",
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-UNSEALED" in codes(report)
    assert not plan_path.exists()

def test_target_matching_latest_receipt_passes_preimage_gate(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = seed_installed_demo(root, paths["claude"] / "demo")
    actual_digest = tree_digest(target)
    commit_test_receipt(
        root,
        backup_root=paths["backups"],
        target_path=target,
        name="0" * 24,
        target_id="claude_user_skills",
        after_digest="f" * 64,
        completed_at="2026-07-24T10:00:00+00:00",
    )
    commit_test_receipt(
        root,
        backup_root=paths["backups"],
        target_path=target,
        name="1" * 24,
        target_id="claude_user_skills",
        before_digest="f" * 64,
        after_digest=actual_digest,
        completed_at="2026-07-25T10:00:00+00:00",
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-UNEXPLAINED" not in codes(report)
    assert plan_path.is_file()


def test_target_with_extra_file_fails_preimage_gate_without_writes(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = seed_installed_demo(root, paths["claude"] / "demo")
    expected_digest = tree_digest(target)
    commit_test_receipt(
        root,
        backup_root=paths["backups"],
        target_path=target,
        name="2" * 24,
        target_id="claude_user_skills",
        after_digest=expected_digest,
        completed_at="2026-07-25T10:00:00+00:00",
    )
    (target / "live-only.md").write_text("preserve me\n", encoding="utf-8")
    actual_digest = tree_digest(target)
    backup_entries = list(paths["backups"].rglob("*"))

    report = check_promotion(root, map_path, config_path, plan_path)

    matches = [
        item for item in report["findings"]
        if item["code"] == "PROMOTION-TARGET-UNEXPLAINED"
    ]
    assert len(matches) == 1
    assert matches[0]["message"] == (
        "The promotion target contains bytes no previous receipt explains."
    )
    assert matches[0]["evidence"] == (
        f"target=claude_user_skills expected={expected_digest} "
        f"actual={actual_digest}"
    )
    assert tree_digest(target) == actual_digest
    assert (target / "live-only.md").read_text(encoding="utf-8") == "preserve me\n"
    assert list(paths["backups"].rglob("*")) == backup_entries
    assert not plan_path.exists()


def test_target_with_modified_file_fails_preimage_gate(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = seed_installed_demo(root, paths["claude"] / "demo")
    expected_digest = tree_digest(target)
    commit_test_receipt(
        root,
        backup_root=paths["backups"],
        target_path=target,
        name="3" * 24,
        target_id="claude_user_skills",
        after_digest=expected_digest,
        completed_at="2026-07-25T10:00:00+00:00",
    )
    (target / "SKILL.md").write_text("locally changed\n", encoding="utf-8")

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-UNEXPLAINED" in codes(report)
    assert tree_digest(target) != expected_digest
    assert not plan_path.exists()


def test_nonempty_target_without_receipt_fails_preimage_gate(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = seed_installed_demo(root, paths["claude"] / "demo")
    actual_digest = tree_digest(target)

    report = check_promotion(root, map_path, config_path, plan_path)

    matches = [
        item for item in report["findings"]
        if item["code"] == "PROMOTION-TARGET-UNEXPLAINED"
    ]
    assert len(matches) == 1
    assert matches[0]["evidence"] == (
        f"target=claude_user_skills expected=none actual={actual_digest}"
    )
    assert not plan_path.exists()


def test_absent_target_without_receipt_passes_preimage_gate(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = paths["claude"] / "demo"
    assert not target.exists()

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-UNEXPLAINED" not in codes(report)
    assert not target.exists()
    assert plan_path.is_file()


def test_preimage_gate_checks_every_logical_target_not_just_the_first(
    tmp_path: Path,
) -> None:
    """Fails if a logical id after the first one stops being checked.

    The operations that reach the gate today are pre-dedup and carry a single
    id (measured: 68 of 68). The dedup that merges ids mutates those same dicts
    in place afterwards, so checking only `[0]` is a latent trap: calling this
    function with plan operations would be enough for an adjudication on the
    second id to silently stop counting.
    """
    digest = "a" * 64
    target = tmp_path / "merged-target"
    target.mkdir()
    (target / "payload.txt").write_text("content", encoding="utf-8")
    operation = {
        "artifact_id": "skill/demo",
        "target_path": str(target),
        "logical_target_ids": ["agents_user_skills", "claude_user_skills"],
        "before_digest": digest,
    }
    receipts = {("skill/demo", "agents_user_skills"): digest}

    only_first_explained = promotion._target_preimage_findings(
        [operation], receipts, {},
    )

    assert [item["code"] for item in only_first_explained] == [
        "PROMOTION-TARGET-UNEXPLAINED"
    ]

    second_adjudicated = promotion._target_preimage_findings(
        [operation],
        receipts,
        {("skill/demo", "claude_user_skills"): digest},
    )

    assert second_adjudicated == []


def test_unexplained_preimage_evidence_names_logical_target(
    tmp_path: Path,
) -> None:
    digest = "a" * 64
    other = "b" * 64
    target = tmp_path / "merged-target"
    target.mkdir()
    (target / "payload.txt").write_text("content", encoding="utf-8")
    operation = {
        "artifact_id": "skill/demo",
        "target_path": str(target),
        "logical_target_ids": ["agents_user_skills", "claude_user_skills"],
        "before_digest": digest,
    }

    findings = promotion._target_preimage_findings(
        [operation],
        {("skill/demo", "agents_user_skills"): other},
        {},
    )

    unexplained = [
        item for item in findings
        if item["code"] == "PROMOTION-TARGET-UNEXPLAINED"
    ]
    assert [item["path"] for item in unexplained] == [
        "skill/demo",
        "skill/demo",
    ]
    evidences = [item["evidence"] for item in unexplained]
    assert (
        f"target=agents_user_skills expected={other} actual={digest}"
        in evidences
    )
    assert (
        f"target=claude_user_skills expected=none actual={digest}"
        in evidences
    )


def test_matching_adjudication_allows_observed_target_digest(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = seed_installed_demo(root, paths["claude"] / "demo")
    observed_digest = tree_digest(target)
    commit_test_adjudication(
        root,
        target_id="claude_user_skills",
        observed_digest=observed_digest,
        reason="Preserve content reviewed outside prior receipt history.",
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-UNEXPLAINED" not in codes(report)
    assert plan_path.is_file()


def test_adjudication_expires_after_target_digest_changes(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = seed_installed_demo(root, paths["claude"] / "demo")
    observed_digest = tree_digest(target)
    commit_test_adjudication(
        root,
        target_id="claude_user_skills",
        observed_digest=observed_digest,
        reason="Preserve content reviewed outside prior receipt history.",
    )
    first = check_promotion(root, map_path, config_path, plan_path)
    assert "PROMOTION-TARGET-UNEXPLAINED" not in codes(first)
    (target / "changed.txt").write_text("changed again\n", encoding="utf-8")

    second = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-UNEXPLAINED" in codes(second)
    assert not plan_path.exists()


def test_adjudicated_preimage_advances_to_post_for_next_pass(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = paths["claude"] / "demo"
    root_digest = _set_test_target_state(target, "state-a\n")
    head_digest = _set_test_target_state(target, "state-b\n")
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="e6" * 12, target_id="claude_user_skills",
        before_digest=root_digest, after_digest=head_digest,
        completed_at="2026-07-26T10:00:00+00:00",
    )
    foreign_digest = _set_test_target_state(target, "state-x\n")
    reason = "Adjudicate the reconciled state outside receipt history."
    commit_test_adjudication(
        root, target_id="claude_user_skills",
        observed_digest=foreign_digest, reason=reason,
    )
    source_digest = tree_digest(root / "skills/demo")
    assert foreign_digest != source_digest
    checked = check_promotion(root, map_path, config_path, plan_path)
    assert checked["verdict"] in {"PASS", "WARN"}

    applied = apply_promotion(plan_path)

    assert applied["verdict"] == "PASS"
    assert tree_digest(target) == source_digest
    adjudication_path = root / "promotions/adjudications.json"
    adjudication_value = json.loads(adjudication_path.read_text(encoding="utf-8"))
    assert set(adjudication_value) == {"schema_version", "adjudications"}
    assert len(adjudication_value["adjudications"]) == 1
    entry = adjudication_value["adjudications"][0]
    assert set(entry) == {"artifact_id", "target_id", "observed_digest", "reason"}
    assert entry["observed_digest"] == source_digest
    assert entry["reason"] == reason
    receipt_path = Path(str(applied["artifacts"]["receipt_path"]))
    run_git(
        root, "add", "promotions/adjudications.json",
        receipt_path.relative_to(root).as_posix(),
    )
    run_git(root, "commit", "-qm", "record automatic adjudication advance")

    second = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-HISTORY-AMBIGUOUS" not in codes(second)
    assert "PROMOTION-TARGET-UNEXPLAINED" not in codes(second)
    assert second["verdict"] in {"PASS", "WARN"}
    assert plan_path.is_file()


def test_adjudication_with_empty_reason_is_schema_error(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = seed_installed_demo(root, paths["claude"] / "demo")
    commit_test_adjudication(
        root,
        target_id="claude_user_skills",
        observed_digest=tree_digest(target),
        reason="",
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-ADJUDICATION-INVALID" in codes(report)
    assert not plan_path.exists()


def commit_demo_payload(root: Path, relative: str, content: str) -> Path:
    path = root / "skills" / "demo" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    run_git(root, "add", path.relative_to(root).as_posix())
    run_git(root, "commit", "-qm", f"add executable fixture {relative}")
    return path


def configure_path_aliases(
    config_path: Path,
    aliases: dict[str, dict[str, str]],
) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["path_aliases"] = aliases
    write_json(config_path, config)


def configure_complete_path_aliases(
    config_path: Path,
    tmp_path: Path,
    *,
    fragment_value: str = "fixture-user",
) -> Path:
    dayz_projects = tmp_path / "DayZ Projects"
    dayz_projects.mkdir(exist_ok=True)
    configure_path_aliases(
        config_path,
        {
            "<dayz-projects>": {
                "kind": "path",
                "value": str(dayz_projects),
            },
            "<you>": {
                "kind": "fragment",
                "value": fragment_value,
            },
        },
    )
    return dayz_projects


def test_ps1_pack_alias_missing_from_map_fails_config_without_writes(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    commit_demo_payload(
        root,
        "templates/demo.ps1",
        'param()\nWrite-Output "demo"\n$Root = "<dayz-projects>\\LF"\n',
    )
    target = paths["claude"] / "demo"
    backup_entries = list(paths["backups"].rglob("*"))

    report = check_promotion(root, map_path, config_path, plan_path)

    matches = [
        item for item in report["findings"]
        if item["code"] == "PROMOTION-CONFIG-INVALID"
    ]
    assert len(matches) == 1
    assert matches[0]["path"] == "local-targets.json"
    assert matches[0]["line"] == 1
    assert matches[0]["evidence"] == (
        "skills/demo/templates/demo.ps1:3 <dayz-projects>"
    )
    assert not target.exists()
    assert list(paths["backups"].rglob("*")) == backup_entries
    assert not plan_path.exists()


def test_ps1_usage_text_with_mod_placeholder_passes(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path,
    )
    commit_demo_payload(
        root,
        "templates/demo.ps1",
        'Write-Output "Usage: demo <mod>"\n',
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-PLACEHOLDER-IN-EXECUTABLE" not in codes(report)
    assert plan_path.is_file()


def test_markdown_pack_alias_is_not_scanned_by_placeholder_gate(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path,
    )
    commit_demo_payload(
        root,
        "references/policy.md",
        "Use <dayz-projects> as the distribution alias.\n",
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-PLACEHOLDER-IN-EXECUTABLE" not in codes(report)
    assert plan_path.is_file()


def test_python_pack_alias_missing_from_map_fails_config_case_insensitively(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path,
    )
    commit_demo_payload(
        root,
        "scripts/demo.py",
        'print("demo")\nVAULT_ROOT = "<VaUlT>"\n',
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    matches = [
        item for item in report["findings"]
        if item["code"] == "PROMOTION-CONFIG-INVALID"
    ]
    assert len(matches) == 1
    assert matches[0]["line"] == 1
    assert matches[0]["evidence"] == "skills/demo/scripts/demo.py:2 <VaUlT>"
    assert not plan_path.exists()



def test_path_alias_nested_in_absolute_path_fails_without_writes(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    configure_complete_path_aliases(config_path, tmp_path)
    commit_demo_payload(
        root,
        "templates/demo.ps1",
        '$Root = "C:\\wrapper\\<dayz-projects>\\tool"\n',
    )
    backup_entries = list(paths["backups"].rglob("*"))

    report = check_promotion(root, map_path, config_path, plan_path)

    matches = [
        item for item in report["findings"]
        if item["code"] == "PROMOTION-CONFIG-INVALID"
    ]
    assert len(matches) == 1
    assert matches[0]["evidence"] == (
        "skills/demo/templates/demo.ps1:1 <dayz-projects>"
    )
    assert not plan_path.exists()
    assert not (paths["claude"] / "demo").exists()
    assert list(paths["backups"].rglob("*")) == backup_entries


def test_real_promotion_map_placeholder_scan_excludes_detector_corpus_and_keeps_real_payloads() -> None:
    # Scans every route of the original pack tree, which is not in this repository.
    root = require_tree_root("promotions/promotion-map.json", "knowledge", "skills")
    promotion_map = json.loads(
        (root / "promotions/promotion-map.json").read_text(encoding="utf-8")
    )
    routes = []
    for route_value in promotion_map["artifacts"]:
        route = dict(route_value)
        route["_resolved_source"] = str(
            (root / str(route["repo_path"])).resolve(strict=True)
        )
        route["_source_files"] = promotion._tracked_projection(
            root,
            str(route["repo_path"]),
            route["artifact_kind"],
        )
        routes.append(route)

    unmapped = promotion._executable_placeholder_findings(routes, {})
    observed_paths = sorted(
        str(item["evidence"]).split(":", 2)[0]
        for item in unmapped
        if item["code"] == "PROMOTION-CONFIG-INVALID"
    )
    # Census of every executable payload carrying a token from the closed alias
    # list with no localisation configured. Pinned so that adding one is a
    # deliberate act: each entry is a file that will not run until an operator
    # points it at their own machine, and silently growing this list is how a
    # pack ends up shipping scripts nobody can execute. It is only ever as good
    # as PROMOTION_PATH_PLACEHOLDERS: a hardcoded path written with a token
    # outside that tuple is invisible here AND unconfigurable, so an entry
    # leaving is a fact about the scanner until someone runs the file.
    assert observed_paths == [
        "skills/dayz-animation-pipeline/scripts/extract_empties.py",
        "skills/dayz-animation-pipeline/scripts/extract_weapon.py",
        "skills/dayz-animation-pipeline/scripts/fbx_extract.py",
        "skills/dayz-animation-pipeline/scripts/seanim_export.py",
        "skills/dayz-clothing/references/alignment_viewer_build.py",
        "skills/dayz-clothing/references/alignment_viewer_extract.py",
        "skills/dayz-clothing/references/alignment_viewer_extract.py",
        "skills/dayz-clothing/references/alignment_viewer_extract.py",
        "skills/dayz-clothing/references/alignment_viewer_extract.py",
        "skills/dayz-clothing/references/apply_alignment_json.py",
        "skills/dayz-clothing/references/apply_alignment_json.py",
        "skills/dayz-clothing/references/export_clothing_fbx.py",
        "skills/dayz-clothing/references/export_clothing_fbx.py",
        "skills/dayz-mcp-verify/references/drive_ladder.py",
        "skills/dayz-preflight/preflight.py",
        "skills/dayz-test-ingame/templates/dayz-test.ps1",
        "skills/dayz-test-ingame/templates/dayz-test.ps1",
        "skills/dayz-test-ingame/templates/dayz-test.ps1",
        "skills/dayz-vehicles/references/check_odol_bone_refs.py",
        "skills/dayz-vehicles/references/check_odol_bone_refs.py",
        "skills/dayz-vehicles/references/check_odol_bone_refs.py",
        "skills/dayz-vehicles/references/gate_odol_sections.py",
        "skills/dayz-vehicles/references/gate_odol_sections.py",
        "tools/py3d/rollout/fix-junctions.ps1",
        "tools/py3d/rollout/fix-junctions.ps1",
        "tools/py3d/rollout/fix-junctions.ps1",
    ]

    findings = promotion._executable_placeholder_findings(
        routes,
        {
            "<dayz-projects>": {"kind": "path", "value": str(root)},
            "<you>": {"kind": "fragment", "value": "fixture-user"},
            "<claude-appdata>": {
                "kind": "path",
                "value": str(root / "claude-appdata"),
            },
            "<tmp>": {"kind": "path", "value": str(root / "tmp")},
        },
    )

    assert findings == []

    # fb-20261018-002910-6bdf: localization writes the configured path as
    # is, so `<dayz-projects>` in a plain Python string became
    # "C:\Users\...", which Python reads as a \U escape, and the installed
    # preflight.py stopped parsing. Every Python payload must still compile
    # with Windows paths in place of its placeholders.
    windows_aliases = {
        "<dayz-projects>": {
            "kind": "path",
            "value": "C:\\Users\\fixture\\DayZ Projects",
        },
        "<you>": {"kind": "fragment", "value": "fixture-user"},
        "<claude-appdata>": {
            "kind": "path",
            "value": "C:\\Users\\fixture\\AppData\\Roaming\\Claude",
        },
        "<tmp>": {
            "kind": "path",
            "value": "C:\\Users\\fixture\\AppData\\Local\\Temp",
        },
    }
    for repo_path in sorted(set(observed_paths)):
        if repo_path.endswith(".py"):
            localized = promotion._localized_payload_bytes(
                root / repo_path, windows_aliases, root
            )
            compile(localized, repo_path, "exec")


def test_legacy_v1_without_path_aliases_passes_without_placeholders(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path,
    )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.pop("path_aliases")
    write_json(config_path, config)

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-CONFIG-INVALID" not in codes(report)
    assert plan_path.is_file()


def test_legacy_v1_without_path_aliases_still_scans_executable_payloads(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    commit_demo_payload(
        root,
        "templates/demo.ps1",
        'param()\n$Root = "<dayz-projects>\\LF"\n',
    )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.pop("path_aliases")
    write_json(config_path, config)
    backup_entries = list(paths["backups"].rglob("*"))

    report = check_promotion(root, map_path, config_path, plan_path)

    matches = [
        item for item in report["findings"]
        if item["code"] == "PROMOTION-CONFIG-INVALID"
    ]
    assert len(matches) == 1
    assert matches[0]["evidence"] == (
        "skills/demo/templates/demo.ps1:2 <dayz-projects>"
    )
    assert not plan_path.exists()
    assert not (paths["claude"] / "demo").exists()
    assert list(paths["backups"].rglob("*")) == backup_entries


def test_optional_path_aliases_does_not_allow_unknown_top_level_fields(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path,
    )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.pop("path_aliases")
    config["unexpected"] = {}
    write_json(config_path, config)

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-CONFIG-INVALID" in codes(report)
    assert not plan_path.exists()


@pytest.mark.parametrize(
    "case",
    [
        "not-object",
        "unknown-alias",
        "missing-value",
        "empty-value",
        "invalid-kind",
        "relative-path",
        "missing-path",
        "fragment-separator",
        "fragment-drive",
        "fragment-dotdot",
    ],
)
def test_invalid_path_alias_config_fails_before_plan_or_writes(
    repo_factory,
    tmp_path: Path,
    case: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    valid_path = tmp_path / "valid-path"
    valid_path.mkdir()
    invalid: object
    if case == "not-object":
        invalid = []
    elif case == "unknown-alias":
        invalid = {"<unknown>": {"kind": "path", "value": str(valid_path)}}
    elif case == "missing-value":
        invalid = {"<you>": {"kind": "fragment"}}
    elif case == "empty-value":
        invalid = {"<you>": {"kind": "fragment", "value": ""}}
    elif case == "invalid-kind":
        invalid = {"<you>": {"kind": "directory", "value": "fixture"}}
    elif case == "relative-path":
        invalid = {"<dayz-projects>": {"kind": "path", "value": "relative"}}
    elif case == "missing-path":
        invalid = {
            "<dayz-projects>": {
                "kind": "path",
                "value": str(tmp_path / "does-not-exist"),
            }
        }
    elif case == "fragment-separator":
        invalid = {"<you>": {"kind": "fragment", "value": "fixture/user"}}
    elif case == "fragment-drive":
        invalid = {"<you>": {"kind": "fragment", "value": "C:fixture"}}
    else:
        invalid = {"<you>": {"kind": "fragment", "value": "fixture..user"}}
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["path_aliases"] = invalid
    write_json(config_path, config)
    backup_entries = list(paths["backups"].rglob("*"))

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-CONFIG-INVALID" in codes(report)
    assert not plan_path.exists()
    assert list(paths["backups"].rglob("*")) == backup_entries
    assert not (paths["claude"] / "demo").exists()


def test_localized_ps1_is_written_and_receipt_hashes_localized_content(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    dayz_projects = configure_complete_path_aliases(config_path, tmp_path)
    commit_demo_payload(
        root,
        "templates/demo.ps1",
        '$Root = "<dayz-projects>\\LF"\n',
    )

    checked = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-CONFIG-INVALID" not in codes(checked)
    assert "PROMOTION-PLACEHOLDER-IN-EXECUTABLE" not in codes(checked)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    target = paths["claude"] / "demo"
    operation = next(
        item
        for item in plan["operations"]
        if Path(str(item["target_path"])) == target.resolve()
    )

    applied = apply_promotion(plan_path)

    expected = f'$Root = "{dayz_projects}\\LF"\n'
    installed = (target / "templates/demo.ps1").read_text(encoding="utf-8")
    assert applied["verdict"] == "PASS"
    assert installed == expected
    assert all(
        token not in installed.casefold()
        for token in promotion.PROMOTION_PATH_PLACEHOLDERS
    )
    receipt = json.loads(
        Path(str(applied["artifacts"]["receipt_path"])).read_text(
            encoding="utf-8"
        )
    )
    receipt_operation = next(
        item
        for item in receipt["operations"]
        if item["physical_alias"] == operation["physical_alias"]
    )
    assert tree_digest(target) == operation["after_digest"]
    assert receipt_operation["after_digest"] == operation["after_digest"]


def test_repeated_localized_promotion_is_idempotent_and_preimage_passes(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    dayz_projects = configure_complete_path_aliases(config_path, tmp_path)
    commit_demo_payload(
        root,
        "templates/demo.ps1",
        '$Root = "<dayz-projects>\\LF"\n',
    )
    first_check = check_promotion(root, map_path, config_path, plan_path)
    assert first_check["verdict"] == "WARN"
    first_apply = apply_promotion(plan_path)
    assert first_apply["verdict"] == "PASS"
    target = paths["claude"] / "demo"
    first_digest = tree_digest(target)
    exclude = root / ".git/info/exclude"
    exclude.write_text(
        exclude.read_text(encoding="utf-8")
        + "\npromotions/receipts/*.json\n",
        encoding="utf-8",
        newline="\n",
    )
    assert run_git(root, "status", "--porcelain") == ""

    second_check = check_promotion(root, map_path, config_path, plan_path)

    assert second_check["verdict"] == "PASS"
    assert "PROMOTION-TARGET-UNEXPLAINED" not in codes(second_check)
    second_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    operation = next(
        item
        for item in second_plan["operations"]
        if Path(str(item["target_path"])) == target.resolve()
    )
    assert operation["before_digest"] == operation["after_digest"]
    second_apply = apply_promotion(plan_path)
    installed = (target / "templates/demo.ps1").read_text(encoding="utf-8")
    assert second_apply["verdict"] == "PASS"
    assert tree_digest(target) == first_digest
    assert installed == f'$Root = "{dayz_projects}\\LF"\n'


def test_markdown_path_alias_is_promoted_literal_without_localization(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    configure_complete_path_aliases(config_path, tmp_path)
    literal = "Use <dayz-projects> as the distribution alias.\n"
    commit_demo_payload(root, "references/policy.md", literal)

    checked = check_promotion(root, map_path, config_path, plan_path)
    assert "PROMOTION-CONFIG-INVALID" not in codes(checked)
    applied = apply_promotion(plan_path)

    assert applied["verdict"] == "PASS"
    assert (
        paths["claude"] / "demo/references/policy.md"
    ).read_text(encoding="utf-8") == literal


def test_alias_value_is_single_pass_literal_and_residual_blocks_commit(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    dayz_projects = configure_complete_path_aliases(
        config_path,
        tmp_path,
        fragment_value="<dayz-projects>",
    )
    commit_demo_payload(
        root,
        "templates/demo.ps1",
        'Write-Output "<you>"\n',
    )
    checked = check_promotion(root, map_path, config_path, plan_path)
    assert checked["verdict"] == "WARN"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    source_files = promotion._tracked_projection(root, "skills/demo", "tree")
    projected = tmp_path / "single-pass-projection"
    promotion._copy_artifact(
        root / "skills/demo",
        projected,
        "tree",
        source_files,
        path_aliases={
            "<dayz-projects>": {
                "kind": "path",
                "value": str(dayz_projects),
            },
            "<you>": {
                "kind": "fragment",
                "value": "<dayz-projects>",
            },
        },
        source_root=root,
    )
    projected_text = (
        projected / "templates/demo.ps1"
    ).read_text(encoding="utf-8")
    assert projected_text == 'Write-Output "<dayz-projects>"\n'
    assert str(dayz_projects) not in projected_text

    applied = apply_promotion(plan_path)

    transaction = transaction_root(plan)
    events = assert_valid_event_chain(transaction)
    assert applied["verdict"] == "FAIL"
    assert "PROMOTION-APPLY-FAILED" in codes(applied)
    failure = next(
        item for item in applied["findings"]
        if item["code"] == "PROMOTION-APPLY-FAILED"
    )
    evidence = str(failure["evidence"])
    assert evidence.startswith("PROMOTION-PLACEHOLDER-IN-EXECUTABLE ")
    assert ":staging-readback " in evidence
    assert (
        "skills/demo/templates/demo.ps1:1 <dayz-projects>"
        in evidence
    )
    assert events[-1]["event_type"] == "ABORT"
    assert all(event["event_type"] != "COMMIT" for event in events)
    assert not Path(str(plan["receipt_path"])).exists()
    assert not (paths["claude"] / "demo").exists()


def test_promotion_check_routes_repo_vault_and_both_skill_roots(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert report["verdict"] == "WARN"
    assert codes(report) == ["PROMOTION-DRIFT"]
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["source_commit"] == run_git(root, "rev-parse", "HEAD")
    assert set(plan["artifact_ids"]) == {"fixture", "fixture-root"}
    assert set(plan["target_ids"]) == {
        "claude_user_skills",
        "agents_user_skills",
        "obsidian_snapshots",
    }
    assert len(plan["operations"]) == 4
    assert plan["plan_digest"]
    assert plan["promotion_map_hash"]
    assert plan["local_targets_hash"]


def test_alias_targets_dedupe_physical_write_but_keep_logical_readbacks(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path, alias_skills=True
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert report["verdict"] == "WARN"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    skill_operation = next(
        operation
        for operation in plan["operations"]
        if "claude_user_skills" in operation["logical_target_ids"]
    )
    assert set(skill_operation["logical_target_ids"]) == set(REQUIRED_SKILL_TARGETS)
    assert len(plan["operations"]) == 3


def test_unrouted_source_artifact_fails_closed(repo_factory, tmp_path: Path) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    write_json(map_path, {"schema_version": 1, "artifacts": []})

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-UNROUTED" in codes(report)
    assert not plan_path.exists()


def test_routing_id_must_cover_each_source_map_output(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    source_map_path = root / "sources/source-map.json"
    value = json.loads(source_map_path.read_text(encoding="utf-8"))
    readme = next(
        item for item in value["artifacts"] if item["output_path"] == "README.md"
    )
    readme["routing_artifact_id"] = "fixture"
    write_json(source_map_path, value)
    run_git(root, "add", "sources/source-map.json")
    run_git(root, "commit", "-qm", "misroute fixture artifact")

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-UNROUTED" in codes(report)
    assert not plan_path.exists()


def test_domain_invariant_requires_both_skill_targets(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    value = json.loads(map_path.read_text(encoding="utf-8"))
    value["artifacts"][0]["skill_target_ids"] = ["claude_user_skills"]
    write_json(map_path, value)

    report = check_promotion(root, map_path, config_path, plan_path)

    assert codes(report) == ["PROMOTION-ROUTING-INVALID"]
    assert not plan_path.exists()


def test_not_applicable_requires_reason(repo_factory, tmp_path: Path) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    value = json.loads(map_path.read_text(encoding="utf-8"))
    value["artifacts"][0]["applicability"] = "governance"
    value["artifacts"][0]["skill_target_ids"] = []
    write_json(map_path, value)

    report = check_promotion(root, map_path, config_path, plan_path)

    assert codes(report) == ["PROMOTION-NOT-APPLICABLE-INVALID"]


def test_readonly_or_missing_target_fails_before_staging(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path, writable=False
    )

    readonly = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-READONLY" in codes(readonly)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    for target in config["targets"].values():
        target["writable"] = True
    config["targets"]["agents_user_skills"]["path"] = str(
        paths["targets"] / "missing"
    )
    write_json(config_path, config)

    missing = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-MISSING" in codes(missing)


def test_escape_and_forbidden_target_fail_closed(repo_factory, tmp_path: Path) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    outside = tmp_path / "outside"
    outside.mkdir()
    config["targets"]["agents_user_skills"]["path"] = str(outside)
    write_json(config_path, config)

    escaped = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-ESCAPE" in codes(escaped)
    plugin = paths["targets"] / "plugins"
    plugin.mkdir()
    config["targets"]["agents_user_skills"]["path"] = str(plugin)
    write_json(config_path, config)

    forbidden = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-FORBIDDEN" in codes(forbidden)


def test_compare_and_swap_rejects_target_change_without_writes(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    changed = paths["claude"] / "demo"
    changed.mkdir()
    (changed / "foreign.txt").write_text("changed\n", encoding="utf-8")
    before = tree_digest(changed)

    report = apply_promotion(plan_path)

    assert codes(report) == ["PROMOTION-TARGET-CHANGED"]
    assert tree_digest(changed) == before
    assert not (paths["agents"] / "demo").exists()


@pytest.mark.parametrize(
    ("location", "expected_code"),
    [
        ("outside", "PROMOTION-BACKUP-ESCAPE"),
        ("forbidden", "PROMOTION-BACKUP-FORBIDDEN"),
    ],
)
def test_backup_root_must_be_allowlisted_and_not_forbidden(
    repo_factory,
    tmp_path: Path,
    location: str,
    expected_code: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    backup_root = (
        tmp_path / "outside-backups"
        if location == "outside"
        else paths["targets"] / "plugins" / "backups"
    )
    backup_root.mkdir(parents=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["backup_root"] = str(backup_root)
    write_json(config_path, config)

    report = check_promotion(root, map_path, config_path, plan_path)

    assert expected_code in codes(report)
    assert not plan_path.exists()


def test_apply_rejects_tampered_plan_before_any_write(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["operations"][0]["after_digest"] = "0" * 64
    write_json(plan_path, plan)

    report = apply_promotion(plan_path)

    assert codes(report) == ["PROMOTION-PLAN-TAMPERED"]
    assert not (paths["claude"] / "demo").exists()
    assert not (paths["agents"] / "demo").exists()


@pytest.mark.parametrize("contract", ["promotion_map", "local_targets"])
def test_apply_rejects_contract_change_after_check(
    repo_factory,
    tmp_path: Path,
    contract: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    changed_path = map_path if contract == "promotion_map" else config_path
    changed_path.write_text(
        changed_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
        newline="\n",
    )

    report = apply_promotion(plan_path)

    assert codes(report) == ["PROMOTION-CONTRACT-CHANGED"]
    assert not (paths["claude"] / "demo").exists()


def test_tree_promotion_copies_only_tracked_projection(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    ignored = root / "skills/demo/local-secret.txt"
    ignored.write_text("must not leave source tree\n", encoding="utf-8")
    (root / ".git/info/exclude").write_text(
        "skills/demo/local-secret.txt\n",
        encoding="utf-8",
        newline="\n",
    )

    check_report = check_promotion(root, map_path, config_path, plan_path)
    assert check_report["verdict"] == "WARN"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    skill_operation = next(
        item
        for item in plan["operations"]
        if item["artifact_id"] == "fixture" and item["target_role"] == "skill"
    )
    assert skill_operation["source_files"] == ["SKILL.md"]

    report = apply_promotion(plan_path)

    assert report["verdict"] == "PASS"
    assert not (paths["claude"] / "demo/local-secret.txt").exists()
    assert not (
        paths["vault"]
        / "fixture"
        / run_git(root, "rev-parse", "HEAD")
        / "local-secret.txt"
    ).exists()


def test_tree_promotion_uses_consistent_order_for_mixed_case_projection(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    reference = root / "skills/demo/references/detail.md"
    reference.parent.mkdir()
    reference.write_text("reference\n", encoding="utf-8", newline="\n")
    run_git(root, "add", "skills/demo/references/detail.md")
    run_git(root, "commit", "-qm", "add mixed-case projection fixture")

    check_report = check_promotion(root, map_path, config_path, plan_path)
    assert check_report["verdict"] == "WARN"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    skill_operation = next(
        item
        for item in plan["operations"]
        if item["artifact_id"] == "fixture" and item["target_role"] == "skill"
    )
    assert skill_operation["source_files"] == [
        "SKILL.md",
        "references/detail.md",
    ]
    assert tree_digest(root / "skills/demo") == skill_operation["after_digest"]

    report = apply_promotion(plan_path)

    assert report["verdict"] == "PASS"
    assert tree_digest(paths["claude"] / "demo") == skill_operation["after_digest"]


def test_file_promotion_hashes_content_independently_of_snapshot_name(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    source_map_path = root / "sources/source-map.json"
    source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
    readme_artifact = next(
        item
        for item in source_map["artifacts"]
        if item["output_path"] == "README.md"
    )
    readme_artifact["routing_artifact_id"] = "fixture-file"
    write_json(source_map_path, source_map)
    run_git(root, "add", "sources/source-map.json")
    run_git(root, "commit", "-qm", "route file fixture")
    promotion_map = json.loads(map_path.read_text(encoding="utf-8"))
    promotion_map["artifacts"].append(
        {
            "artifact_id": "fixture-file",
            "repo_path": "README.md",
            "artifact_kind": "file",
            "applicability": "governance",
            "vault_targets": ["obsidian_snapshots"],
            "skill_target_ids": [],
            "not_applicable_reason": (
                "Fixture file is durable vault context, not a skill."
            ),
        }
    )
    write_json(map_path, promotion_map)
    check = check_promotion(root, map_path, config_path, plan_path)
    assert check["verdict"] == "WARN"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    file_operation = next(
        operation
        for operation in plan["operations"]
        if operation["artifact_id"] == "fixture-file"
    )

    report = apply_promotion(plan_path)

    target = Path(str(file_operation["target_path"]))
    assert report["verdict"] == "PASS"
    assert target.read_bytes() == (root / "README.md").read_bytes()
    assert target == (
        paths["vault"]
        / "fixture-file"
        / run_git(root, "rev-parse", "HEAD")
    )


@pytest.mark.parametrize("residue_kind", ["stage", "old"])
def test_apply_rejects_preexisting_residue_without_deleting_it(
    repo_factory,
    tmp_path: Path,
    residue_kind: str,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    operation = plan["operations"][0]
    target = Path(operation["target_path"])
    residue = target.parent / (
        f".{target.name}.packctl-{residue_kind}-{plan['transaction_id']}"
    )
    residue.mkdir(parents=True)
    sentinel = residue / "foreign.txt"
    sentinel.write_text("do not delete\n", encoding="utf-8")

    report = apply_promotion(plan_path)

    assert "PROMOTION-APPLY-FAILED" in codes(report)
    assert sentinel.read_text(encoding="utf-8") == "do not delete\n"


def test_partial_stage_from_failed_copy_is_removed(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    created_stage: Path | None = None

    def fail_after_partial_copy(
        source,
        destination,
        kind,
        source_files=None,
        **_kwargs,
    ):
        nonlocal created_stage
        created_stage = Path(destination)
        created_stage.mkdir(parents=True)
        (created_stage / "partial.txt").write_text(
            "partial\n", encoding="utf-8"
        )
        raise OSError("copy fault")

    monkeypatch.setattr("packctl.promotion._copy_artifact", fail_after_partial_copy)

    report = apply_promotion(plan_path)

    assert "PROMOTION-APPLY-FAILED" in codes(report)
    assert created_stage is not None
    assert not created_stage.exists()


def test_stale_lock_file_does_not_block_apply(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    lock = promotion._lock_path_for_root(paths["targets"])
    lock.write_text("stale metadata\n", encoding="utf-8")

    report = apply_promotion(plan_path)

    assert report["verdict"] == "PASS"
    assert lock.exists()
    assert (paths["claude"] / "demo/SKILL.md").is_file()


def test_root_lock_sidecar_does_not_modify_an_exact_target(
    tmp_path: Path,
) -> None:
    target = tmp_path / "exact-target"
    target.mkdir()
    (target / "content.txt").write_text("stable\n", encoding="utf-8")
    before = tree_digest(target)

    with promotion._RootLocks([target]):
        assert tree_digest(target) == before
        assert not (target / ".packctl.lock").exists()
        assert (tmp_path / ".exact-target.packctl.lock").is_file()

    assert tree_digest(target) == before


@pytest.mark.skipif(os.name != "nt", reason="Windows rename retry contract")
def test_windows_durable_rename_retries_transient_delete_denial(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "payload.txt").write_text("payload\n", encoding="utf-8")
    destination = tmp_path / "destination"
    outcomes = [
        (False, 5, "Access is denied."),
        (False, 32, "The process cannot access the file."),
        (True, 0, ""),
    ]
    calls: list[tuple[Path, Path, int]] = []
    delays: list[float] = []

    def fake_move(
        candidate_source: Path,
        candidate_destination: Path,
        flags: int,
    ) -> tuple[bool, int, str]:
        calls.append((candidate_source, candidate_destination, flags))
        outcome = outcomes.pop(0)
        if outcome[0]:
            candidate_source.rename(candidate_destination)
        return outcome

    monkeypatch.setattr(
        common,
        "_windows_move_file_ex",
        fake_move,
    )
    monkeypatch.setattr(
        common,
        "_sleep_before_windows_rename_retry",
        delays.append,
    )

    common.durable_rename(source, destination, replace=False)

    assert destination.joinpath("payload.txt").read_text(encoding="utf-8") == (
        "payload\n"
    )
    assert [call[2] for call in calls] == [0x00000008] * 3
    assert delays == [0.05, 0.1]


@pytest.mark.skipif(os.name != "nt", reason="Windows rename retry contract")
def test_windows_durable_rename_does_not_retry_ambiguous_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "payload.txt").write_text("payload\n", encoding="utf-8")
    destination = tmp_path / "destination"
    calls = 0
    delays: list[float] = []

    def ambiguous_move(
        candidate_source: Path,
        candidate_destination: Path,
        flags: int,
    ) -> tuple[bool, int, str]:
        nonlocal calls
        calls += 1
        candidate_source.rename(candidate_destination)
        return False, 5, "Access is denied."

    monkeypatch.setattr(
        common,
        "_windows_move_file_ex",
        ambiguous_move,
    )
    monkeypatch.setattr(
        common,
        "_sleep_before_windows_rename_retry",
        delays.append,
    )

    with pytest.raises(PermissionError) as captured:
        common.durable_rename(source, destination, replace=False)

    assert captured.value.winerror == 5
    assert calls == 1
    assert delays == []
    assert destination.joinpath("payload.txt").is_file()


def test_live_os_lock_blocks_apply_with_exit_2(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    lock = promotion._lock_path_for_root(paths["targets"])
    holder = start_lock_holder(lock)
    try:
        report = apply_promotion(plan_path)
    finally:
        assert holder.stdin is not None
        holder.stdin.write("\n")
        holder.stdin.flush()
        holder.wait(timeout=10)

    assert "PROMOTION-LOCK-ACTIVE" in codes(report)
    assert report["artifacts"]["requires_intervention"] is True
    assert report["artifacts"]["exit_code"] == 2
    assert not (paths["claude"] / "demo").exists()


@pytest.mark.parametrize(
    "state",
    ["starting", "replacing", "readback-complete", "rollback-failed", "complete"],
)
def test_unverifiable_journal_blocks_apply_with_exit_2(
    repo_factory,
    tmp_path: Path,
    state: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    prior_id = "a" * 24
    prior_root = paths["backups"] / prior_id
    prior_root.mkdir()
    write_json(
        prior_root / "journal.json",
        {
            "schema_version": 1,
            "transaction_id": prior_id,
            "source_commit": "0" * 40,
            "state": state,
            "touched_aliases": [],
            "rollback_errors": (
                ["physical-0001:OSError"]
                if state == "rollback-failed"
                else []
            ),
        },
    )

    report = apply_promotion(plan_path)

    assert "PROMOTION-RECOVERY-REQUIRED" in codes(report)
    assert report["artifacts"]["requires_intervention"] is True
    assert report["artifacts"]["exit_code"] == 2
    assert not (paths["claude"] / "demo").exists()


def test_legacy_mutable_journal_does_not_count_as_terminal_evidence(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    prior_id = "b" * 24
    prior_root = paths["backups"] / prior_id
    prior_root.mkdir()
    write_json(
        prior_root / "journal.json",
        {
            "schema_version": 1,
            "transaction_id": prior_id,
            "source_commit": "0" * 40,
            "state": "rolled-back",
            "touched_aliases": [],
            "rollback_errors": [],
        },
    )

    report = apply_promotion(plan_path)

    assert "PROMOTION-RECOVERY-REQUIRED" in codes(report)
    assert report["artifacts"]["exit_code"] == 2
    assert not (paths["claude"] / "demo/SKILL.md").exists()


def test_check_revalidates_destination_after_child_link_resolution(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    forbidden = paths["targets"] / "plugins"
    forbidden.mkdir()
    linked = paths["agents"] / "demo"
    if not try_dir_link(forbidden, linked):
        pytest.skip("directory symlink/junction unavailable")

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-FORBIDDEN" in codes(report)
    assert not plan_path.exists()


def test_apply_revalidates_every_logical_alias(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    physical = paths["claude"] / "demo"
    physical.mkdir()
    (physical / "old.txt").write_text("old\n", encoding="utf-8")
    logical = paths["agents"] / "demo"
    if not try_dir_link(physical, logical):
        pytest.skip("directory symlink/junction unavailable")
    observed_digest = tree_digest(physical)
    commit_test_adjudications(
        root,
        [
            {
                "artifact_id": "fixture",
                "target_id": target_id,
                "observed_digest": observed_digest,
                "reason": (
                    "Fixture preimage required before logical alias retarget."
                ),
            }
            for target_id in REQUIRED_SKILL_TARGETS
        ],
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    aliased = next(
        item
        for item in plan["operations"]
        if set(item["logical_target_ids"]) == set(REQUIRED_SKILL_TARGETS)
    )
    assert set(aliased["logical_target_paths"]) == set(REQUIRED_SKILL_TARGETS)

    if logical.is_symlink():
        logical.unlink()
    else:
        os.rmdir(logical)
    replacement = paths["targets"] / "replacement"
    replacement.mkdir()
    if not try_dir_link(replacement, logical):
        pytest.skip("directory symlink/junction unavailable")

    report = apply_promotion(plan_path)

    assert "PROMOTION-LOGICAL-TARGET-CHANGED" in codes(report)
    assert (physical / "old.txt").read_text(encoding="utf-8") == "old\n"


def test_idempotent_operation_is_read_back_without_replace(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    target = paths["claude"] / "demo"
    target.mkdir()
    (target / "SKILL.md").write_bytes((root / "skills/demo/SKILL.md").read_bytes())
    commit_test_adjudication(
        root,
        target_id="claude_user_skills",
        observed_digest=tree_digest(target),
        reason="Fixture preimage required by idempotent apply coverage.",
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    noop = next(
        item
        for item in plan["operations"]
        if item["target_path"] == str(target.resolve())
    )
    assert noop["before_digest"] == noop["after_digest"]
    original_copy = __import__("packctl.promotion", fromlist=["_copy_artifact"])._copy_artifact
    destinations: list[Path] = []

    def recording_copy(
        source,
        destination,
        kind,
        source_files=None,
        **kwargs,
    ):
        destinations.append(Path(destination))
        return original_copy(
            source,
            destination,
            kind,
            source_files,
            **kwargs,
        )

    monkeypatch.setattr("packctl.promotion._copy_artifact", recording_copy)

    report = apply_promotion(plan_path)

    assert report["verdict"] == "PASS"
    assert not any(
        destination.parent == target.parent
        and f".{target.name}.packctl-stage-" in destination.name
        for destination in destinations
    )


def test_failure_after_moving_old_restores_original_target(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    existing = paths["claude"] / "demo"
    existing.mkdir()
    (existing / "old.txt").write_text("original\n", encoding="utf-8")
    commit_test_adjudication(
        root,
        target_id="claude_user_skills",
        observed_digest=tree_digest(existing),
        reason="Fixture preimage required by rollback coverage.",
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    index = next(
        index
        for index, item in enumerate(plan["operations"])
        if item["target_path"] == str(existing.resolve())
    )
    before = tree_digest(existing)

    report = apply_promotion(plan_path, fault_at=f"after_old_move:{index}")

    assert "PROMOTION-APPLY-FAILED" in codes(report)
    assert tree_digest(existing) == before
    assert (existing / "old.txt").read_text(encoding="utf-8") == "original\n"


def test_apply_reports_winerror_without_physical_path(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    blocked_target = paths["claude"] / "demo"
    original_rename = promotion.durable_rename
    failed = False

    def deny_publish_once(
        source: Path,
        destination: Path,
        *,
        replace: bool,
    ) -> None:
        nonlocal failed
        if (
            not failed
            and destination == blocked_target
            and ".packctl-stage-" in source.name
        ):
            failed = True
            raise OSError(
                None,
                "Access is denied.",
                str(destination),
                5,
            )
        original_rename(source, destination, replace=replace)

    monkeypatch.setattr(
        "packctl.promotion.durable_rename",
        deny_publish_once,
    )

    report = apply_promotion(plan_path)

    assert report["verdict"] == "FAIL"
    assert report["findings"][0]["evidence"] == "PermissionError:winerror=5"
    assert str(paths["targets"]) not in report["findings"][0]["evidence"]
    assert_plan_state(
        json.loads(plan_path.read_text(encoding="utf-8")),
        state="PRE",
    )


def test_receipt_is_not_published_when_commit_event_write_fails(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    original_append = promotion._append_event

    def fail_commit_event(
        transaction: Path,
        event_type: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        if event_type == "COMMIT":
            raise OSError("commit event fault")
        return original_append(transaction, event_type, payload)

    monkeypatch.setattr("packctl.promotion._append_event", fail_commit_event)

    report = apply_promotion(plan_path)

    assert "PROMOTION-APPLY-FAILED" in codes(report)
    assert not Path(plan["receipt_path"]).exists()


def test_apply_writes_all_targets_and_receipt_without_physical_paths(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)

    report = apply_promotion(plan_path)

    assert report["verdict"] == "PASS"
    commit = run_git(root, "rev-parse", "HEAD")
    source_digest = tree_digest(root / "skills/demo")
    assert tree_digest(paths["claude"] / "demo") == source_digest
    assert tree_digest(paths["agents"] / "demo") == source_digest
    assert tree_digest(paths["vault"] / "fixture" / commit) == source_digest
    receipt_path = Path(str(report["artifacts"]["receipt_path"]))
    receipt_text = receipt_path.read_text(encoding="utf-8")
    assert str(tmp_path) not in receipt_text
    receipt = json.loads(receipt_text)
    assert receipt["verdict"] == "PASS"
    assert set(receipt["target_ids"]) == {
        "claude_user_skills",
        "agents_user_skills",
        "obsidian_snapshots",
    }


@pytest.mark.parametrize(
    "fault_at",
    [
        "after_staging:0",
        "after_backup:0",
        "after_replace:0",
        "after_readback:0",
    ],
)
def test_fault_injection_restores_every_touched_target(
    repo_factory,
    tmp_path: Path,
    fault_at: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    existing = paths["claude"] / "demo"
    existing.mkdir()
    (existing / "old.txt").write_text("original\n", encoding="utf-8")
    existing_agents = paths["agents"] / "demo"
    existing_agents.mkdir()
    (existing_agents / "old.txt").write_text("original\n", encoding="utf-8")
    commit_test_adjudications(
        root,
        [
            {
                "artifact_id": "fixture",
                "target_id": target_id,
                "observed_digest": tree_digest(target),
                "reason": "Fixture preimage required by fault coverage.",
            }
            for target_id, target in (
                ("claude_user_skills", existing),
                ("agents_user_skills", existing_agents),
            )
        ],
    )
    check_promotion(root, map_path, config_path, plan_path)
    before = tree_digest(existing)

    report = apply_promotion(plan_path, fault_at=fault_at)

    assert "PROMOTION-APPLY-FAILED" in codes(report)
    assert tree_digest(existing) == before
    assert tree_digest(existing_agents) == before
    assert not report["artifacts"].get("receipt_path")
    residue = [
        path
        for path in paths["targets"].rglob("*")
        if ".packctl-stage-" in path.name or ".packctl-old-" in path.name
    ]
    assert residue == []


def test_failed_rollback_requires_intervention_exit_2(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)

    report = apply_promotion(
        plan_path,
        fault_at="after_replace:0",
        rollback_fault=True,
    )

    assert "PROMOTION-ROLLBACK-FAILED" in codes(report)
    assert report["artifacts"]["requires_intervention"] is True
    assert report["artifacts"]["exit_code"] == 2


def test_legacy_skill_overlap_blocks_apply(repo_factory, tmp_path: Path) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    legacy = paths["claude"] / "legacy-demo"
    legacy.mkdir()
    (legacy / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Old duplicate.\n---\n",
        encoding="utf-8",
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-LEGACY-OVERLAP" in codes(report)
    assert not plan_path.exists()


def test_vault_snapshot_preserves_private_note(repo_factory, tmp_path: Path) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    private = paths["vault"] / "private-note.md"
    private.write_text("private durable context\n", encoding="utf-8")
    before = private.read_bytes()
    check_promotion(root, map_path, config_path, plan_path)

    apply_promotion(plan_path)

    assert private.read_bytes() == before


APPLY_TERMINATION_BOUNDARIES = (
    ["after_pending"]
    + [
        f"{boundary}:{index}"
        for boundary in (
            "after_stage",
            "after_backup",
            "after_old_move",
            "after_publish",
            "after_target_event",
        )
        for index in range(4)
    ]
    + ["after_post_verified", "after_commit"]
)


def test_apply_publishes_hash_chained_terminal_journal(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    report = apply_promotion(plan_path)

    assert report["verdict"] == "PASS"
    transaction = transaction_root(plan)
    assert json.loads((transaction / "plan.json").read_text(encoding="utf-8")) == plan
    events = assert_valid_event_chain(transaction)
    assert events[0]["event_type"] == "PENDING"
    assert events[-2]["event_type"] == "POST_VERIFIED"
    assert events[-1]["event_type"] == "COMMIT"
    assert sum(event["event_type"] == "COMMIT" for event in events) == 1
    assert all(event["event_type"] != "ABORT" for event in events)


@pytest.mark.parametrize("boundary", APPLY_TERMINATION_BOUNDARIES)
def test_apply_process_termination_recovers_to_one_decided_state(
    repo_factory,
    tmp_path: Path,
    boundary: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_every_target_with_pre_state(root, paths)
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    adjudication_path = root / "promotions/adjudications.json"
    adjudications_before = json.loads(
        adjudication_path.read_text(encoding="utf-8")
    )

    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": boundary},
    )

    assert killed.returncode == 97
    transaction = transaction_root(plan)
    recovered = promotion.recover_promotion(transaction)
    assert recovered["verdict"] == "PASS"
    events = assert_valid_event_chain(transaction)
    receipt_path = Path(str(plan["receipt_path"]))
    adjudications_after = json.loads(
        adjudication_path.read_text(encoding="utf-8")
    )
    if boundary == "after_commit":
        assert events[-1]["event_type"] == "COMMIT"
        assert_plan_state(plan, state="POST")
        assert receipt_path.is_file()
        expected_post = {
            (str(operation["artifact_id"]), str(target_id)): str(
                operation["after_digest"]
            )
            for operation in plan["operations"]
            for target_id in operation["logical_target_ids"]
        }
        assert {
            (entry["artifact_id"], entry["target_id"]): entry["observed_digest"]
            for entry in adjudications_after["adjudications"]
        } == expected_post
    else:
        assert events[-1]["event_type"] == "ABORT"
        assert_plan_state(plan, state="PRE")
        assert not receipt_path.exists()
        assert adjudications_after == adjudications_before


@pytest.mark.parametrize(
    "boundary",
    [
        "after_recovery_stage:0",
        "after_recovery_old_move:0",
        "after_pre_publish:0",
        "after_pre_verified:0",
        "after_abort",
    ],
)
def test_recovery_process_termination_is_restartable(
    repo_factory,
    tmp_path: Path,
    boundary: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_every_target_with_pre_state(root, paths)
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed_apply = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": "after_publish:0"},
    )
    assert killed_apply.returncode == 97
    transaction = transaction_root(plan)

    killed_recovery = run_promote_process(
        root,
        "--recover",
        "--transaction-root",
        str(transaction),
        environment={"PACKCTL_RECOVER_TERMINATE_AT": boundary},
    )
    assert killed_recovery.returncode == 97

    recovered = run_promote_process(
        root,
        "--recover",
        "--transaction-root",
        str(transaction),
    )
    assert recovered.returncode == 0, recovered.stderr
    events = assert_valid_event_chain(transaction)
    assert events[-1]["event_type"] == "ABORT"
    assert_plan_state(plan, state="PRE")
    assert not Path(str(plan["receipt_path"])).exists()


@pytest.mark.parametrize(
    "mutation",
    ["payload", "truncate", "sequence", "plan"],
)
def test_recovery_rejects_corrupt_authoritative_evidence_without_target_writes(
    repo_factory,
    tmp_path: Path,
    mutation: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_every_target_with_pre_state(root, paths)
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": "after_pending"},
    )
    assert killed.returncode == 97
    transaction = transaction_root(plan)
    before = {
        str(operation["target_path"]): tree_digest(
            Path(str(operation["target_path"]))
        )
        for operation in plan["operations"]
    }
    first_event = transaction / "events/00000000.json"
    if mutation == "payload":
        event = json.loads(first_event.read_text(encoding="utf-8"))
        event["payload"] = {"tampered": True}
        write_json(first_event, event)
    elif mutation == "truncate":
        first_event.write_text("{", encoding="utf-8")
    elif mutation == "sequence":
        first_event.rename(transaction / "events/00000001.json")
    else:
        sealed_plan = json.loads(
            (transaction / "plan.json").read_text(encoding="utf-8")
        )
        sealed_plan["source_commit"] = "0" * 40
        write_json(transaction / "plan.json", sealed_plan)

    report = promotion.recover_promotion(transaction)

    assert report["verdict"] == "FAIL"
    assert report["artifacts"]["exit_code"] == 2
    assert "PROMOTION-JOURNAL-INVALID" in codes(report)
    assert {
        path: tree_digest(Path(path))
        for path in before
    } == before


def test_recovery_rejects_foreign_target_digest_without_deleting_it(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_every_target_with_pre_state(root, paths)
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": "after_publish:0"},
    )
    assert killed.returncode == 97
    target = Path(str(plan["operations"][0]["target_path"]))
    sentinel = target / "foreign-after-crash.txt"
    sentinel.write_text("operator data\n", encoding="utf-8")
    foreign_digest = tree_digest(target)

    report = promotion.recover_promotion(transaction_root(plan))

    assert report["verdict"] == "FAIL"
    assert report["artifacts"]["exit_code"] == 2
    assert "PROMOTION-FOREIGN-TARGET" in codes(report)
    assert tree_digest(target) == foreign_digest
    assert sentinel.read_text(encoding="utf-8") == "operator data\n"


def test_commit_recovery_refuses_to_overwrite_foreign_receipt(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": "after_commit"},
    )
    assert killed.returncode == 97
    receipt_path = Path(str(plan["receipt_path"]))
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    foreign = b'{"foreign":true}\n'
    receipt_path.write_bytes(foreign)

    report = promotion.recover_promotion(transaction_root(plan))

    assert report["verdict"] == "FAIL"
    assert report["artifacts"]["exit_code"] == 2
    assert "PROMOTION-RECEIPT-CONFLICT" in codes(report)
    assert receipt_path.read_bytes() == foreign


@pytest.mark.parametrize(
    ("termination_boundary", "terminal", "state"),
    [
        ("after_publish:0", "ABORT", "PRE"),
        ("after_commit", "COMMIT", "POST"),
    ],
)
def test_recovery_is_idempotent_after_terminal_decision(
    repo_factory,
    tmp_path: Path,
    termination_boundary: str,
    terminal: str,
    state: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_every_target_with_pre_state(root, paths)
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": termination_boundary},
    )
    assert killed.returncode == 97
    transaction = transaction_root(plan)

    first = promotion.recover_promotion(transaction)
    event_bytes = {
        path.name: path.read_bytes()
        for path in (transaction / "events").glob("*.json")
    }
    second = promotion.recover_promotion(transaction)

    assert first["verdict"] == second["verdict"] == "PASS"
    assert {
        path.name: path.read_bytes()
        for path in (transaction / "events").glob("*.json")
    } == event_bytes
    assert assert_valid_event_chain(transaction)[-1]["event_type"] == terminal
    assert_plan_state(plan, state=state)


def test_commit_seals_exact_create_only_receipt_hash(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    report = apply_promotion(plan_path)

    assert report["verdict"] == "PASS"
    events = assert_valid_event_chain(transaction_root(plan))
    commit = events[-1]
    receipt_path = Path(str(plan["receipt_path"]))
    receipt_bytes = receipt_path.read_bytes()
    assert commit["payload"]["receipt_hash"] == sha256_bytes(receipt_bytes)
    assert str(tmp_path).encode("utf-8") not in receipt_bytes


def test_apply_refuses_mixed_pending_transaction_until_recovery(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_every_target_with_pre_state(root, paths)
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": "after_publish:0"},
    )
    assert killed.returncode == 97
    mixed = {
        str(operation["target_path"]): tree_digest(
            Path(str(operation["target_path"]))
        )
        for operation in plan["operations"]
    }

    refused = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
    )

    assert refused.returncode == 2
    report = json.loads(
        plan_path.with_suffix(".apply-report.json").read_text(
            encoding="utf-8"
        )
    )
    assert "PROMOTION-RECOVERY-REQUIRED" in codes(report)
    assert {
        path: tree_digest(Path(path))
        for path in mixed
    } == mixed


@pytest.mark.parametrize(
    ("termination_boundary", "terminal_code"),
    [
        ("after_commit", "PROMOTION-COMMIT-STATE-INVALID"),
        ("after_pending", "PROMOTION-ABORT-STATE-INVALID"),
    ],
)
def test_terminal_decision_rejects_later_target_mutation(
    repo_factory,
    tmp_path: Path,
    termination_boundary: str,
    terminal_code: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_every_target_with_pre_state(root, paths)
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": termination_boundary},
    )
    assert killed.returncode == 97
    transaction = transaction_root(plan)
    if termination_boundary == "after_pending":
        assert promotion.recover_promotion(transaction)["verdict"] == "PASS"
    target = Path(str(plan["operations"][0]["target_path"]))
    sentinel = target / "foreign-after-terminal.txt"
    sentinel.write_text("operator mutation\n", encoding="utf-8")
    foreign_digest = tree_digest(target)

    report = promotion.recover_promotion(transaction)

    assert report["verdict"] == "FAIL"
    assert report["artifacts"]["exit_code"] == 2
    assert terminal_code in codes(report)
    assert tree_digest(target) == foreign_digest
    assert sentinel.read_text(encoding="utf-8") == "operator mutation\n"


def test_three_sequential_commits_accept_superseded_terminal_history(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    exclude = root / ".git/info/exclude"
    exclude.write_text(
        exclude.read_text(encoding="utf-8")
        + "\npromotions/receipts/\n",
        encoding="utf-8",
    )
    transaction_ids: list[str] = []
    for version in range(1, 4):
        skill = root / "skills/demo/SKILL.md"
        skill.write_text(
            "---\n"
            "name: demo\n"
            f"description: Promotion fixture v{version}.\n"
            "---\n"
            "# Demo\n",
            encoding="utf-8",
        )
        run_git(root, "add", "skills/demo/SKILL.md")
        run_git(root, "commit", "-qm", f"fixture v{version}")
        checked = check_promotion(
            root,
            map_path,
            config_path,
            plan_path,
        )
        assert checked["verdict"] in {"PASS", "WARN"}
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        transaction_ids.append(str(plan["transaction_id"]))

        applied = apply_promotion(plan_path)

        assert applied["verdict"] == "PASS"
        assert tree_digest(paths["claude"] / "demo") == tree_digest(
            root / "skills/demo"
        )
    assert len(set(transaction_ids)) == 3


def test_clean_abort_can_be_rechecked_and_retried_as_new_transaction(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    first_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    failed = apply_promotion(plan_path, fault_at="after_stage:0")
    assert "PROMOTION-APPLY-FAILED" in codes(failed)
    assert assert_valid_event_chain(transaction_root(first_plan))[-1][
        "event_type"
    ] == "ABORT"

    check_promotion(root, map_path, config_path, plan_path)
    retry_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    retried = apply_promotion(plan_path)

    assert retry_plan["transaction_id"] != first_plan["transaction_id"]
    assert retried["verdict"] == "PASS"
    assert (paths["claude"] / "demo/SKILL.md").is_file()


def test_cli_recovery_does_not_write_report_inside_invalid_transaction(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": "after_pending"},
    )
    assert killed.returncode == 97
    transaction = transaction_root(plan)
    (transaction / "events/00000000.json").write_text(
        "{",
        encoding="utf-8",
    )

    recovered = run_promote_process(
        root,
        "--recover",
        "--transaction-root",
        str(transaction),
    )

    assert recovered.returncode == 2
    assert not (transaction / "recover-report.json").exists()


def test_failed_transaction_initialization_never_publishes_a_transaction(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    original_write = promotion.durable_write_json

    def fail_sealed_plan(
        path: Path,
        value: object,
        *,
        create_only: bool,
    ) -> bytes:
        if path.name == "plan.json":
            raise OSError("sealed plan fsync fault")
        return original_write(path, value, create_only=create_only)

    monkeypatch.setattr(
        "packctl.promotion.durable_write_json",
        fail_sealed_plan,
    )

    report = apply_promotion(plan_path)

    assert "PROMOTION-APPLY-FAILED" in codes(report)
    assert "exit_code" not in report["artifacts"]
    assert not transaction_root(plan).exists()
    assert not any(
        path.name.endswith(".packctl-init")
        for path in paths["backups"].iterdir()
    )
    assert not (paths["claude"] / "demo").exists()


def test_apply_revalidates_sealed_contracts_after_acquiring_os_locks(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    original_enter = promotion._RootLocks.__enter__
    mutated = False

    def mutate_after_lock(self):
        nonlocal mutated
        result = original_enter(self)
        if not mutated:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["targets"]["claude_user_skills"]["ownership"] = (
                "changed-after-preflight"
            )
            write_json(config_path, config)
            mutated = True
        return result

    monkeypatch.setattr(
        promotion._RootLocks,
        "__enter__",
        mutate_after_lock,
    )

    report = apply_promotion(plan_path)

    assert "PROMOTION-CONTRACT-CHANGED" in codes(report)
    assert not transaction_root(
        json.loads(plan_path.read_text(encoding="utf-8"))
    ).exists()
    assert not (paths["claude"] / "demo").exists()


def test_target_change_after_backup_is_preserved_before_old_move(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_every_target_with_pre_state(root, paths)
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    first_target = Path(str(plan["operations"][0]["target_path"]))
    sentinel = first_target / "external-after-backup.txt"
    original_append = promotion._append_event
    injected = False

    def mutate_after_backup(
        transaction: Path,
        event_type: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        nonlocal injected
        event = original_append(transaction, event_type, payload)
        if event_type == "BACKUP_READY" and not injected:
            sentinel.write_text("external mutation\n", encoding="utf-8")
            injected = True
        return event

    monkeypatch.setattr(
        "packctl.promotion._append_event",
        mutate_after_backup,
    )

    report = apply_promotion(plan_path)

    assert report["verdict"] == "FAIL"
    assert report["artifacts"]["exit_code"] == 2
    assert sentinel.read_text(encoding="utf-8") == "external mutation\n"


@pytest.mark.skipif(os.name != "nt", reason="Windows read-only semantics")
def test_copy_artifact_syncs_and_preserves_readonly_files(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    source_file = source / "readonly.txt"
    source_file.write_text("durable\n", encoding="utf-8")
    source_file.chmod(0o444)
    destination = tmp_path / "destination"

    try:
        promotion._copy_artifact(source, destination, "tree")

        copied = destination / source_file.name
        assert copied.read_bytes() == source_file.read_bytes()
        assert not copied.stat().st_mode & 0o200
    finally:
        for path in (source_file, destination / source_file.name):
            if path.exists():
                path.chmod(0o666)


@pytest.mark.skipif(os.name != "nt", reason="Windows read-only semantics")
def test_copy_artifact_restores_readonly_attribute_when_fsync_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    source_file = source / "readonly.txt"
    source_file.write_text("durable\n", encoding="utf-8")
    source_file.chmod(0o444)
    destination = tmp_path / "destination"

    def fail_fsync(_descriptor: int) -> None:
        raise OSError("injected fsync failure")

    monkeypatch.setattr(common.os, "fsync", fail_fsync)
    try:
        with pytest.raises(OSError, match="injected fsync failure"):
            promotion._copy_artifact(source, destination, "tree")

        copied = destination / source_file.name
        assert not copied.stat().st_mode & 0o200
    finally:
        for path in (source_file, destination / source_file.name):
            if path.exists():
                path.chmod(0o666)


@pytest.mark.skipif(os.name != "nt", reason="Windows read-only semantics")
def test_remove_artifact_deletes_readonly_tree(tmp_path: Path) -> None:
    tree = tmp_path / "readonly-tree"
    tree.mkdir()
    readonly_file = tree / "readonly.txt"
    readonly_file.write_text("retired sidecar\n", encoding="utf-8")
    readonly_file.chmod(0o444)

    try:
        promotion._remove_artifact(tree)
        assert not tree.exists()
    finally:
        if readonly_file.exists():
            readonly_file.chmod(0o666)


@pytest.mark.skipif(os.name != "nt", reason="Windows read-only semantics")
def test_remove_artifact_deletes_readonly_file(tmp_path: Path) -> None:
    readonly_file = tmp_path / "readonly.txt"
    readonly_file.write_text("retired sidecar\n", encoding="utf-8")
    readonly_file.chmod(0o444)

    try:
        promotion._remove_artifact(readonly_file)
        assert not readonly_file.exists()
    finally:
        if readonly_file.exists():
            readonly_file.chmod(0o666)


@pytest.mark.skipif(os.name != "nt", reason="Windows read-only semantics")
def test_remove_artifact_does_not_mask_other_permission_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = tmp_path / "writable.txt"
    artifact.write_text("foreign denial\n", encoding="utf-8")

    def deny_unlink(_path: Path) -> None:
        raise PermissionError("injected non-readonly denial")

    monkeypatch.setattr(Path, "unlink", deny_unlink)
    with pytest.raises(PermissionError, match="non-readonly denial"):
        promotion._remove_artifact(artifact)


PHRASE_LONG = "an external ODOL->MLOD converter (not distributed with this pack)"
PHRASE_SHORT = "external ODOL->MLOD converter"
PHRASE_LOCAL = "`the-local-tool`"


def configure_phrase_alias(
    config_path: Path,
    tmp_path: Path,
    *,
    phrase: str = PHRASE_SHORT,
    value: str = PHRASE_LOCAL,
    kind: str = "phrase",
) -> None:
    dayz_projects = tmp_path / "DayZ Projects"
    dayz_projects.mkdir(exist_ok=True)
    configure_path_aliases(
        config_path,
        {
            "<dayz-projects>": {"kind": "path", "value": str(dayz_projects)},
            "<you>": {"kind": "fragment", "value": "fixture-user"},
            phrase: {"kind": kind, "value": value},
        },
    )


def test_phrase_alias_localizes_markdown_on_promotion(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    configure_phrase_alias(config_path, tmp_path)
    published = f"Pre-process the model with {PHRASE_SHORT} first.\n"
    source = commit_demo_payload(root, "references/scope.md", published)

    checked = check_promotion(root, map_path, config_path, plan_path)
    assert "PROMOTION-CONFIG-INVALID" not in codes(checked)
    applied = apply_promotion(plan_path)

    assert applied["verdict"] == "PASS"
    installed = (paths["claude"] / "demo/references/scope.md").read_text(
        encoding="utf-8",
    )
    assert installed == f"Pre-process the model with {PHRASE_LOCAL} first.\n"
    # the published wording is what stays in the repository
    assert source.read_text(encoding="utf-8") == published


def test_phrase_alias_localizes_executable_payload(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    configure_phrase_alias(config_path, tmp_path)
    commit_demo_payload(
        root,
        "scripts/overlay.py",
        f'"""Built on {PHRASE_SHORT} internals."""\n',
    )

    checked = check_promotion(root, map_path, config_path, plan_path)
    assert "PROMOTION-CONFIG-INVALID" not in codes(checked)
    applied = apply_promotion(plan_path)

    assert applied["verdict"] == "PASS"
    assert (
        paths["claude"] / "demo/scripts/overlay.py"
    ).read_text(encoding="utf-8") == f'"""Built on {PHRASE_LOCAL} internals."""\n'


def test_longest_phrase_wins_over_contained_phrase(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    dayz_projects = tmp_path / "DayZ Projects"
    dayz_projects.mkdir(exist_ok=True)
    configure_path_aliases(
        config_path,
        {
            "<dayz-projects>": {"kind": "path", "value": str(dayz_projects)},
            "<you>": {"kind": "fragment", "value": "fixture-user"},
            PHRASE_SHORT: {"kind": "phrase", "value": "SHORT"},
            PHRASE_LONG: {"kind": "phrase", "value": "LONG"},
        },
    )
    commit_demo_payload(root, "references/scope.md", f"Use {PHRASE_LONG}.\n")

    check_promotion(root, map_path, config_path, plan_path)
    applied = apply_promotion(plan_path)

    assert applied["verdict"] == "PASS"
    assert (
        paths["claude"] / "demo/references/scope.md"
    ).read_text(encoding="utf-8") == "Use LONG.\n"


def test_phrase_alias_does_not_localize_path_placeholders_in_markdown(
    repo_factory,
    tmp_path: Path,
) -> None:
    """Configuring a phrase must not drag markdown into path localisation.

    Published documentation carries <vault>-style tokens on purpose; they are
    part of the text a reader is meant to see.
    """
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    configure_phrase_alias(config_path, tmp_path)
    literal = f"Use <dayz-projects> with {PHRASE_SHORT}.\n"
    commit_demo_payload(root, "references/policy.md", literal)

    check_promotion(root, map_path, config_path, plan_path)
    applied = apply_promotion(plan_path)

    assert applied["verdict"] == "PASS"
    assert (
        paths["claude"] / "demo/references/policy.md"
    ).read_text(encoding="utf-8") == f"Use <dayz-projects> with {PHRASE_LOCAL}.\n"


def test_phrase_alias_declared_with_path_kind_fails_config(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    configure_phrase_alias(config_path, tmp_path, kind="path")
    commit_demo_payload(root, "references/scope.md", f"Uses {PHRASE_SHORT}.\n")
    backup_entries = list(paths["backups"].rglob("*"))

    report = check_promotion(root, map_path, config_path, plan_path)

    matches = [
        item for item in report["findings"]
        if item["code"] == "PROMOTION-CONFIG-INVALID"
    ]
    assert len(matches) == 1
    assert matches[0]["evidence"] == PHRASE_SHORT
    assert not plan_path.exists()
    assert list(paths["backups"].rglob("*")) == backup_entries


def test_path_placeholder_declared_with_phrase_kind_fails_config(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path,
    )
    configure_path_aliases(
        config_path,
        {
            "<dayz-projects>": {"kind": "phrase", "value": "anything"},
            "<you>": {"kind": "fragment", "value": "fixture-user"},
        },
    )
    commit_demo_payload(root, "references/scope.md", "text\n")

    report = check_promotion(root, map_path, config_path, plan_path)

    matches = [
        item for item in report["findings"]
        if item["code"] == "PROMOTION-CONFIG-INVALID"
    ]
    assert matches
    assert any(item["evidence"] == "<dayz-projects>" for item in matches)
    assert not plan_path.exists()


def test_phrase_outside_the_closed_list_fails_config(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path,
    )
    configure_phrase_alias(
        config_path,
        tmp_path,
        phrase="some phrase nobody registered",
    )
    commit_demo_payload(root, "references/scope.md", "text\n")

    report = check_promotion(root, map_path, config_path, plan_path)

    matches = [
        item for item in report["findings"]
        if item["code"] == "PROMOTION-CONFIG-INVALID"
    ]
    assert matches
    assert any(
        item["evidence"] == "some phrase nobody registered" for item in matches
    )
    assert not plan_path.exists()


def _assert_untouched(
    plan_path: Path,
    paths: dict[str, Path],
    *,
    backups: list[Path],
    claude_demo: bool = False,
) -> None:
    assert not plan_path.exists()
    assert (paths["claude"] / "demo").exists() is claude_demo
    assert list(paths["backups"].rglob("*")) == backups


def test_v2_check_without_genesis_fails_uninitialized(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    backups = backup_entries(paths)

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-INSTALLATION-UNINITIALIZED" in codes(report)
    _assert_untouched(plan_path, paths, backups=backups)


def test_bootstrap_rejects_v1_config_without_writes(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    backups = backup_entries(paths)

    report = check_promotion(
        root, map_path, config_path, plan_path, bootstrap=True,
    )

    assert "PROMOTION-BOOTSTRAP-UNSUPPORTED" in codes(report)
    _assert_untouched(plan_path, paths, backups=backups)


def test_bootstrap_requires_plan_path(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, _, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    backups = backup_entries(paths)

    report = check_promotion(
        root, map_path, config_path, None, bootstrap=True,
    )

    assert "PROMOTION-BOOTSTRAP-PLAN-REQUIRED" in codes(report)
    assert list(paths["backups"].rglob("*")) == backups
    assert not (paths["claude"] / "demo").exists()


def test_bootstrap_v2_with_foreign_v1_receipts_then_relocated_checkout(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    for index, name in enumerate(("aa" * 12, "ab" * 12, "ac" * 12, "ad" * 12)):
        commit_test_receipt(
            root,
            backup_root=paths["backups"],
            target_path=paths["claude"] / "demo",
            name=name,
            target_id="claude_user_skills",
            after_digest="0" * 64,
            completed_at=f"2026-09-11T10:0{index}:00+00:00",
            seal_journal=False,
        )

    checked = check_promotion(
        root, map_path, config_path, plan_path, bootstrap=True,
    )
    assert checked["verdict"] in {"PASS", "WARN"}
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["schema_version"] == 2
    assert plan["installation_id"] == INSTALLATION_A
    assert plan["bootstrap"] is True
    check_head = run_git(root, "rev-parse", "HEAD")
    assert plan["source_commit"] == check_head

    applied = apply_promotion(plan_path)
    assert applied["verdict"] == "PASS"
    receipt_path = commit_published_receipt(
        root, applied, "genesis v2 receipt",
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["schema_version"] == 2
    assert receipt["installation_id"] == INSTALLATION_A
    assert receipt["bootstrap"] is True
    assert receipt["source_commit"] == check_head
    assert list(root.rglob("events/*.json")) == []
    journal = paths["backups"] / str(plan["transaction_id"])
    assert (journal / "events").is_dir()

    moved = tmp_path / "moved-checkout"
    shutil.copytree(root, moved)
    moved_plan = tmp_path / "moved-plan.json"
    relocated = check_promotion(
        moved, map_path, config_path, moved_plan,
    )
    assert "PROMOTION-RECEIPT-UNSEALED" not in codes(relocated)
    assert "PROMOTION-INSTALLATION-UNINITIALIZED" not in codes(relocated)
    if relocated["verdict"] not in {"PASS", "WARN"}:
        raise AssertionError(codes(relocated))
    assert moved_plan.is_file()
    relocated_plan = json.loads(moved_plan.read_text(encoding="utf-8"))
    assert relocated_plan["bootstrap"] is False
    assert relocated_plan["installation_id"] == INSTALLATION_A


def test_g5_v1_v2_restore_from_git_commits(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    skill = root / "skills/demo/SKILL.md"
    v1_bytes = skill.read_bytes()

    genesis_head = run_git(root, "rev-parse", "HEAD")
    genesis_check = check_promotion(
        root, map_path, config_path, plan_path, bootstrap=True,
    )
    assert genesis_check["verdict"] in {"PASS", "WARN"}
    genesis_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert genesis_plan["source_commit"] == genesis_head
    genesis_apply = apply_promotion(plan_path)
    assert genesis_apply["verdict"] == "PASS"
    genesis_receipt = json.loads(
        commit_published_receipt(root, genesis_apply, "genesis").read_text(
            encoding="utf-8"
        )
    )
    assert genesis_receipt["source_commit"] == genesis_head
    assert genesis_receipt["bootstrap"] is True

    skill.write_text(
        "---\nname: demo\ndescription: v2.\n---\n# Demo v2\n",
        encoding="utf-8",
        newline="\n",
    )
    run_git(root, "add", "skills/demo/SKILL.md")
    run_git(root, "commit", "-qm", "fixture v2")
    v2_head = run_git(root, "rev-parse", "HEAD")
    v2_check = check_promotion(root, map_path, config_path, plan_path)
    assert v2_check["verdict"] in {"PASS", "WARN"}
    v2_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert v2_plan["bootstrap"] is False
    assert v2_plan["source_commit"] == v2_head
    v2_apply = apply_promotion(plan_path)
    assert v2_apply["verdict"] == "PASS"
    v2_receipt = json.loads(
        commit_published_receipt(root, v2_apply, "v2 receipt").read_text(
            encoding="utf-8"
        )
    )
    assert v2_receipt["source_commit"] == v2_head
    assert v2_receipt["bootstrap"] is False

    skill.write_bytes(v1_bytes)
    run_git(root, "add", "skills/demo/SKILL.md")
    run_git(root, "commit", "-qm", "restore v1 bytes")
    restore_head = run_git(root, "rev-parse", "HEAD")
    restore_check = check_promotion(root, map_path, config_path, plan_path)
    assert restore_check["verdict"] in {"PASS", "WARN"}
    restore_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert restore_plan["source_commit"] == restore_head
    restore_apply = apply_promotion(plan_path)
    assert restore_apply["verdict"] == "PASS"
    restore_receipt = json.loads(
        commit_published_receipt(root, restore_apply, "restore receipt").read_text(
            encoding="utf-8"
        )
    )
    assert restore_receipt["source_commit"] == restore_head
    assert tree_digest(paths["claude"] / "demo") == tree_digest(root / "skills/demo")
    assert (paths["claude"] / "demo" / "SKILL.md").read_bytes() == v1_bytes
    assert (paths["agents"] / "demo" / "SKILL.md").read_bytes() == v1_bytes
    journals = [
        path
        for path in paths["backups"].iterdir()
        if path.is_dir() and not path.name.startswith(".")
    ]
    assert len(journals) == 3
    assert list(root.rglob("events/*.json")) == []


def test_v2_matching_receipt_without_journal_fails_closed(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    commit_test_receipt(
        root,
        backup_root=paths["backups"],
        target_path=paths["claude"] / "demo",
        name="b0" * 12,
        target_id="claude_user_skills",
        after_digest="0" * 64,
        completed_at="2026-09-11T12:00:00+00:00",
        seal_journal=False,
        schema_version=2,
        installation_id=INSTALLATION_A,
        bootstrap=True,
    )
    backups = backup_entries(paths)

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-UNSEALED" in codes(report)
    assert not plan_path.exists()
    assert list(paths["backups"].rglob("*")) == backups
    assert not (paths["claude"] / "demo").exists()


def test_v2_receipt_source_commit_must_be_ancestor(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    commit_test_receipt(
        root,
        backup_root=paths["backups"],
        target_path=paths["claude"] / "demo",
        name="ae" * 12,
        target_id="claude_user_skills",
        after_digest="0" * 64,
        completed_at="2026-09-11T12:00:00+00:00",
        source_commit="ab" * 20,
        schema_version=2,
        installation_id=INSTALLATION_A,
        bootstrap=True,
    )
    backups = backup_entries(paths)

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-COMMIT-NOT-ANCESTOR" in codes(report)
    assert not plan_path.exists()
    assert not (paths["claude"] / "demo").exists()
    assert backup_entries(paths) == backups


def _remove_sealed_checkout(root: Path, tmp_path: Path) -> Path:
    # The checkout that sealed the receipts disappears, as a temporary
    # worktree does after its merge; the repository lives on elsewhere.
    moved = tmp_path / "moved-checkout"
    shutil.move(str(root), str(moved))
    return moved


def test_v1_receipt_of_removed_checkout_is_read_where_head_tracks_it(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = paths["claude"] / "demo"
    digest = _set_test_target_state(target, "promoted\n")
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="c1" * 12, target_id="claude_user_skills",
        after_digest=digest, completed_at="2026-09-11T12:00:00+00:00",
    )
    moved = _remove_sealed_checkout(root, tmp_path)

    report = check_promotion(moved, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-JOURNAL-MISMATCH" not in codes(report)
    assert "PROMOTION-TARGET-UNEXPLAINED" not in codes(report)
    assert plan_path.is_file()


def test_v1_receipt_of_removed_checkout_untracked_at_head_fails_closed(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = paths["claude"] / "demo"
    digest = _set_test_target_state(target, "promoted\n")
    name = "c2" * 12
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name=name, target_id="claude_user_skills",
        after_digest=digest, completed_at="2026-09-11T12:00:00+00:00",
    )
    moved = _remove_sealed_checkout(root, tmp_path)
    relative = f"promotions/receipts/{name}.json"
    run_git(moved, "rm", "-q", "--cached", relative)
    exclude = moved / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    with exclude.open("a", encoding="utf-8") as handle:
        handle.write(relative + "\n")
    run_git(moved, "commit", "-qm", "untrack the receipt")

    report = check_promotion(moved, map_path, config_path, plan_path)

    assert "PROMOTION-DIRTY" not in codes(report)
    assert "PROMOTION-RECEIPT-JOURNAL-MISMATCH" in codes(report)
    assert not plan_path.exists()


def test_v1_journal_sealed_outside_the_receipts_layout_stays_refused_after_a_move(
    repo_factory, tmp_path: Path,
) -> None:
    # The journal loader refuses a sealed receipt_path other than
    # <source_root>/promotions/receipts/<id>.json, so relocation never sees it.
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = paths["claude"] / "demo"
    digest = _set_test_target_state(target, "promoted\n")
    name = "c3" * 12
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name=name, target_id="claude_user_skills",
        after_digest=digest, completed_at="2026-09-11T12:00:00+00:00",
        sealed_receipt_path=tmp_path / "elsewhere" / f"{name}.json",
    )
    moved = _remove_sealed_checkout(root, tmp_path)

    report = check_promotion(moved, map_path, config_path, plan_path)

    assert codes(report) == ["PROMOTION-RECEIPT-UNSEALED"]
    assert not plan_path.exists()


def test_v1_promotion_continues_from_a_new_checkout_of_the_repository(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    first = check_promotion(root, map_path, config_path, plan_path)
    assert first["verdict"] in {"PASS", "WARN"}, codes(first)
    applied = apply_promotion(plan_path)
    assert applied["verdict"] == "PASS", codes(applied)
    commit_published_receipt(root, applied, "v1 receipt")
    moved = _remove_sealed_checkout(root, tmp_path)
    skill = moved / "skills/demo/SKILL.md"
    skill.write_text(
        "---\nname: demo\ndescription: v2.\n---\n# Demo v2\n",
        encoding="utf-8",
        newline="\n",
    )
    run_git(moved, "add", "skills/demo/SKILL.md")
    run_git(moved, "commit", "-qm", "fixture v2")
    second_plan = tmp_path / "second-plan.json"

    checked = check_promotion(moved, map_path, config_path, second_plan)
    assert checked["verdict"] in {"PASS", "WARN"}, codes(checked)
    second = apply_promotion(second_plan)

    assert second["verdict"] == "PASS", codes(second)
    assert (paths["claude"] / "demo" / "SKILL.md").read_bytes() == skill.read_bytes()
    assert (paths["agents"] / "demo" / "SKILL.md").read_bytes() == skill.read_bytes()


def test_journal_sweep_reads_relocated_v1_receipt_only_while_head_tracks_it(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = paths["claude"] / "demo"
    digest = _set_test_target_state(target, "promoted\n")
    name = "c5" * 12
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name=name, target_id="claude_user_skills",
        after_digest=digest, completed_at="2026-09-11T12:00:00+00:00",
    )
    moved = _remove_sealed_checkout(root, tmp_path)

    promotion._scan_transactions(paths["backups"], live_root=moved)

    run_git(moved, "rm", "-q", "--cached", f"promotions/receipts/{name}.json")
    run_git(moved, "commit", "-qm", "untrack the receipt")
    with pytest.raises(promotion._PromotionIntegrityError) as raised:
        promotion._scan_transactions(paths["backups"], live_root=moved)
    assert raised.value.code == "PROMOTION-RECOVERY-REQUIRED"
    assert raised.value.evidence == f"{name}:{name}:receipt-missing"


def _tracked_receipt_and_plan(
    repo_factory, tmp_path: Path, name: str,
) -> tuple[Path, dict[str, object]]:
    # A receipt that HEAD tracks, sealed by a checkout that no longer exists:
    # with schema_version 1 every relocation condition holds.
    root, _, _, _, _ = promotion_fixture(repo_factory, tmp_path)
    receipt = root / "promotions" / "receipts" / f"{name}.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_bytes(b"{}\n")
    run_git(root, "add", receipt.relative_to(root).as_posix())
    run_git(root, "commit", "-qm", "add receipt")
    gone = tmp_path / "gone"
    plan: dict[str, object] = {
        "schema_version": 1,
        "source_root": str(gone),
        "receipt_path": str(gone / "promotions" / "receipts" / f"{name}.json"),
    }
    assert promotion._relocated_v1_receipt(root, plan, name) == receipt
    return root, plan


def test_relocated_v1_receipt_rule_ignores_schema_2_plans(
    repo_factory, tmp_path: Path,
) -> None:
    name = "c4" * 12
    root, plan = _tracked_receipt_and_plan(repo_factory, tmp_path, name)
    plan["schema_version"] = 2

    assert promotion._relocated_v1_receipt(root, plan, name) is None


def test_relocated_v1_receipt_requires_the_blob_at_head_not_the_index(
    repo_factory, tmp_path: Path,
) -> None:
    name = "c6" * 12
    root, plan = _tracked_receipt_and_plan(repo_factory, tmp_path, name)
    relative = f"promotions/receipts/{name}.json"
    run_git(root, "rm", "-q", "--cached", relative)
    run_git(root, "commit", "-qm", "drop the receipt from HEAD")
    run_git(root, "add", relative)

    assert promotion._relocated_v1_receipt(root, plan, name) is None


def test_relocated_v1_receipt_refuses_a_linked_receipts_directory(
    repo_factory, tmp_path: Path,
) -> None:
    name = "c7" * 12
    root, plan = _tracked_receipt_and_plan(repo_factory, tmp_path, name)
    receipts = root / "promotions" / "receipts"
    real = root / "promotions" / "receipts-real"
    receipts.rename(real)
    if not try_dir_link(real, receipts):
        pytest.skip("cannot create a directory link here")

    assert promotion._relocated_v1_receipt(root, plan, name) is None


def test_v1_relocated_receipt_does_not_explain_targets_of_another_installation(
    repo_factory, tmp_path: Path,
) -> None:
    # Same backup root, receipt copied into HEAD, other target directories
    # holding the same bytes: the receipt is not about them.
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = paths["claude"] / "demo"
    digest = _set_test_target_state(target, "promoted\n")
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="c8" * 12, target_id="claude_user_skills",
        after_digest=digest, completed_at="2026-09-11T12:00:00+00:00",
    )
    moved = _remove_sealed_checkout(root, tmp_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    for target_id in ("claude_user_skills", "agents_user_skills", "obsidian_snapshots"):
        elsewhere = paths["targets"] / f"elsewhere-{target_id}"
        elsewhere.mkdir()
        config["targets"][target_id]["path"] = str(elsewhere)
    other_config = tmp_path / "other-local-targets.json"
    write_json(other_config, config)
    other_target = paths["targets"] / "elsewhere-claude_user_skills" / "demo"
    assert _set_test_target_state(other_target, "promoted\n") == digest

    report = check_promotion(moved, map_path, other_config, plan_path)

    mismatches = [
        item for item in report["findings"]
        if item["code"] == "PROMOTION-RECEIPT-JOURNAL-MISMATCH"
    ]
    assert [item["evidence"] for item in mismatches] == [
        "relocated-receipt-targets-outside-installation"
    ]
    assert not plan_path.exists()


def test_v1_relocated_receipt_does_not_explain_a_path_it_did_not_write(
    repo_factory, tmp_path: Path,
) -> None:
    # Same installation root, another concrete path: the sealed write went to
    # claude/renamed-demo, this check writes claude/demo.
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    sealed_target = paths["claude"] / "renamed-demo"
    digest = _set_test_target_state(sealed_target, "promoted\n")
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=sealed_target,
        name="cc" * 12, target_id="claude_user_skills",
        after_digest=digest, completed_at="2026-09-11T12:00:00+00:00",
    )
    moved = _remove_sealed_checkout(root, tmp_path)
    assert _set_test_target_state(paths["claude"] / "demo", "promoted\n") == digest

    report = check_promotion(moved, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-JOURNAL-MISMATCH" not in codes(report)
    unexplained = [
        str(item["evidence"]) for item in report["findings"]
        if item["code"] == "PROMOTION-TARGET-UNEXPLAINED"
    ]
    assert len(unexplained) == 1 and unexplained[0].startswith("target=claude_user_skills ")
    assert not plan_path.exists()


def test_relocated_v1_receipt_refuses_an_unreadable_sealed_path(
    repo_factory, tmp_path: Path, monkeypatch,
) -> None:
    # Present but unreadable is not gone (Path.exists() answers False here).
    name = "cd" * 12
    root, plan = _tracked_receipt_and_plan(repo_factory, tmp_path, name)
    sealed = os.path.normcase(str(plan["receipt_path"]))
    real_lstat = os.lstat

    def lstat(path, *args, **kwargs):
        if os.path.normcase(os.fspath(path)) == sealed:
            raise PermissionError(13, "Access is denied", os.fspath(path))
        return real_lstat(path, *args, **kwargs)

    monkeypatch.setattr(promotion.os, "lstat", lstat)

    assert promotion._relocated_v1_receipt(root, plan, name) is None


def test_relocated_v1_receipt_compares_raw_head_bytes_not_filtered_ones(
    repo_factory, tmp_path: Path,
) -> None:
    # A clean filter stores E in HEAD while the file on disk keeps D: hashes
    # taken through the filter would agree, the raw blob does not.
    root, _, _, _, _ = promotion_fixture(repo_factory, tmp_path)
    flip = tmp_path / "flip.py"
    flip.write_text(
        "import sys\n"
        "data = sys.stdin.buffer.read()\n"
        "a, b = b'\"schema_version\":1', b'\"schema_version\":9'\n"
        "sys.stdout.buffer.write(data.replace(a, b) if sys.argv[1] == 'clean' else data.replace(b, a))\n",
        encoding="utf-8",
    )
    command = f'"{Path(sys.executable).as_posix()}" "{flip.as_posix()}"'
    run_git(root, "config", "filter.flip.clean", f"{command} clean")
    run_git(root, "config", "filter.flip.smudge", f"{command} smudge")
    attributes = root / ".git" / "info" / "attributes"
    attributes.parent.mkdir(parents=True, exist_ok=True)
    attributes.write_text("promotions/receipts/*.json filter=flip\n", encoding="utf-8")
    name = "ce" * 12
    relative = f"promotions/receipts/{name}.json"
    receipt = root / relative
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_bytes(b'{"schema_version":1}\n')
    run_git(root, "add", relative)
    run_git(root, "commit", "-qm", "add a filtered receipt")
    head_blob = subprocess.run(
        ["git", "cat-file", "blob", f"HEAD:{relative}"],
        cwd=root, capture_output=True, check=True,
    ).stdout
    assert head_blob == b'{"schema_version":9}\n'
    assert receipt.read_bytes() == b'{"schema_version":1}\n'
    gone = tmp_path / "gone"
    plan = {
        "schema_version": 1,
        "source_root": str(gone),
        "receipt_path": str(gone / "promotions" / "receipts" / f"{name}.json"),
    }

    assert promotion._relocated_v1_receipt(root, plan, name) is None


def test_v1_receipt_is_not_relocated_while_its_sealed_path_exists(
    repo_factory, tmp_path: Path,
) -> None:
    # Check and journal sweep pick the same copy: the sealed one, if present.
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    target = paths["claude"] / "demo"
    digest = _set_test_target_state(target, "promoted\n")
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="c9" * 12, target_id="claude_user_skills",
        after_digest=digest, completed_at="2026-09-11T12:00:00+00:00",
    )
    copy = tmp_path / "second-checkout"
    shutil.copytree(root, copy)

    report = check_promotion(copy, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-JOURNAL-MISMATCH" in codes(report)
    assert not plan_path.exists()
    promotion._scan_transactions(paths["backups"], live_root=copy)


def test_v1_relocated_receipt_needs_no_ancestry(
    repo_factory, tmp_path: Path,
) -> None:
    # The real receipts name commits of squash-merged branches.
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    branch = run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    run_git(root, "checkout", "-q", "-b", "squashed-away")
    run_git(root, "commit", "-q", "--allow-empty", "-m", "branch work")
    side_commit = run_git(root, "rev-parse", "HEAD")
    run_git(root, "checkout", "-q", branch)
    target = paths["claude"] / "demo"
    digest = _set_test_target_state(target, "promoted\n")
    commit_test_receipt(
        root, backup_root=paths["backups"], target_path=target,
        name="ca" * 12, target_id="claude_user_skills",
        after_digest=digest, completed_at="2026-09-11T12:00:00+00:00",
        source_commit=side_commit,
    )
    moved = _remove_sealed_checkout(root, tmp_path)
    assert not promotion._git_is_ancestor(moved, side_commit)

    report = check_promotion(moved, map_path, config_path, plan_path)

    assert "PROMOTION-RECEIPT-JOURNAL-MISMATCH" not in codes(report)
    assert "PROMOTION-RECEIPT-COMMIT-NOT-ANCESTOR" not in codes(report)
    assert plan_path.is_file()


def test_bootstrap_duplicate_installation_id_fails_closed(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    check_promotion(root, map_path, config_path, plan_path, bootstrap=True)
    applied = apply_promotion(plan_path)
    commit_published_receipt(root, applied, "genesis")
    second_plan = tmp_path / "second-plan.json"
    claude_before = tree_digest(paths["claude"] / "demo")
    backups = backup_entries(paths)

    report = check_promotion(
        root, map_path, config_path, second_plan, bootstrap=True,
    )

    assert "PROMOTION-INSTALLATION-EXISTS" in codes(report)
    assert not second_plan.exists()
    assert tree_digest(paths["claude"] / "demo") == claude_before
    assert backup_entries(paths) == backups


def test_bootstrap_nonempty_destination_fails_closed(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    seed_installed_demo(root, paths["claude"] / "demo")
    backups = backup_entries(paths)

    report = check_promotion(
        root, map_path, config_path, plan_path, bootstrap=True,
    )

    assert "PROMOTION-TARGET-NONEMPTY" in codes(report)
    _assert_untouched(plan_path, paths, backups=backups, claude_demo=True)


def test_bootstrap_zero_byte_file_on_tree_destination_fails_closed(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    demo = paths["claude"] / "demo"
    demo.write_text("", encoding="utf-8")
    backups = backup_entries(paths)

    report = check_promotion(
        root, map_path, config_path, plan_path, bootstrap=True,
    )

    assert "PROMOTION-TARGET-TYPE-MISMATCH" in codes(report)
    assert not plan_path.exists()
    assert demo.is_file()
    assert list(paths["backups"].rglob("*")) == backups


def test_bootstrap_empty_dir_on_file_destination_fails_closed(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    add_file_route(root, map_path)
    commit = run_git(root, "rev-parse", "HEAD")
    file_dest = paths["vault"] / "fixture-file" / commit
    file_dest.mkdir(parents=True)
    backups = backup_entries(paths)

    report = check_promotion(
        root, map_path, config_path, plan_path, bootstrap=True,
    )

    assert "PROMOTION-TARGET-TYPE-MISMATCH" in codes(report)
    assert not plan_path.exists()
    assert file_dest.is_dir()
    assert list(paths["backups"].rglob("*")) == backups


def test_bootstrap_backup_residue_fails_closed(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    residue = paths["backups"] / "residue.txt"
    residue.write_text("keep\n", encoding="utf-8")

    report = check_promotion(
        root, map_path, config_path, plan_path, bootstrap=True,
    )

    assert "PROMOTION-BACKUP-NONEMPTY" in codes(report)
    assert not plan_path.exists()
    assert residue.read_text(encoding="utf-8") == "keep\n"
    assert not (paths["claude"] / "demo").exists()


def test_bootstrap_partial_map_fails_closed(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    write_json(map_path, {"schema_version": 1, "artifacts": []})
    backups = backup_entries(paths)

    report = check_promotion(
        root, map_path, config_path, plan_path, bootstrap=True,
    )

    assert "PROMOTION-UNROUTED" in codes(report)
    _assert_untouched(plan_path, paths, backups=backups)


def test_bootstrap_dirty_source_fails_closed(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    (root / "skills/demo/SKILL.md").write_text("dirty\n", encoding="utf-8")
    backups = backup_entries(paths)

    report = check_promotion(
        root, map_path, config_path, plan_path, bootstrap=True,
    )

    assert "PROMOTION-DIRTY" in codes(report)
    _assert_untouched(plan_path, paths, backups=backups)


def test_bootstrap_source_change_after_check_fails_without_writes(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    check_promotion(root, map_path, config_path, plan_path, bootstrap=True)
    (root / "skills/demo/SKILL.md").write_text("changed\n", encoding="utf-8")
    backups = backup_entries(paths)

    report = apply_promotion(plan_path)

    assert "PROMOTION-SOURCE-CHANGED" in codes(report)
    assert not (paths["claude"] / "demo").exists()
    assert list(paths["backups"].rglob("*")) == backups


def test_bootstrap_contract_change_after_check_fails_without_writes(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    check_promotion(root, map_path, config_path, plan_path, bootstrap=True)
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
        newline="\n",
    )
    backups = backup_entries(paths)

    report = apply_promotion(plan_path)

    assert codes(report) == ["PROMOTION-CONTRACT-CHANGED"]
    assert not (paths["claude"] / "demo").exists()
    assert list(paths["backups"].rglob("*")) == backups


def test_bootstrap_escape_and_forbidden_fail_closed(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    outside = tmp_path / "outside"
    outside.mkdir()
    config["targets"]["agents_user_skills"]["path"] = str(outside)
    write_json(config_path, config)
    backups = backup_entries(paths)

    escaped = check_promotion(
        root, map_path, config_path, plan_path, bootstrap=True,
    )

    assert "PROMOTION-TARGET-ESCAPE" in codes(escaped)
    assert not plan_path.exists()
    plugin = paths["targets"] / "plugins"
    plugin.mkdir()
    config["targets"]["agents_user_skills"]["path"] = str(plugin)
    write_json(config_path, config)

    forbidden = check_promotion(
        root, map_path, config_path, plan_path, bootstrap=True,
    )

    assert "PROMOTION-TARGET-FORBIDDEN" in codes(forbidden)
    assert not plan_path.exists()
    assert list(paths["backups"].rglob("*")) == backups
    assert not (paths["claude"] / "demo").exists()


def test_bootstrap_parent_link_fails_closed(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    elsewhere = paths["targets"] / "elsewhere"
    elsewhere.mkdir()
    parent = paths["vault"] / "fixture"
    if not try_dir_link(elsewhere, parent):
        pytest.skip("directory symlink/junction unavailable")
    backups = backup_entries(paths)

    report = check_promotion(
        root, map_path, config_path, plan_path, bootstrap=True,
    )

    assert "PROMOTION-TARGET-LINKED" in codes(report)
    assert not plan_path.exists()
    assert list(paths["backups"].rglob("*")) == backups
    assert not (paths["claude"] / "demo").exists()


def test_bootstrap_backup_link_fails_closed(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    linked = paths["targets"] / "backup-link"
    if not try_dir_link(paths["backups"], linked):
        pytest.skip("directory symlink/junction unavailable")
    write_v2_config(config_path, INSTALLATION_A)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["backup_root"] = str(linked)
    write_json(config_path, config)

    report = check_promotion(
        root, map_path, config_path, plan_path, bootstrap=True,
    )

    assert "PROMOTION-BACKUP-LINKED" in codes(report)
    assert not plan_path.exists()
    assert not (paths["claude"] / "demo").exists()


def test_v2_foreign_receipt_does_not_authorize_preimage(
    repo_factory, tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    write_v2_config(config_path, INSTALLATION_A)
    target = seed_installed_demo(root, paths["claude"] / "demo")
    commit_test_receipt(
        root,
        backup_root=paths["backups"],
        target_path=target,
        name="af" * 12,
        target_id="claude_user_skills",
        after_digest=tree_digest(target),
        completed_at="2026-09-11T13:00:00+00:00",
        seal_journal=False,
        schema_version=2,
        installation_id=INSTALLATION_B,
        bootstrap=True,
    )
    backups = backup_entries(paths)

    report = check_promotion(
        root, map_path, config_path, plan_path, bootstrap=True,
    )

    assert "PROMOTION-TARGET-NONEMPTY" in codes(report)
    assert "PROMOTION-INSTALLATION-UNINITIALIZED" not in codes(report)
    assert not plan_path.exists()
    assert target.is_dir()
    assert backup_entries(paths) == backups


def test_example_local_targets_declares_v2_installation_id() -> None:
    root = Path(__file__).resolve().parents[2]
    example = json.loads(
        (root / "promotions/local-targets.example.json").read_text(
            encoding="utf-8"
        )
    )
    assert example["schema_version"] == 2
    assert promotion._is_canonical_uuid_v4(example["installation_id"])


@pytest.mark.parametrize("schema", [1, 2])
def test_target_parent_binding_inside_allowed_fails_closed(
    repo_factory,
    tmp_path: Path,
    schema: int,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    allowed = paths["targets"]
    real = allowed / "real"
    move_fixture_dirs(paths, real)
    binding = allowed / "binding"
    if not try_dir_link(real, binding):
        pytest.skip("directory symlink/junction unavailable")
    rewrite_local_targets(config_path, allowed=allowed, dest_root=binding)
    if schema == 2:
        write_v2_config(config_path, INSTALLATION_A)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    logical_target = Path(str(config["targets"]["claude_user_skills"]["path"]))
    backups = list(Path(str(config["backup_root"])).rglob("*"))

    *_, findings = promotion._target_config_findings(config)

    assert promotion._path_is_link(logical_target.parent) is True
    assert "PROMOTION-TARGET-LINKED" in [str(item["code"]) for item in findings]
    report = check_promotion(
        root,
        map_path,
        config_path,
        plan_path,
        bootstrap=schema == 2,
    )
    assert "PROMOTION-TARGET-LINKED" in codes(report)
    assert not plan_path.exists()
    assert list(Path(str(config["backup_root"])).rglob("*")) == backups
    assert not (logical_target / "demo").exists()


def test_parent_binding_inserted_after_check_fails_apply_without_writes(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    outer = paths["targets"]
    mid = outer / "mid"
    move_fixture_dirs(paths, mid)
    rewrite_local_targets(config_path, allowed=outer, dest_root=mid)
    write_v2_config(config_path, INSTALLATION_A)
    check_promotion(root, map_path, config_path, plan_path, bootstrap=True)
    real = outer / "real"
    shutil.move(str(mid), str(real))
    if not try_dir_link(real, mid):
        pytest.skip("directory symlink/junction unavailable")
    backups = list((real / "backups").rglob("*"))

    report = apply_promotion(plan_path)

    assert "PROMOTION-TARGET-LINKED" in codes(report)
    assert not (real / "claude" / "demo").exists()
    assert not (mid / "claude" / "demo").exists()
    assert list((real / "backups").rglob("*")) == backups


@pytest.mark.parametrize("schema", [1, 2])
def test_shared_physical_dest_lock_blocks_inner_allowlist_apply(
    repo_factory,
    tmp_path: Path,
    schema: int,
) -> None:
    root, map_path, config_a, plan_a_path, paths = promotion_fixture(
        repo_factory, tmp_path,
    )
    outer = paths["targets"]
    inner = outer / "inner"
    move_fixture_dirs(paths, inner)
    rewrite_local_targets(config_a, allowed=outer, dest_root=inner)
    if schema == 2:
        write_v2_config(config_a, INSTALLATION_A)
    config_b = tmp_path / "local-targets-inner.json"
    inner_config = json.loads(config_a.read_text(encoding="utf-8"))
    inner_config["allowed_physical_roots"] = [str(inner)]
    inner_config["forbidden_physical_roots"] = [str(inner / "plugins")]
    if schema == 2:
        inner_config["installation_id"] = INSTALLATION_B
    write_json(config_b, inner_config)
    plan_b_path = tmp_path / "plan-inner.json"
    check_a = check_promotion(
        root,
        map_path,
        config_a,
        plan_a_path,
        bootstrap=schema == 2,
    )
    check_b = check_promotion(
        root,
        map_path,
        config_b,
        plan_b_path,
        bootstrap=schema == 2,
    )
    assert check_a["verdict"] in {"PASS", "WARN"}
    assert check_b["verdict"] in {"PASS", "WARN"}
    assert plan_a_path.is_file()
    assert plan_b_path.is_file()
    plan_a = json.loads(plan_a_path.read_text(encoding="utf-8"))
    plan_b = json.loads(plan_b_path.read_text(encoding="utf-8"))
    shared = lock_paths_for_plan(plan_a) & lock_paths_for_plan(plan_b)
    assert shared
    backups = backup_entries(paths)

    with promotion._RootLocks(promotion._lock_roots_for_plan(plan_a)):
        applied = run_promote_process(
            root,
            "--apply",
            "--plan",
            str(plan_b_path),
        )

    report = json.loads(
        plan_b_path.with_suffix(".apply-report.json").read_text(encoding="utf-8")
    )
    assert applied.returncode == 2
    assert "PROMOTION-LOCK-ACTIVE" in codes(report)
    assert not (paths["claude"] / "demo").exists()
    assert backup_entries(paths) == backups


def test_disjoint_physical_dests_keep_independent_locks(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_a, plan_a_path, paths_a = promotion_fixture(
        repo_factory, tmp_path,
    )
    other = tmp_path / "other-targets"
    claude_b = other / "claude"
    agents_b = other / "agents"
    vault_b = other / "vault"
    backups_b = other / "backups"
    for path in (claude_b, agents_b, vault_b, backups_b):
        path.mkdir(parents=True, exist_ok=True)
    config_b = tmp_path / "local-targets-other.json"
    other_config = json.loads(config_a.read_text(encoding="utf-8"))
    other_config["allowed_physical_roots"] = [str(other)]
    other_config["forbidden_physical_roots"] = [str(other / "plugins")]
    other_config["backup_root"] = str(backups_b)
    other_config["targets"]["claude_user_skills"]["path"] = str(claude_b)
    other_config["targets"]["agents_user_skills"]["path"] = str(agents_b)
    other_config["targets"]["obsidian_snapshots"]["path"] = str(vault_b)
    write_json(config_b, other_config)
    plan_b_path = tmp_path / "plan-other.json"
    check_promotion(root, map_path, config_a, plan_a_path)
    check_promotion(root, map_path, config_b, plan_b_path)
    plan_a = json.loads(plan_a_path.read_text(encoding="utf-8"))
    plan_b = json.loads(plan_b_path.read_text(encoding="utf-8"))

    assert not (lock_paths_for_plan(plan_a) & lock_paths_for_plan(plan_b))

    with promotion._RootLocks(promotion._lock_roots_for_plan(plan_a)):
        report = apply_promotion(plan_b_path)

    assert report["verdict"] == "PASS"
    assert (claude_b / "demo" / "SKILL.md").is_file()
    assert not (paths_a["claude"] / "demo").exists()


def test_ensure_known_residue_rejects_root_junction_with_allowed_digest(
    tmp_path: Path,
) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (real / "payload.txt").write_text("payload\n", encoding="utf-8")
    residue = tmp_path / "residue-root"
    assert try_dir_link(real, residue) is True
    allowed = tree_digest(real)
    assert tree_digest(residue) == allowed
    assert promotion._path_is_link(residue) is True
    try:
        with pytest.raises(promotion._PromotionIntegrityError) as caught:
            promotion._ensure_known_residue(residue, {allowed}, "old")
        assert caught.value.code == "PROMOTION-FOREIGN-TARGET"
    finally:
        if residue.is_symlink():
            residue.unlink()
        elif promotion._is_junction(residue):
            os.rmdir(residue)


@pytest.mark.skipif(os.name != "nt", reason="directory junctions are a Windows feature")
def test_ensure_known_residue_rejects_a_broken_junction(tmp_path: Path) -> None:
    # Codex review of #120, J1: once its target is gone, exists() follows the
    # junction and is_symlink() does not see it, so the residue read as absent.
    real = tmp_path / "real"
    real.mkdir()
    residue = tmp_path / "residue-root"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(residue), str(real)],
        capture_output=True,
    )
    assert result.returncode == 0
    try:
        real.rmdir()
        assert residue.exists() is False
        assert residue.is_symlink() is False
        with pytest.raises(promotion._PromotionIntegrityError) as caught:
            promotion._ensure_known_residue(residue, {"absent"}, "old")
        assert caught.value.code == "PROMOTION-FOREIGN-TARGET"
    finally:
        if os.path.lexists(residue):
            os.rmdir(residue)


@pytest.mark.skipif(os.name != "nt", reason="directory junctions are a Windows feature")
def test_remove_artifact_removes_a_broken_junction(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    junction = tmp_path / "junction"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(real)],
        capture_output=True,
    )
    assert result.returncode == 0
    try:
        real.rmdir()
        promotion._remove_artifact(junction)
        assert os.path.lexists(junction) is False
    finally:
        if os.path.lexists(junction):
            os.rmdir(junction)


@pytest.mark.skipif(os.name != "nt", reason="directory junctions are a Windows feature")
def test_remove_artifact_removes_a_junction_and_keeps_its_target(
    tmp_path: Path,
) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (real / "payload.txt").write_text("payload\n", encoding="utf-8")
    junction = tmp_path / "junction"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(real)],
        capture_output=True,
    )
    assert result.returncode == 0
    try:
        promotion._remove_artifact(junction)
        assert os.path.lexists(junction) is False
        assert (real / "payload.txt").read_text(encoding="utf-8") == "payload\n"
    finally:
        if os.path.lexists(junction):
            os.rmdir(junction)


def test_apply_keeps_a_link_planted_in_its_own_partial_stage(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    # Codex review of #120, J4: the rollback removed the stages this apply
    # had made without looking inside, so a link planted in one went too.
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    real = tmp_path / "real"
    real.mkdir()
    (real / "payload.txt").write_text("payload\n", encoding="utf-8")
    created_stage: Path | None = None

    def plant_a_link_and_fail(
        source,
        destination,
        kind,
        source_files=None,
        **_kwargs,
    ):
        nonlocal created_stage
        created_stage = Path(destination)
        created_stage.mkdir(parents=True)
        assert try_dir_link(real, created_stage / "linked") is True
        raise OSError("copy fault")

    monkeypatch.setattr("packctl.promotion._copy_artifact", plant_a_link_and_fail)
    try:
        report = apply_promotion(plan_path)

        assert created_stage is not None
        assert [
            item["evidence"]
            for item in report["findings"]
            if item["code"] == "PROMOTION-ROLLBACK-FAILED"
        ] == [f"{plan['operations'][0]['physical_alias']}:{created_stage.name}"]
        assert promotion._path_is_link(created_stage / "linked") is True
        assert (real / "payload.txt").read_text(encoding="utf-8") == "payload\n"
        assert journal_events(transaction_root(plan))[-1]["event_type"] != "ABORT"
    finally:
        if created_stage is not None:
            link = created_stage / "linked"
            if link.is_symlink():
                link.unlink()
            elif promotion._is_junction(link):
                os.rmdir(link)


@pytest.mark.skipif(os.name != "nt", reason="directory junctions are a Windows feature")
def test_apply_refuses_a_broken_junction_at_a_stage_and_keeps_it(
    repo_factory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Codex review of #120, J4: a junction whose target was gone passed the
    # residue check, so its stage counted as one this apply made; once the
    # target was back, the rollback unlinked the junction and wrote ABORT.
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    operation = plan["operations"][0]
    stage = promotion._operation_paths(operation, str(plan["transaction_id"]))[0]
    stage.parent.mkdir(parents=True, exist_ok=True)
    real = tmp_path / "real"
    real.mkdir()
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(stage), str(real)],
        capture_output=True,
    )
    assert result.returncode == 0
    rollback = promotion._rollback_to_pre

    def rollback_once_the_target_is_back(*args, **kwargs):
        real.mkdir()
        return rollback(*args, **kwargs)

    monkeypatch.setattr(
        promotion, "_rollback_to_pre", rollback_once_the_target_is_back
    )
    try:
        real.rmdir()

        report = apply_promotion(plan_path)

        assert [
            (item["code"], item["evidence"]) for item in report["findings"]
        ] == [
            ("PROMOTION-APPLY-FAILED", "RuntimeError"),
            (
                "PROMOTION-ROLLBACK-FAILED",
                f"{operation['physical_alias']}:{stage.name}",
            ),
        ]
        assert promotion._is_junction(stage) is True
        assert journal_events(transaction_root(plan))[-1]["event_type"] != "ABORT"
    finally:
        if os.path.lexists(stage):
            os.rmdir(stage)


@pytest.mark.skipif(os.name != "nt", reason="directory junctions are a Windows feature")
def test_recovery_refuses_a_broken_junction_at_a_ready_stage(
    repo_factory,
    tmp_path: Path,
) -> None:
    # Codex review of #120, J3: after STAGE_READY, a stage swapped for a
    # junction whose target is gone read as absent, and the recovery wrote
    # ABORT and kept it.
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": "after_stage:0"},
    )
    assert killed.returncode == 97
    stage = promotion._operation_paths(
        plan["operations"][0], str(plan["transaction_id"])
    )[0]
    shutil.rmtree(stage)
    real = tmp_path / "real"
    real.mkdir()
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(stage), str(real)],
        capture_output=True,
    )
    assert result.returncode == 0
    try:
        real.rmdir()
        transaction = transaction_root(plan)

        report = promotion.recover_promotion(transaction)

        assert codes(report) == ["PROMOTION-FOREIGN-TARGET"]
        assert promotion._is_junction(stage) is True
        assert journal_events(transaction)[-1]["event_type"] != "ABORT"
    finally:
        if os.path.lexists(stage):
            os.rmdir(stage)


@pytest.mark.skipif(os.name != "nt", reason="directory junctions are a Windows feature")
def test_is_junction_reads_the_reparse_tag_without_path_is_junction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # fb-20261018-012600-cdc5: Path.is_junction is new in Python 3.12, and
    # without it every link check of the promotion took a junction for a
    # plain directory.
    real = tmp_path / "real"
    real.mkdir()
    junction = tmp_path / "junction"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(real)],
        capture_output=True,
    )
    assert result.returncode == 0
    monkeypatch.setattr(Path, "is_junction", None, raising=False)
    try:
        assert promotion._is_junction(junction) is True
        assert promotion._path_is_link(junction) is True
        assert promotion._is_junction(real) is False
        assert promotion._is_junction(tmp_path / "missing") is False
    finally:
        os.rmdir(junction)


@pytest.mark.skipif(os.name != "nt", reason="directory junctions are a Windows feature")
def test_is_junction_without_path_is_junction_reads_only_the_mount_point_tag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Codex review of #120, J2: cloud placeholders, symlinks and app execution
    # aliases carry reparse tags too, and only the mount point tag is a
    # junction.
    monkeypatch.setattr(Path, "is_junction", None, raising=False)
    for tag, expected in (
        (0xA0000003, True),
        (0x9000A01A, False),
        (0xA000000C, False),
        (0x8000001B, False),
        (0, False),
    ):
        fake_os = types.SimpleNamespace(
            name="nt",
            lstat=lambda path, tag=tag: types.SimpleNamespace(st_reparse_tag=tag),
        )
        monkeypatch.setattr(promotion, "os", fake_os)
        assert promotion._is_junction(tmp_path) is expected, hex(tag)
