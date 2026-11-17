import re


ES_LAYOUT_PATH_PBOPREFIX_RULE_ID = "ES-LAYOUT-PATH-PBOPREFIX-MISMATCH"


ES_LAYOUT_PATH_PBOPREFIX_NO_PREFIX_RULE_ID = (
    "ES-LAYOUT-PATH-PBOPREFIX-MISMATCH-NO-PREFIX"
)


# Layout path mismatch causes crash + ghost menu in UIManager
# (pitfalls-advanced.md:304-316, SKILL.md rule 34, dayz-mod-workflow:187).
# Cross-file rule: addon's `$PBOPREFIX$` defines the canonical prefix; every
# .layout string literal in .c files must start with that prefix.
#
# Phase 1 supported pattern: string literals only — `".../<name>.layout"`.
# Phase 1 NOT supported: paths built by concatenation (`"prefix" + "/path"`)
# or by variables. Known false negative.


# Pre-stripper string-literal extractor that ignores comments.
# Walks source char-by-char with a tiny state machine; returns
# [(line_number, string_content), ...] for every "..." literal in code.
def _extract_string_literals(source):
    literals = []
    chars = source
    length = len(chars)
    index = 0
    line_number = 1
    state = "code"
    buffer_start_line = 0
    buffer_chars = []

    while index < length:
        char = chars[index]
        next_char = chars[index + 1] if index + 1 < length else ""

        if state == "code":
            if char == "\n":
                line_number += 1
                index += 1
                continue
            if char == "/" and next_char == "/":
                state = "line_comment"
                index += 2
                continue
            if char == "/" and next_char == "*":
                state = "block_comment"
                index += 2
                continue
            if char == '"':
                state = "string"
                buffer_start_line = line_number
                buffer_chars = []
                index += 1
                continue
            index += 1
            continue

        if state == "line_comment":
            if char == "\n":
                state = "code"
                line_number += 1
            index += 1
            continue

        if state == "block_comment":
            if char == "\n":
                line_number += 1
                index += 1
                continue
            if char == "*" and next_char == "/":
                state = "code"
                index += 2
                continue
            index += 1
            continue

        if state == "string":
            if char == "\\" and next_char:
                # Capture the escaped pair literally; only `\"` and `\\` matter
                # for string termination, but we don't need to interpret
                # escapes — just skip the next char.
                buffer_chars.append(char)
                buffer_chars.append(next_char)
                if next_char == "\n":
                    line_number += 1
                index += 2
                continue
            if char == '"':
                literals.append((buffer_start_line, "".join(buffer_chars)))
                state = "code"
                index += 1
                continue
            if char == "\n":
                # Unterminated string; bail out for this literal but keep
                # scanning the rest of the file.
                line_number += 1
                state = "code"
                index += 1
                continue
            buffer_chars.append(char)
            index += 1
            continue

    return literals


# `.layout` path detector. Permissive on the prefix portion (anything but `"`
# and whitespace) and requires the suffix `.layout` immediately before the
# closing quote. A literal with whitespace is a message that names a layout,
# such as a Print after a failed CreateWidgets (inbox 22f2), not a path; a
# path with a space in it is a known false negative.
_LAYOUT_PATH_RE = re.compile(r"^[^\"\s]*\.layout$")


def _normalize_prefix(raw_prefix):
    """Trim whitespace and trailing slashes; return None if empty."""
    if raw_prefix is None:
        return None
    cleaned = raw_prefix.strip()
    if not cleaned:
        return None
    while cleaned.endswith(("/", "\\")):
        cleaned = cleaned[:-1]
    return cleaned


def parse_pboprefix(addon_root):
    """Read `$PBOPREFIX$` from the addon root; return the prefix string or None.

    `addon_root` may be a directory path (pathlib.Path) or a single file path
    (linter invoked on one .c file, no addon scope). When `addon_root` is a
    file, walks up to find a `$PBOPREFIX$` sibling — phase 1 keeps this simple
    and only checks the directory containing the file.
    """
    if addon_root is None:
        return None
    try:
        if addon_root.is_file():
            candidate = addon_root.parent / "$PBOPREFIX$"
        else:
            candidate = addon_root / "$PBOPREFIX$"
    except (OSError, AttributeError):
        return None

    if not candidate.exists() or not candidate.is_file():
        return None

    try:
        text = candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    for raw_line in text.splitlines():
        normalized = _normalize_prefix(raw_line)
        if normalized:
            return normalized
    return None


def _path_starts_with_prefix(path, prefix):
    """Case-insensitive prefix check. Accept both `/` and `\\` separators."""
    if not path or not prefix:
        return False
    normalized_path = path.replace("\\", "/").lower()
    normalized_prefix = prefix.replace("\\", "/").lower()
    if not normalized_path.startswith(normalized_prefix):
        return False
    # Require a separator after the prefix (or exact match if path == prefix)
    after = normalized_path[len(normalized_prefix) :]
    return after == "" or after.startswith("/")


def check_es_layout_path_pboprefix(source, rel_path, prefix):
    """Scan a single .c source for `.layout` string literals and verify each
    one starts with `prefix`. If `prefix` is None (no `$PBOPREFIX$` found),
    skip silently — phase 1 does not bootstrap the prefix from other sources.
    """
    errors = []

    if prefix is None:
        return errors

    for line_number, literal in _extract_string_literals(source):
        if not _LAYOUT_PATH_RE.match(literal):
            continue
        if _path_starts_with_prefix(literal, prefix):
            continue
        message = (
            f"[FAIL] {rel_path} line {line_number}: layout path "
            f"'{literal}' does not start with $PBOPREFIX$ "
            f"'{prefix}'. Mismatch causes crash + ghost menu in "
            "UIManager (pitfalls-advanced.md:304-316, SKILL.md rule "
            "34). Update the layout path to begin with the addon's "
            "PBOPREFIX or update $PBOPREFIX$ to match."
        )
        errors.append(
            {
                "check": ES_LAYOUT_PATH_PBOPREFIX_RULE_ID,
                "file": rel_path,
                "line": line_number,
                "message": message,
                "severity": "FAIL",
                "rule_id": ES_LAYOUT_PATH_PBOPREFIX_RULE_ID,
            }
        )

    return errors
