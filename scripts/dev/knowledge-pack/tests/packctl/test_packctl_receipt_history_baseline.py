from __future__ import annotations

import json
import shutil
from collections import defaultdict
from pathlib import Path

from packctl.common import canonical_json_bytes, sha256_bytes
import packctl.promotion as promotion


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "receipt_history"
RECEIPT_NAMES = (
    "c7b5366cc761a8038e52f6a2.json",
    "51a7024ef9a5e333e5fab7b8.json",
    "e2aa6cf9058070bb4fbf2a8c.json",
)


def _append_fixture_event(
    transaction_root: Path,
    events: list[dict[str, object]],
    event_type: str,
    payload: dict[str, object],
) -> None:
    material: dict[str, object] = {
        "schema_version": 1,
        "sequence": len(events),
        "transaction_id": transaction_root.name,
        "event_type": event_type,
        "previous_event_hash": (
            str(events[-1]["event_hash"]) if events else "0" * 64
        ),
        "payload": payload,
    }
    event = dict(material)
    event["event_hash"] = sha256_bytes(canonical_json_bytes(material))
    event_path = transaction_root / "events" / f"{len(events):08d}.json"
    event_path.write_bytes(canonical_json_bytes(event))
    events.append(event)


def _sealed_fixture_plan(
    repo_root: Path,
    backup_root: Path,
    allowed_root: Path,
    receipt_path: Path,
) -> dict[str, object]:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    transaction_id = str(receipt["transaction_id"])
    target_root = allowed_root / "targets" / transaction_id
    operations: list[dict[str, object]] = []
    for operation in receipt["operations"]:
        target = target_root / str(operation["physical_alias"])
        logical_target_ids = list(operation["logical_target_ids"])
        operations.append(
            {
                "artifact_id": operation["artifact_id"],
                "artifact_kind": "tree",
                "source_path": str(repo_root / "fixture-source"),
                "source_files": [],
                "target_path": str(target),
                "logical_target_ids": logical_target_ids,
                "logical_target_paths": {
                    target_id: str(target) for target_id in logical_target_ids
                },
                "before_digest": operation["before_digest"],
                "after_digest": operation["after_digest"],
                "target_role": "fixture",
                "physical_alias": operation["physical_alias"],
            }
        )
    assert len({item["physical_alias"] for item in operations}) == len(operations)
    plan: dict[str, object] = {
        "schema_version": 1,
        "transaction_id": transaction_id,
        "source_root": str(repo_root.resolve()),
        "source_commit": receipt["source_commit"],
        "promotion_map_path": str(repo_root / "promotions/promotion-map.json"),
        "promotion_map_hash": "0" * 64,
        "local_targets_path": str(repo_root / "promotions/local-targets.json"),
        "local_targets_hash": "0" * 64,
        "backup_root": str(backup_root.resolve()),
        "allowed_physical_roots": [str(allowed_root.resolve())],
        "forbidden_physical_roots": [],
        "receipt_path": str(receipt_path.resolve()),
        "artifact_ids": receipt["artifact_ids"],
        "target_ids": receipt["target_ids"],
        "operations": operations,
    }
    plan["plan_digest"] = promotion._plan_digest(plan)
    transaction_root = backup_root / transaction_id
    (transaction_root / "events").mkdir(parents=True)
    (transaction_root / "plan.json").write_bytes(canonical_json_bytes(plan))

    events: list[dict[str, object]] = []
    _append_fixture_event(
        transaction_root,
        events,
        "PENDING",
        {"plan_digest": plan["plan_digest"]},
    )
    for operation in operations:
        if operation["before_digest"] == operation["after_digest"]:
            continue
        alias = str(operation["physical_alias"])
        _append_fixture_event(
            transaction_root,
            events,
            "STAGE_READY",
            {"physical_alias": alias, "after_digest": operation["after_digest"]},
        )
        _append_fixture_event(
            transaction_root,
            events,
            "BACKUP_READY",
            {
                "physical_alias": alias,
                "before_digest": operation["before_digest"],
                "existed": operation["before_digest"] != "absent",
            },
        )
        _append_fixture_event(
            transaction_root,
            events,
            "TARGET_PUBLISHED",
            {"physical_alias": alias, "after_digest": operation["after_digest"]},
        )
    _append_fixture_event(
        transaction_root,
        events,
        "POST_VERIFIED",
        {
            "operation_count": len(operations),
            "logical_target_count": len(plan["target_ids"]),
        },
    )
    _append_fixture_event(
        transaction_root,
        events,
        "COMMIT",
        {
            "completed_at": receipt["completed_at"],
            "receipt_hash": sha256_bytes(receipt_path.read_bytes()),
        },
    )
    return plan


