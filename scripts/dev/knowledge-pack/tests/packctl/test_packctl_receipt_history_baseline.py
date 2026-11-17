from __future__ import annotations

import packctl.promotion as promotion


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
