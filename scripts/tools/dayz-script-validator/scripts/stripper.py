UNTERMINATED_STRING_RULE_ID = "ES-SOURCE-UNTERMINATED-STRING"


UNTERMINATED_BLOCK_COMMENT_RULE_ID = "ES-SOURCE-UNTERMINATED-BLOCK-COMMENT"


def make_stripper_warning(rule_id, rel_path, token_name, line_number):
    location = rel_path if rel_path else "<unknown>"
    return {
        "check": rule_id,
        "file": location,
        "line": line_number,
        "rule_id": rule_id,
        "severity": "WARN",
        "message": (
            f"[WARN] {location}: unterminated {token_name} starting near line "
            f"{line_number}. Linter coverage on this file is degraded; fix the "
            "source or rely on baseline syntax validation (dayz-pbo-build)."
        ),
    }


def strip_enforce_comments_and_strings(source, rel_path=None):
    """Remove comments and strings from Enforce Script while preserving lines."""
    chars = list(source)
    index = 0
    length = len(chars)
    state = "code"
    escaped = False
    line_number = 1
    state_start_line = None

    while index < length:
        char = chars[index]
        next_char = chars[index + 1] if index + 1 < length else ""

        if state == "code":
            if char == "\n":
                line_number += 1
                index += 1
                continue
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
                state_start_line = line_number
                continue
            if char == '"':
                chars[index] = " "
                index += 1
                state = "string"
                escaped = False
                state_start_line = line_number
                continue
            index += 1
            continue

        if state == "line_comment":
            if char == "\n":
                state = "code"
                line_number += 1
            else:
                chars[index] = " "
            index += 1
            continue

        if state == "block_comment":
            if char == "\n":
                line_number += 1
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

        if state == "string":
            if char == "\n":
                chars[index] = "\n"
                escaped = False
                line_number += 1
                index += 1
                continue
            chars[index] = " "
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                state = "code"
            index += 1
            continue

    stripper_warnings = []
    if state == "string":
        stripper_warnings.append(
            make_stripper_warning(
                UNTERMINATED_STRING_RULE_ID,
                rel_path,
                "string",
                state_start_line or line_number,
            )
        )
    elif state == "block_comment":
        stripper_warnings.append(
            make_stripper_warning(
                UNTERMINATED_BLOCK_COMMENT_RULE_ID,
                rel_path,
                "block comment",
                state_start_line or line_number,
            )
        )

    return "".join(chars), stripper_warnings