def _copy_sealed_receipts(tmp_path: Path) -> tuple[Path, Path]:
    repo_root = tmp_path / "repo"
    receipts_root = repo_root / "promotions" / "receipts"
    receipts_root.mkdir(parents=True)
    for name in RECEIPT_NAMES:
        shutil.copyfile(FIXTURE_ROOT / name, receipts_root / name)
    allowed_root = tmp_path / "managed"
    backup_root = allowed_root / "backups"
    backup_root.mkdir(parents=True)
    for receipt_path in receipts_root.glob("*.json"):
        _sealed_fixture_plan(repo_root, backup_root, allowed_root, receipt_path)
    return repo_root, backup_root

def _fixture_adjudications() -> dict[tuple[str, str], str]:
    value = json.loads(
        (FIXTURE_ROOT / "adjudications.json").read_text(encoding="utf-8")
    )
    return {
        (str(item["artifact_id"]), str(item["target_id"])): str(
            item["observed_digest"]
        )
        for item in value["adjudications"]
    }


def _observed_digests(
    sealed_batches: list[
        tuple[
            str,
            str,
            list[tuple[tuple[str, str], str, str, str]],
        ]
    ],
) -> dict[tuple[str, str], str]:
    observed: dict[tuple[str, str], str] = {}
    for _, _, transitions in sorted(sealed_batches):
        for key, _, after_digest, _ in transitions:
            observed[key] = (
                "absent" if key[1] == "obsidian_snapshots" else after_digest
            )
    return observed


def _measure_receipt_history(
    tmp_path: Path,
    adjudications: dict[tuple[str, str], str],
) -> dict[str, int]:
    repo_root, backup_root = _copy_sealed_receipts(tmp_path)
    sealed_batches: list[
        tuple[
            str,
            str,
            list[tuple[tuple[str, str], str, str, str]],
        ]
    ] = []
    receipts_root = repo_root / "promotions" / "receipts"
    for receipt_path in receipts_root.glob("*.json"):
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert promotion._receipt_contract_is_canonical(receipt_path, receipt)
        transitions, issue_code, issue_evidence = (
            promotion._sealed_receipt_transitions(
                repo_root,
                backup_root,
                receipt_path,
                receipt,
            )
        )
        assert issue_code is None, issue_evidence
        sealed_batches.append(
            (
                str(receipt["completed_at"]),
                str(receipt["transaction_id"]),
                transitions,
            )
        )

    transitions_by_key: dict[
        tuple[str, str], list[tuple[str, str, str]]
    ] = defaultdict(list)
    for _, _, transitions in sorted(sealed_batches):
        for key, before_digest, after_digest, transaction_id in transitions:
            transitions_by_key[key].append(
                (before_digest, after_digest, transaction_id)
            )

    observed_digests = _observed_digests(sealed_batches)
    counts = {
        "sealed_pairs": len(transitions_by_key),
        "absent": 0,
        "resolved": 0,
        "broken": 0,
        "visible": 0,
        "masked": 0,
    }
    for key, transitions in transitions_by_key.items():
        if observed_digests[key] == "absent":
            counts["absent"] += 1
            continue
        _, issue_code, _ = promotion._causal_receipt_head(transitions)
        if issue_code is None:
            counts["resolved"] += 1
            continue
        counts["broken"] += 1
        if promotion._pairs_have_matching_adjudications(
            {key}, adjudications, observed_digests
        ):
            counts["masked"] += 1
        else:
            counts["visible"] += 1
    return counts

