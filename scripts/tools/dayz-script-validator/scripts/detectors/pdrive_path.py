import re


PDRIVE_PATH_RVMAT_RULE_ID = "RVMAT-PDRIVE-PATH"
PDRIVE_PATH_CONFIG_RULE_ID = "CONFIG-PDRIVE-PATH"


# Matches a baked-in work-drive path at the start of a double-quoted string
# value, e.g. texture="P:\dz\...paa" or hiddenSelectionsTextures[]={"P:\DZ..."}.
# The drive letter is case-insensitive; the path separator (\ or /) after "P:"
# is required so a stray "P:" that is not a path is never flagged. Comments are
# stripped first (strings preserved) so commented-out vanilla refs do not FP.
PDRIVE_PATH_RE = re.compile(r'"[Pp]:[\\/]')


def _build_message(rel_path, line_number):
    return (
        f"[WARN] {rel_path} line {line_number}: baked-in work-drive path "
        "'P:\\...' in a quoted asset path. Absolute P:\\ paths only resolve on "
        "the dev machine with P: mounted and break on distribution (missing "
        "texture/material). Use a path relative to the addon root (no P:\\ "
        "prefix). Source: dayz-p3d-audit/SKILL.md:308-325,:364-374."
    )


def strip_comments_keep_strings(source):
    """Blank // and /* */ comments while preserving string literals and lines.

    Unlike strip_enforce_comments_and_strings (stripper.py), string contents
    are kept: the P:\\ path lives inside a quoted value and must stay visible
    to the regex. String tracking also shields // and /* inside strings.
    """
    chars = list(source)
    index = 0
    length = len(chars)
    state = "code"
    escaped = False

    while index < length:
        char = chars[index]
        next_char = chars[index + 1] if index + 1 < length else ""

        if state == "code":
            if char == "/" and next_char == "/":
                chars[index] = " "
                chars[index + 1] = " "
                index += 2
                state = "line_comment"
                continue
            if char == "/" and next_char == "*":
                chars[index] = " "
                chars[index + 1] = " "
                index += 2
                state = "block_comment"
                continue
            if char == '"':
                index += 1
                state = "string"
                escaped = False
                continue
            index += 1
            continue

        if state == "line_comment":
            if char == "\n":
                state = "code"
            else:
                chars[index] = " "
            index += 1
            continue

        if state == "block_comment":
            if char == "\n":
                index += 1
                continue
            if char == "*" and next_char == "/":
                chars[index] = " "
                chars[index + 1] = " "
                index += 2
                state = "code"
                continue
            chars[index] = " "
            index += 1
            continue

        # state == "string"
        if char == "\n":
            escaped = False
            index += 1
            continue
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            state = "code"
        index += 1

    return "".join(chars)


def check_pdrive_path(source, rel_path, rule_id):
    cleaned = strip_comments_keep_strings(source)
    findings = []
    for line_number, line in enumerate(cleaned.splitlines(), start=1):
        if PDRIVE_PATH_RE.search(line):
            findings.append(
                {
                    "check": rule_id,
                    "file": rel_path,
                    "line": line_number,
                    "message": _build_message(rel_path, line_number),
                    "severity": "WARN",
                    "rule_id": rule_id,
                }
            )
    return findings
