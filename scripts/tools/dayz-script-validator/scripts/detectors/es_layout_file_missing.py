# CANDIDATE-36 ES-LAYOUT-FILE-MISSING.
# A `.layout` string literal referenced from Enforce (CreateWidgets / a
# GetLayoutFile override) whose file does not exist in the addon crashes
# INSIDE the native CreateWidgets call (the `if(!root)` guard never runs).
# Source: origin: production mod bug ledger (BUG-004, crash). Distinct from
# ES-LAYOUT-PATH-PBOPREFIX-MISMATCH (CANDIDATE-10), which checks the prefix:
# this checks the target file EXISTS. Only correctly-prefixed paths are
# checked here, so the two rules do not overlap (a wrong prefix is CAND-10).
#
# Phase 1 supported: string literals only (reuses CANDIDATE-10's extractor).
# NOT supported: paths built by concatenation/variables (known false negative).

import pathlib

from detectors.es_layout_path_pboprefix import (
    _LAYOUT_PATH_RE,
    _extract_string_literals,
    _path_starts_with_prefix,
)


ES_LAYOUT_FILE_MISSING_RULE_ID = "ES-LAYOUT-FILE-MISSING"


def _strip_prefix(path, prefix):
    """Remove the leading `<prefix>` and return the addon-relative remainder.

    Caller has already confirmed `path` starts with `prefix` (case-insensitive,
    separator-aware), so slicing by the normalized prefix length is safe.
    """
    normalized_path = path.replace("\\", "/")
    normalized_prefix = prefix.replace("\\", "/")
    remainder = normalized_path[len(normalized_prefix):]
    return remainder.lstrip("/")


def _resolve_case_insensitive(root, rel):
    """True if `rel` resolves to an existing path under `root`, matching each
    segment case-insensitively (Bohemia paths are case-insensitive at runtime).
    """
    current = root
    for segment in rel.split("/"):
        if segment in ("", "."):
            continue
        try:
            entries = {entry.name.lower(): entry for entry in current.iterdir()}
        except (OSError, NotADirectoryError):
            return False
        match = entries.get(segment.lower())
        if match is None:
            return False
        current = match
    return current.exists()


def check_es_layout_file_missing(source, rel_path, prefix, addon_root):
    """Verify each correctly-prefixed `.layout` literal resolves to a file."""
    errors = []

    if prefix is None or addon_root is None:
        return errors
    try:
        root = pathlib.Path(addon_root)
        if not root.is_dir():
            return errors
    except (OSError, AttributeError):
        return errors

    for line_number, literal in _extract_string_literals(source):
        if not _LAYOUT_PATH_RE.match(literal):
            continue
        if not _path_starts_with_prefix(literal, prefix):
            # Wrong prefix is ES-LAYOUT-PATH-PBOPREFIX-MISMATCH's job; skip.
            continue
        relative = _strip_prefix(literal, prefix)
        if not relative:
            continue
        if _resolve_case_insensitive(root, relative):
            continue
        message = (
            f"[FAIL] {rel_path} line {line_number}: layout '{literal}' is "
            f"referenced but the file does not exist under the addon root "
            f"(resolved '{relative}'). CreateWidgets on a missing .layout "
            f"crashes inside the native call (origin: production mod bug ledger). "
            f"Create the file or fix the path."
        )
        errors.append(
            {
                "check": ES_LAYOUT_FILE_MISSING_RULE_ID,
                "file": rel_path,
                "line": line_number,
                "message": message,
                "severity": "FAIL",
                "rule_id": ES_LAYOUT_FILE_MISSING_RULE_ID,
            }
        )

    return errors
