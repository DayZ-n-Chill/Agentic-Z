"""Vanilla-tree control gate for dayz-script-validator.

Bohemia's vanilla script tree compiles and ships, so a linter finding on
it is a false positive by construction. This control runs the existing
validator over that tree and fails if the findings differ from a measured
baseline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
TOOL_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_vanilla_index import tree_digest  # noqa: E402
from script_validator import validate_addon  # noqa: E402
from shared.input_errors import discover_files  # noqa: E402
from shared.vanilla_reference import loaded_index_path  # noqa: E402
from shared.vanilla_tree import resolve_vanilla_root  # noqa: E402


DEFAULT_BASELINE_PATH = (
    TOOL_DIR / "tests" / "baselines" / "vanilla_control_baseline.json"
)
DIGEST_MISMATCH_MESSAGE = (
    "the control tree is not the one that was measured; check the DayZ "
    "build, then re-baseline on purpose with --update"
)
LOCAL_INDEX_MESSAGE = (
    "a local vanilla index is loaded (%s); the baseline measures the "
    "validator without one, so move that file away and run the control again"
)
DEFAULT_WHAT_THIS_IS = (
    "Expected findings of dayz-script-validator over Bohemia's vanilla "
    "script tree. The tree compiles and ships, so any finding on it is a "
    "false positive by construction: this file is the allowlist of the ones "
    "already triaged, each with the reason it is tolerated. A finding that "
    "is NOT here fails the control."
)
DEFAULT_DIGEST_SCOPE = (
    "sha256 over (posix relpath, sha256 of contents) of every file the "
    "validator discovers under the vanilla root, in walk order. Not "
    "comparable to the vanilla_index digest, which covers .c only."
)


def posix_file(value):
    return str(value).replace("\\", "/")


def rule_id_of(item):
    return item.get("rule_id") or item.get("check") or "?"


def error_pairs(errors):
    pairs = set()
    for item in errors:
        pairs.add((rule_id_of(item), posix_file(item.get("file", ""))))
    return pairs


def warning_counts_from(warnings):
    counts = {}
    for item in warnings:
        key = rule_id_of(item)
        counts[key] = counts.get(key, 0) + 1
    return counts


def compare(run, baseline):
    """Pure comparison of a linter run against a measured baseline.

    Does not touch disk and does not invoke the linter.
    """
    run = run or {}
    baseline = baseline or {}
    run_errors = error_pairs(run.get("errors") or [])
    base_errors = error_pairs(baseline.get("errors") or [])
    extra_errors = sorted(run_errors - base_errors)
    missing_errors = sorted(base_errors - run_errors)

    run_warnings = warning_counts_from(run.get("warnings") or [])
    base_warnings = dict(baseline.get("warning_counts") or {})
    new_warning_rules = sorted(
        rule_id for rule_id in run_warnings if rule_id not in base_warnings
    )
    warning_increases = []
    warning_decreases = []
    for rule_id, run_count in sorted(run_warnings.items()):
        if rule_id not in base_warnings:
            continue
        base_count = int(base_warnings[rule_id])
        if run_count > base_count:
            warning_increases.append((rule_id, run_count, base_count))
        elif run_count < base_count:
            warning_decreases.append((rule_id, run_count, base_count))
    for rule_id, base_count in sorted(base_warnings.items()):
        if rule_id not in run_warnings and int(base_count) > 0:
            warning_decreases.append((rule_id, 0, int(base_count)))

    tree = baseline.get("tree") or {}
    digest_run = run.get("tree_digest")
    digest_baseline = tree.get("digest")
    digest_mismatch = digest_run != digest_baseline

    failed = bool(
        extra_errors
        or missing_errors
        or new_warning_rules
        or warning_increases
        or digest_mismatch
    )
    return {
        "status": "FAIL" if failed else "PASS",
        "extra_errors": extra_errors,
        "missing_errors": missing_errors,
        "new_warning_rules": new_warning_rules,
        "warning_increases": warning_increases,
        "warning_decreases": warning_decreases,
        "digest_mismatch": digest_mismatch,
        "digest_run": digest_run,
        "digest_baseline": digest_baseline,
    }


def format_human(comparison):
    extra_errors = comparison["extra_errors"]
    missing_errors = comparison["missing_errors"]
    new_warning_rules = comparison["new_warning_rules"]
    warning_increases = comparison["warning_increases"]
    warning_decreases = comparison["warning_decreases"]
    digest_mismatch = comparison["digest_mismatch"]

    details = []
    for rule_id, file_name in extra_errors:
        details.append("  new finding  %s  %s" % (rule_id, file_name))
    for rule_id, file_name in missing_errors:
        details.append(
            "  stale baseline  %s  %s; re-baseline on purpose with --update"
            % (rule_id, file_name)
        )
    for rule_id in new_warning_rules:
        details.append("  new warning rule  %s" % rule_id)
    for rule_id, run_count, base_count in warning_increases:
        details.append(
            "  warning count above baseline  %s  %d > %d"
            % (rule_id, run_count, base_count)
        )
    for rule_id, run_count, base_count in warning_decreases:
        details.append(
            "  improved  %s  %d < %d; re-baseline on purpose with --update"
            % (rule_id, run_count, base_count)
        )
    if digest_mismatch:
        details.append("  %s" % DIGEST_MISMATCH_MESSAGE)

    if extra_errors:
        rule_id, file_name = extra_errors[0]
        head = "FAIL - new finding %s %s" % (rule_id, file_name)
    elif missing_errors:
        rule_id, file_name = missing_errors[0]
        head = (
            "FAIL - baseline is stale: %s %s; re-baseline on purpose with --update"
            % (rule_id, file_name)
        )
    elif new_warning_rules:
        head = "FAIL - new warning rule %s" % new_warning_rules[0]
    elif warning_increases:
        rule_id, run_count, base_count = warning_increases[0]
        head = "FAIL - warning count above baseline %s %d > %d" % (
            rule_id,
            run_count,
            base_count,
        )
    elif digest_mismatch:
        head = "FAIL - %s" % DIGEST_MISMATCH_MESSAGE
    elif warning_decreases:
        head = (
            "PASS - warning count dropped below the baseline "
            "(improvement; re-baseline on purpose with --update)"
        )
    else:
        head = "PASS - findings match the baseline"
    return head, details


def collect_run(vanilla_root):
    root = Path(vanilla_root).resolve()
    # The tree is its own vanilla root: without it ES-UNDEFINED-CLASS-REF
    # would SKIP and the control would prove nothing about that rule.
    result = validate_addon(root, vanilla_root=root)
    files = discover_files(root)
    return {
        "errors": list(result.get("errors") or []),
        "warnings": list(result.get("warnings") or []),
        "tree_digest": tree_digest(files, root),
        "file_count": len(files),
        "total_bytes": sum(path.stat().st_size for path in files),
        "elapsed_ms": (result.get("info") or {}).get("elapsed_ms"),
    }


def unexplained_entries(document):
    """Allowlist entries carrying no reason.

    The allowlist is only worth anything while every tolerated finding says
    why it is tolerated. --update cannot invent that reason, so it names the
    entries a human still has to fill in.
    """
    missing = []
    for item in (document.get("errors") or []):
        if not (item.get("note") or "").strip():
            missing.append((item.get("rule_id", "?"), item.get("file", "?")))
    return sorted(missing)


def build_baseline_document(run, previous=None):
    previous = previous or {}
    notes = {}
    for item in previous.get("errors") or []:
        key = (rule_id_of(item), posix_file(item.get("file", "")))
        if item.get("note"):
            notes[key] = item["note"]

    errors = []
    for item in run.get("errors") or []:
        key = (rule_id_of(item), posix_file(item.get("file", "")))
        errors.append(
            {
                "file": key[1],
                "note": notes.get(key, ""),
                "rule_id": key[0],
            }
        )

    prev_tree = previous.get("tree") or {}
    prev_measured = previous.get("measured") or {}
    elapsed_ms = run.get("elapsed_ms")
    if elapsed_ms is None:
        elapsed_seconds = prev_measured.get("elapsed_seconds", 0)
    else:
        elapsed_seconds = elapsed_ms / 1000.0
    return {
        "errors": errors,
        "measured": {
            "date": prev_measured.get("date", ""),
            "elapsed_seconds": elapsed_seconds,
            "roots": prev_measured.get("roots", ""),
            "runs": prev_measured.get("runs", 1),
        },
        "schema": previous.get("schema", 1),
        "totals": {
            "errors": len(run.get("errors") or []),
            "warnings": len(run.get("warnings") or []),
        },
        "tree": {
            "dayz_build": prev_tree.get("dayz_build", ""),
            "dayz_build_note": prev_tree.get("dayz_build_note", ""),
            "digest": run.get("tree_digest"),
            "digest_scope": prev_tree.get("digest_scope", DEFAULT_DIGEST_SCOPE),
            "file_count": run.get("file_count", 0),
            "total_bytes": run.get("total_bytes", 0),
        },
        "warning_counts": warning_counts_from(run.get("warnings") or []),
        "what_this_is": previous.get("what_this_is", DEFAULT_WHAT_THIS_IS),
    }


def load_baseline(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        return None, "baseline is unreadable: %s" % error
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        return None, "baseline is unreadable: %s" % error
    if not isinstance(data, dict):
        return None, "baseline is unreadable: expected a JSON object"
    return data, None


def write_baseline(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
    return path


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Compare dayz-script-validator findings on Bohemia's vanilla "
            "tree against a measured baseline."
        )
    )
    parser.add_argument(
        "--vanilla-root",
        default=None,
        help=(
            "Root of the vanilla scripts tree (default: DAYZ_VANILLA_ROOT, "
            "then P:\\scripts if present)"
        ),
    )
    parser.add_argument(
        "--baseline",
        default=str(DEFAULT_BASELINE_PATH),
        help=(
            "Baseline JSON path (default: tests/baselines/"
            "vanilla_control_baseline.json next to this tool)"
        ),
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Rewrite the baseline from the current run, on purpose.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable JSON report.",
    )
    return parser


def emit_skip(reason, json_mode):
    head = "SKIP - %s" % reason
    print(head)
    if json_mode:
        print(
            json.dumps(
                {"exit_code": 2, "reason": reason, "status": "SKIP"},
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
            )
        )
    return 2


def comparison_payload(comparison, head, details, exit_code):
    return {
        "details": details,
        "digest_baseline": comparison.get("digest_baseline"),
        "digest_mismatch": comparison.get("digest_mismatch"),
        "digest_run": comparison.get("digest_run"),
        "exit_code": exit_code,
        "extra_errors": [
            {"file": file_name, "rule_id": rule_id}
            for rule_id, file_name in comparison.get("extra_errors") or []
        ],
        "missing_errors": [
            {"file": file_name, "rule_id": rule_id}
            for rule_id, file_name in comparison.get("missing_errors") or []
        ],
        "new_warning_rules": list(comparison.get("new_warning_rules") or []),
        "status": comparison.get("status"),
        "verdict": head,
        "warning_decreases": [
            {"baseline": base_count, "run": run_count, "rule_id": rule_id}
            for rule_id, run_count, base_count in comparison.get("warning_decreases")
            or []
        ],
        "warning_increases": [
            {"baseline": base_count, "run": run_count, "rule_id": rule_id}
            for rule_id, run_count, base_count in comparison.get("warning_increases")
            or []
        ],
    }


def emit_comparison(comparison, json_mode):
    head, details = format_human(comparison)
    exit_code = 0 if comparison["status"] == "PASS" else 1
    if json_mode:
        print(
            json.dumps(
                comparison_payload(comparison, head, details, exit_code),
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
            )
        )
    else:
        print(head)
        for line in details:
            print(line)
    return exit_code


def emit_update(path, comparison, created, unexplained=()):
    if created:
        head = "UPDATED - created %s" % path
    elif comparison is None:
        head = "UPDATED - wrote %s" % path
    elif comparison["status"] == "PASS" and not comparison["warning_decreases"]:
        head = "UPDATED - wrote %s (unchanged vs previous)" % path
    else:
        head = "UPDATED - wrote %s" % path
    print(head)
    if comparison is not None:
        _ignored_head, details = format_human(comparison)
        for line in details:
            print(line)
    for rule_id, file_name in unexplained:
        print(
            "  NO REASON WRITTEN  %s  %s; an entry without a note is a "
            "finding nobody triaged" % (rule_id, file_name)
        )
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    vanilla_root, skip = resolve_vanilla_root(args.vanilla_root)
    if skip:
        return emit_skip(skip, args.json)
    index_path = loaded_index_path()
    if index_path is not None:
        return emit_skip(LOCAL_INDEX_MESSAGE % index_path, args.json)

    baseline_path = Path(args.baseline)
    if args.update:
        previous = None
        created = not baseline_path.is_file()
        if not created:
            previous, error = load_baseline(baseline_path)
            if error:
                return emit_skip(error, args.json)
        try:
            run = collect_run(vanilla_root)
            document = build_baseline_document(run, previous)
            write_baseline(baseline_path, document)
        except OSError as error:
            return emit_skip("baseline is not writable: %s" % error, args.json)
        comparison = compare(run, previous) if previous is not None else None
        return emit_update(
            baseline_path, comparison, created, unexplained_entries(document)
        )

    if not baseline_path.is_file():
        return emit_skip("baseline file not found: %s" % baseline_path, args.json)
    baseline, error = load_baseline(baseline_path)
    if error:
        return emit_skip(error, args.json)
    run = collect_run(vanilla_root)
    return emit_comparison(compare(run, baseline), args.json)


if __name__ == "__main__":
    sys.exit(main())
