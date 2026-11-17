from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersistenceFormatProposal:
    legacy_read_behavior: str | None
    old_reader_new_data_behavior: str | None
    no_format_change_alternative: str | None
    no_format_change_unavailable_reason: str | None
    no_format_change_statement_position: int | None
    format_change_statement_position: int


@dataclass(frozen=True)
class PersistenceChecklistResult:
    passed: bool
    missing: tuple[str, ...]


def _has_text(value: str | None) -> bool:
    return bool(value and value.strip())


def validate_persistence_format_proposal(
    proposal: PersistenceFormatProposal,
) -> PersistenceChecklistResult:
    missing: list[str] = []

    if not _has_text(proposal.legacy_read_behavior):
        missing.append("legacy")

    if not _has_text(proposal.old_reader_new_data_behavior):
        missing.append("rollback")

    alternative_declared = _has_text(
        proposal.no_format_change_alternative
    ) or _has_text(proposal.no_format_change_unavailable_reason)
    alternative_presented_first = (
        proposal.no_format_change_statement_position is not None
        and proposal.no_format_change_statement_position
        < proposal.format_change_statement_position
    )
    if not (alternative_declared and alternative_presented_first):
        missing.append("no_format_change_alternative")

    return PersistenceChecklistResult(
        passed=not missing,
        missing=tuple(missing),
    )