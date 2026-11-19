from __future__ import annotations

from dataclasses import dataclass

import pytest

from persistence_checklist import (
    PersistenceFormatProposal,
    validate_persistence_format_proposal,
)


@dataclass(frozen=True)
class ChecklistCase:
    name: str
    proposal: PersistenceFormatProposal
    passed: bool
    missing: tuple[str, ...]


CASES = (
    ChecklistCase(
        "complete",
        PersistenceFormatProposal(
            legacy_read_behavior="Read version 1 records before migrating.",
            old_reader_new_data_behavior="The version 1 reader rejects version 2.",
            no_format_change_alternative="Keep the schema and derive the new value.",
            no_format_change_unavailable_reason=None,
            no_format_change_statement_position=1,
            format_change_statement_position=2,
        ),
        True,
        (),
    ),
    ChecklistCase(
        "missing-legacy",
        PersistenceFormatProposal(
            legacy_read_behavior=None,
            old_reader_new_data_behavior="The version 1 reader rejects version 2.",
            no_format_change_alternative="Keep the schema and derive the new value.",
            no_format_change_unavailable_reason=None,
            no_format_change_statement_position=1,
            format_change_statement_position=2,
        ),
        False,
        ("legacy",),
    ),
    ChecklistCase(
        "missing-rollback",
        PersistenceFormatProposal(
            legacy_read_behavior="Read version 1 records before migrating.",
            old_reader_new_data_behavior=None,
            no_format_change_alternative="Keep the schema and derive the new value.",
            no_format_change_unavailable_reason=None,
            no_format_change_statement_position=1,
            format_change_statement_position=2,
        ),
        False,
        ("rollback",),
    ),
    ChecklistCase(
        "missing-no-format-change-alternative",
        PersistenceFormatProposal(
            legacy_read_behavior="Read version 1 records before migrating.",
            old_reader_new_data_behavior="The version 1 reader rejects version 2.",
            no_format_change_alternative=None,
            no_format_change_unavailable_reason=None,
            no_format_change_statement_position=None,
            format_change_statement_position=1,
        ),
        False,
        ("no_format_change_alternative",),
    ),
)
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_checklist_reports_each_normative_column(case: ChecklistCase) -> None:
    result = validate_persistence_format_proposal(case.proposal)

    assert result.passed is case.passed
    assert result.missing == case.missing
    assert len(result.missing) == len(case.missing)


def test_checklist_reports_all_missing_elements_without_short_circuiting() -> None:
    proposal = PersistenceFormatProposal(
        legacy_read_behavior=None,
        old_reader_new_data_behavior=None,
        no_format_change_alternative=None,
        no_format_change_unavailable_reason=None,
        no_format_change_statement_position=None,
        format_change_statement_position=1,
    )

    result = validate_persistence_format_proposal(proposal)

    assert result.passed is False
    assert result.missing == (
        "legacy",
        "rollback",
        "no_format_change_alternative",
    )


def test_alternative_presented_after_format_change_is_missing() -> None:
    proposal = PersistenceFormatProposal(
        legacy_read_behavior="Read version 1 records before migrating.",
        old_reader_new_data_behavior="The version 1 reader rejects version 2.",
        no_format_change_alternative="Keep the schema and derive the new value.",
        no_format_change_unavailable_reason=None,
        no_format_change_statement_position=2,
        format_change_statement_position=1,
    )

    result = validate_persistence_format_proposal(proposal)

    assert result.passed is False
    assert result.missing == ("no_format_change_alternative",)


def test_reasoned_absence_of_alternative_passes_when_presented_first() -> None:
    proposal = PersistenceFormatProposal(
        legacy_read_behavior="Read version 1 records before migrating.",
        old_reader_new_data_behavior="The version 1 reader rejects version 2.",
        no_format_change_alternative=None,
        no_format_change_unavailable_reason=(
            "The reader must persist the new field because it cannot be derived."
        ),
        no_format_change_statement_position=1,
        format_change_statement_position=2,
    )

    result = validate_persistence_format_proposal(proposal)

    assert result.passed is True
    assert result.missing == ()