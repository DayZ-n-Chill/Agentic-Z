# CANDIDATE-37 LAYOUT-XML-FORMAT.
# A .layout authored in XML instead of the Enfusion brace format
# (`WidgetClass Name { props { children } }`) crashes when the native
# CreateWidgets parses it. The widget-name/#STR reconciliation passes with the
# wrong format, so the format must be checked on its own.
# Source: origin: production mod bug ledger (BUG-004 UPDATE) — the crashing files were
# `<?xml ...?>` + `<GUI><class type=...>`. Corroborated by
# dayz-ui-development/references/layout-format.md:5 (".layout files use
# Enfusion format (NOT XML)").
#
# Trigger is NARROW on purpose: only the verified-crashing signatures
# (`<?xml` prolog or a `<GUI>` root). Other angle-bracket dialects seen in the
# wild (e.g. `<GridSpacerWidget ...>`, `<root>...`) are NOT flagged — their
# in-game behaviour is unverified and some mods load them with custom parsers,
# so flagging them would be a false positive. Partial coverage -> false
# negatives, never false positives (same philosophy as vanilla_reference).

RULE_ID = "LAYOUT-XML-FORMAT"
CHECK_NAME = RULE_ID
MESSAGE = (
    "[FAIL] {rel_path} line {line}: .layout in XML format (starts with "
    "'{signature}'); DayZ CreateWidgets expects Enfusion brace format "
    "(WidgetClass Name {{ ... }}), not XML. An XML layout crashes on load "
    "(origin: production mod bug ledger; layout-format.md:5 'NOT XML'). Re-author "
    "the layout in Enfusion brace format."
)


def _first_significant_index(source):
    """Return (line, index) of the first non-whitespace, non-comment char.

    Skips a leading BOM and both `//` and `/* */` comments, tracking line
    numbers. Returns (line, None) for an empty/comment-only file.
    """
    index = 0
    length = len(source)
    line = 1

    if source.startswith("﻿"):
        index = 1

    while index < length:
        char = source[index]
        next_char = source[index + 1] if index + 1 < length else ""

        if char == "\n":
            line += 1
            index += 1
            continue
        if char.isspace():
            index += 1
            continue
        if char == "/" and next_char == "/":
            index += 2
            while index < length and source[index] != "\n":
                index += 1
            continue
        if char == "/" and next_char == "*":
            index += 2
            while index < length:
                if source[index] == "\n":
                    line += 1
                    index += 1
                    continue
                if source[index] == "*" and index + 1 < length and source[index + 1] == "/":
                    index += 2
                    break
                index += 1
            continue

        return line, index

    return line, None


def _matched_signature(source, index):
    """Return the verified XML signature at `index`, or None.

    Verified-crashing signatures only: an `<?xml` prolog, or a `<GUI>` root
    tag (case-insensitive). A `<GUI` match requires a tag boundary after it
    (`>`, whitespace, or EOF) so it never matches an unrelated `<GUIxxx`.
    """
    window = source[index:index + 5].lower()
    if window.startswith("<?xml"):
        return "<?xml"
    if source[index:index + 4].lower() == "<gui":
        after = source[index + 4] if index + 4 < len(source) else ""
        if after == "" or after == ">" or after.isspace():
            return "<GUI"
    return None


def check_layout_xml_format(source: str, rel_path: str) -> list[dict]:
    if not source.strip():
        return []

    line, index = _first_significant_index(source)
    if index is None:
        return []

    signature = _matched_signature(source, index)
    if signature is None:
        return []

    message = MESSAGE.format(rel_path=rel_path, line=line, signature=signature)
    return [
        {
            "check": CHECK_NAME,
            "file": rel_path,
            "line": line,
            "message": message,
            "severity": "FAIL",
            "rule_id": RULE_ID,
        }
    ]
