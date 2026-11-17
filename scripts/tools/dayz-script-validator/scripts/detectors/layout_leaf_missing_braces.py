# QUARANTINED — not imported or called by script_validator.py.
# Rule LAYOUT-LEAF-MISSING-BRACES is false: a leaf .layout widget
# without a child { } block is valid Enfusion syntax. Its 28 hits on
# one mod were false positives (confirmed against the layouts of four other mods).
# The file remains as a record of the rejected rule. Do not re-wire it.

import re
from collections import namedtuple


RULE_ID = "LAYOUT-LEAF-MISSING-BRACES"
CHECK_NAME = RULE_ID
MESSAGE = (
    "[FAIL] {rel_path} line {line}: widget '{name}' ({class_name}) "
    "has no {{ }} block; add {{ }} even when it is empty."
)


Token = namedtuple("Token", ["type", "value", "line"])
CLASS_RE = re.compile(r"^[A-Za-z_]\w*Class$")


def _is_ident_start(char):
    return char == "_" or char.isalpha()


def _is_ident_char(char):
    return char == "_" or char.isalnum()


def _is_number_start(chars, index):
    char = chars[index]
    next_char = chars[index + 1] if index + 1 < len(chars) else ""
    next_next = chars[index + 2] if index + 2 < len(chars) else ""

    if char in "+-":
        return next_char.isdigit() or (next_char == "." and next_next.isdigit())
    if char == ".":
        return next_char.isdigit()
    return char.isdigit()


def _consume_number(chars, index):
    start = index
    if chars[index] in "+-":
        index += 1

    while index < len(chars) and chars[index].isdigit():
        index += 1

    if index < len(chars) and chars[index] == ".":
        index += 1
        while index < len(chars) and chars[index].isdigit():
            index += 1

    return chars[start:index], index


def _tokenize_layout(source):
    tokens = []
    index = 0
    line = 1
    length = len(source)

    if source.startswith("\ufeff"):
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

        if char == '"':
            start_line = line
            buffer = []
            index += 1
            while index < length:
                char = source[index]
                next_char = source[index + 1] if index + 1 < length else ""
                if char == "\\" and next_char:
                    buffer.append(char)
                    buffer.append(next_char)
                    if next_char == "\n":
                        line += 1
                    index += 2
                    continue
                if char == '"':
                    index += 1
                    break
                if char == "\n":
                    line += 1
                buffer.append(char)
                index += 1
            tokens.append(Token("STRING", "".join(buffer), start_line))
            continue

        if char == "{":
            tokens.append(Token("LBRACE", char, line))
            index += 1
            continue

        if char == "}":
            tokens.append(Token("RBRACE", char, line))
            index += 1
            continue

        if _is_number_start(source, index):
            value, index = _consume_number(source, index)
            tokens.append(Token("NUM", value, line))
            continue

        if _is_ident_start(char):
            start = index
            index += 1
            while index < length and _is_ident_char(source[index]):
                index += 1
            tokens.append(Token("IDENT", source[start:index], line))
            continue

        index += 1

    return tokens


def _is_widget_class(token):
    if token.type != "IDENT":
        return False
    if token.value == "ScriptParamsClass":
        return False
    return CLASS_RE.match(token.value) is not None


def _is_widget_name(token):
    return token.type in ("IDENT", "STRING")


def _matching_braces(tokens):
    stack = []
    pairs = {}

    for index, token in enumerate(tokens):
        if token.type == "LBRACE":
            stack.append(index)
            continue
        if token.type == "RBRACE" and stack:
            open_index = stack.pop()
            pairs[open_index] = index

    return pairs


def _has_direct_child_block(tokens, body_open_index, body_close_index):
    depth = 0

    for index in range(body_open_index + 1, body_close_index):
        token = tokens[index]
        if token.type == "LBRACE":
            if depth == 0:
                return True
            depth += 1
            continue
        if token.type == "RBRACE" and depth > 0:
            depth -= 1

    return False


def _build_finding(rel_path, class_token, name_token):
    message = MESSAGE.format(
        rel_path=rel_path,
        line=class_token.line,
        name=name_token.value,
        class_name=class_token.value,
    )
    return {
        "check": CHECK_NAME,
        "file": rel_path,
        "line": class_token.line,
        "message": message,
        "severity": "FAIL",
        "rule_id": RULE_ID,
    }


def check_layout_leaf_missing_braces(source: str, rel_path: str) -> list[dict]:
    if not source.strip():
        return []

    tokens = _tokenize_layout(source)
    brace_pairs = _matching_braces(tokens)
    findings = []

    for index, token in enumerate(tokens):
        if not _is_widget_class(token):
            continue
        if index + 1 >= len(tokens) or not _is_widget_name(tokens[index + 1]):
            continue

        name_token = tokens[index + 1]
        body_open_index = index + 2
        if body_open_index >= len(tokens) or tokens[body_open_index].type != "LBRACE":
            findings.append(_build_finding(rel_path, token, name_token))
            continue

        body_close_index = brace_pairs.get(body_open_index, len(tokens))
        if not _has_direct_child_block(tokens, body_open_index, body_close_index):
            findings.append(_build_finding(rel_path, token, name_token))

    return findings