from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pytest

from persistence_sidecar import MigrationReader


@dataclass(frozen=True)
class MatrixCase:
    name: str
    payload: bytes
    reader_version: int
    verdict: str
    bytes_consumed: int
    state_preserved: str
    action: str
    mutation_index: int
    mutation_value: int


CASES = (
    MatrixCase(
        "fresh",
        b"FRESH",
        2,
        "ok",
        0,
        "defaults",
        "write current header",
        0,
        ord("X"),
    ),
    MatrixCase(
        "legacy-no-header",
        b"LEGACY:old-state",
        2,
        "ok_legacy",
        16,
        "fully migrated",
        "read legacy, write new after backup",
        0,
        ord("X"),
    ),
    MatrixCase(
        "known-version",
        b"SCAR\x02\x01\x00\x00\x00\x81\x00\x03new",
        2,
        "ok",
        15,
        "complete",
        "none",
        4,
        3,
    ),
    MatrixCase(
        "future-version",
        b"SCAR\x03\x01\x00\x00\x00\x81\x00\x03new",
        2,
        "reject",
        0,
        "intact",
        "do not write; log rate-limited",
        4,
        2,
    ),
    MatrixCase(
        "truncated",
        b"SCAR\x02\x01\x00\x00\x00\x81\x00\x04cut",
        2,
        "reject",
        0,
        "intact",
        "discard partial; preserve evidence",
        11,
        3,
    ),
    MatrixCase(
        "same-dayz-build-new-mod-version",
        b"SCAR\x01\x01\x00\x00\x00\x81\x00\x03old",
        2,
        "ok_migrate",
        15,
        "migrated",
        "migrate by mod version, not game build",
        4,
        2,
    ),
    MatrixCase(
        "rollback-old-reader",
        b"SCAR\x02\x02\x00\x00\x00\x81\x00\x03new",
        1,
        "reject_forward",
        0,
        "intact",
        "old reader rejects; do not delete",
        5,
        1,
    ),
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_migration_matrix_has_all_four_normative_columns(case: MatrixCase) -> None:
    reader = MigrationReader(current_version=case.reader_version)

    result = reader.read(case.payload, window="matrix")

    assert result.verdict == case.verdict
    assert result.bytes_consumed == case.bytes_consumed
    assert result.state_preserved == case.state_preserved
    assert result.action == case.action


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_one_byte_mutation_changes_every_cell_verdict(case: MatrixCase) -> None:
    reader = MigrationReader(current_version=case.reader_version)
    original = reader.read(case.payload, window="original").verdict
    mutated = bytearray(case.payload)
    mutated[case.mutation_index] = case.mutation_value

    changed = MigrationReader(current_version=case.reader_version).read(
        bytes(mutated),
        window="mutated",
    )

    assert changed.verdict != original


def test_future_version_is_read_only_and_logs_once_per_window() -> None:
    payload = CASES[3].payload
    before = hashlib.sha256(payload).hexdigest()
    reader = MigrationReader(current_version=2)

    first = reader.read(payload, window="startup")
    second = reader.read(payload, window="startup")

    assert first.verdict == "reject"
    assert second.verdict == "reject"
    assert hashlib.sha256(payload).hexdigest() == before
    assert reader.logs == ["degradation: future mod version rejected"]


def test_truncated_record_discards_all_partial_state() -> None:
    reader = MigrationReader(
        current_version=2,
        initial_state={"value": "preserved"},
    )

    result = reader.read(CASES[4].payload, window="startup")

    assert result.verdict != "ok"
    assert result.applied_state is None
    assert reader.state == {"value": "preserved"}