def test_real_receipt_history_baseline_is_hermetic(tmp_path: Path) -> None:
    counts = _measure_receipt_history(tmp_path, _fixture_adjudications())

    assert counts == {
        "sealed_pairs": 68,
        "absent": 38,
        "resolved": 30,
        "broken": 0,
        "visible": 0,
        "masked": 0,
    }



def test_noop_occurrence_remains_valid_after_later_transition() -> None:
    digest_a = "a" * 64
    digest_b = "b" * 64
    digest_c = "c" * 64
    transitions = [
        (digest_a, digest_b, "1" * 24),
        (digest_b, digest_b, "2" * 24),
        (digest_b, digest_c, "3" * 24),
    ]

    assert promotion._causal_receipt_head(transitions) == (
        digest_c,
        None,
        "",
    )



def test_return_to_prior_digest_is_a_new_occurrence() -> None:
    digest_a = "a" * 64
    digest_b = "b" * 64
    transitions = [
        (digest_a, digest_b, "1" * 24),
        (digest_b, digest_a, "2" * 24),
    ]

    assert promotion._causal_receipt_head(transitions) == (
        digest_a,
        None,
        "",
    )



def _healthy_in_memory_history() -> tuple[
    str,
    str,
    str,
    str,
    list[tuple[str, str, str]],
]:
    digest_a = "a" * 64
    digest_b = "b" * 64
    digest_c = "c" * 64
    transaction_id = "1" * 24
    return (
        digest_a,
        digest_b,
        digest_c,
        transaction_id,
        [(digest_a, digest_b, transaction_id)],
    )


def test_real_fork_in_one_transaction_still_fails_closed() -> None:
    digest_a, _, digest_c, transaction_id, healthy = (
        _healthy_in_memory_history()
    )
    transitions = healthy + [(digest_a, digest_c, transaction_id)]

    assert promotion._causal_receipt_head(transitions) == (
        None,
        "PROMOTION-RECEIPT-HISTORY-FORK",
        f"fork-at:{digest_a}",
    )


def test_multiple_preimages_in_one_transaction_still_fail_closed() -> None:
    _, digest_b, digest_c, transaction_id, healthy = (
        _healthy_in_memory_history()
    )
    transitions = healthy + [(digest_c, digest_b, transaction_id)]

    assert promotion._causal_receipt_head(transitions) == (
        None,
        "PROMOTION-RECEIPT-HISTORY-AMBIGUOUS",
        f"multiple-preimages:{digest_b}",
    )


def test_real_cycle_in_one_transaction_still_fails_closed() -> None:
    digest_a, digest_b, _, transaction_id, healthy = (
        _healthy_in_memory_history()
    )
    transitions = healthy + [(digest_b, digest_a, transaction_id)]

    head, issue_code, issue_evidence = promotion._causal_receipt_head(
        transitions
    )
    assert head is None
    assert issue_code == "PROMOTION-RECEIPT-HISTORY-CYCLE"
    assert issue_evidence in {
        f"cycle-at:{digest_a}",
        f"cycle-at:{digest_b}",
    }


def test_duplicate_transition_in_one_transaction_still_fails_closed() -> None:
    _, _, _, transaction_id, healthy = _healthy_in_memory_history()
    transitions = healthy + [healthy[0]]

    assert promotion._causal_receipt_head(transitions) == (
        None,
        "PROMOTION-RECEIPT-HISTORY-AMBIGUOUS",
        f"duplicate-transition:{transaction_id}",
    )



def test_real_receipt_history_resolves_without_adjudications(
    tmp_path: Path,
) -> None:
    counts = _measure_receipt_history(tmp_path, {})

    assert counts == {
        "sealed_pairs": 68,
        "absent": 38,
        "resolved": 30,
        "broken": 0,
        "visible": 0,
        "masked": 0,
    }
