import re

from shared.control_flow import line_is_inside_server_guard, line_is_inside_try_block
from shared.method_recognition import (
    find_if_body_range,
    find_inline_pattern_line,
    find_method_regions,
    find_params_read_context_param_name,
    method_is_onrpc,
    method_is_onstoreload,
)


ES_CTX_READ_RULE_ID = "ES-CTX-READ-UNCHECKED"


ES_CTX_READ_UNSUPPORTED_RULE_ID = "ES-CTX-READ-UNSUPPORTED-PATTERN"


ES_CTX_READ_FAIL_MESSAGE = (
    "[FAIL] {rel_path} line {line}: ctx.Read() return not checked inside "
    "{method} (fail-closed context). Required: 'if (!ctx.Read(...)) return "
    "false;' (SKILL.md rule 18, networking.md:169). Silent corruption on "
    "truncated/corrupted packet."
)


ES_CTX_READ_WARN_MESSAGE = (
    "[WARN] {rel_path} line {line}: ctx.Read() return not checked. Recommended: "
    "'if (!ctx.Read(...)) ...'."
)


ES_CTX_READ_UNSUPPORTED_MESSAGE = (
    "[WARN] {rel_path} line {line}: unsupported ctx.Read() check pattern for "
    "ES-CTX-READ-UNCHECKED ({reason}). Phase 1 supports only inline "
    "'if (!ctx.Read(...))', inline 'if (ctx.Read(...))' with non-empty body, "
    "or bool local checked within 5 lines."
)


def compile_ctx_read_re(param_name):
    escaped = re.escape(param_name)
    return re.compile(r"\b" + escaped + r"\.Read\s*\(")


def compile_ctx_read_inline_negated_re(param_name):
    escaped = re.escape(param_name)
    return re.compile(r"if\s*\(\s*!\s*" + escaped + r"\.Read\s*\([^)]*\)\s*\)")


def compile_ctx_read_inline_positive_re(param_name):
    escaped = re.escape(param_name)
    return re.compile(r"if\s*\(\s*" + escaped + r"\.Read\s*\([^)]*\)\s*\)")


def compile_ctx_read_bool_local_re(param_name):
    escaped = re.escape(param_name)
    return re.compile(r"\bbool\s+(?P<var>\w+)\s*=\s*" + escaped + r"\.Read\s*\(")


def extract_if_condition(text):
    match = re.search(r"\bif\s*\(", text)
    if not match:
        return None

    start = match.end()
    balance = 1
    for index in range(start, len(text)):
        char = text[index]
        if char == "(":
            balance += 1
        elif char == ")":
            balance -= 1
            if balance == 0:
                return text[start:index]

    return text[start:]


def line_has_combined_ctx_read_condition(lines, line_index, param_name):
    previous = lines[line_index - 1] if line_index > 0 else ""
    combined = previous + " " + lines[line_index]
    condition = extract_if_condition(combined)
    if condition is None:
        return False
    read_re = compile_ctx_read_re(param_name)
    return read_re.search(condition) is not None and (
        "&&" in condition or "||" in condition
    )


def line_has_statement_content(line):
    content = line.replace("{", " ").replace("}", " ").strip()
    if content == "":
        return False
    return not content.startswith("#")


def if_body_has_statement(lines, if_line_index, method):
    method_end_index = method["end_line"] - 1 if method else len(lines) - 1
    start_line, end_line = find_if_body_range(lines, if_line_index, method_end_index)

    for line_number in range(start_line, end_line + 1):
        line = lines[line_number - 1]
        if line_number == if_line_index + 1:
            close_paren = line.rfind(")")
            if close_paren != -1:
                line = line[close_paren + 1 :]
        if line_has_statement_content(line):
            return True

    return False


def bool_local_is_checked_within_window(var_name, lines, line_index, method):
    method_end_index = method["end_line"] - 1 if method else len(lines) - 1
    last_index = min(line_index + 5, method_end_index)
    check_re = re.compile(r"^\s*if\s*\(\s*!?\s*" + re.escape(var_name) + r"\s*\)")

    for index in range(line_index + 1, last_index + 1):
        if check_re.search(lines[index]):
            return True

    return False


def ctx_read_has_supported_check(lines, line_index, method, param_name):
    if line_has_combined_ctx_read_condition(lines, line_index, param_name):
        return False

    negated_re = compile_ctx_read_inline_negated_re(param_name)
    if find_inline_pattern_line(negated_re, lines, line_index) is not None:
        return True

    positive_re = compile_ctx_read_inline_positive_re(param_name)
    positive_if_index = find_inline_pattern_line(
        positive_re, lines, line_index
    )
    if positive_if_index is not None:
        return if_body_has_statement(lines, positive_if_index, method)

    bool_local_re = compile_ctx_read_bool_local_re(param_name)
    bool_match = bool_local_re.search(lines[line_index])
    if bool_match:
        return bool_local_is_checked_within_window(
            bool_match.group("var"), lines, line_index, method
        )

    return False


def find_bool_local_unsupported_reason(var_name, lines, line_index, method):
    method_end_index = method["end_line"] - 1 if method else len(lines) - 1
    combined_check_re = re.compile(
        r"^\s*if\s*\([^)]*\b"
        + re.escape(var_name)
        + r"\b[^)]*(?:&&|\|\|)[^)]*\)"
    )
    loose_check_re = re.compile(r"^\s*if\s*\([^)]*\b" + re.escape(var_name) + r"\b")

    for index in range(line_index + 1, method_end_index + 1):
        if combined_check_re.search(lines[index]):
            return "bool local checked with a combined condition"
        if index > line_index + 5 and loose_check_re.search(lines[index]):
            return "bool local checked outside the 5-line window"

    return None


def find_ctx_read_unsupported_reason(lines, line_index, method, param_name):
    current = lines[line_index]
    if line_is_inside_try_block(lines, line_index, method):
        return "inside try/catch block"

    if line_has_combined_ctx_read_condition(lines, line_index, param_name):
        return "combined condition around ctx.Read()"

    bool_local_re = compile_ctx_read_bool_local_re(param_name)
    bool_match = bool_local_re.search(current)
    if bool_match:
        return find_bool_local_unsupported_reason(
            bool_match.group("var"), lines, line_index, method
        )

    return None


def build_es_ctx_read_unsupported_warning(rel_path, line_number, reason):
    return {
        "check": ES_CTX_READ_UNSUPPORTED_RULE_ID,
        "file": rel_path,
        "line": line_number,
        "message": ES_CTX_READ_UNSUPPORTED_MESSAGE.format(
            rel_path=rel_path,
            line=line_number,
            reason=reason,
        ),
        "severity": "WARN",
        "rule_id": ES_CTX_READ_UNSUPPORTED_RULE_ID,
    }


def build_es_ctx_read_finding(rel_path, line_number, method, severity):
    if severity == "FAIL":
        message = ES_CTX_READ_FAIL_MESSAGE.format(
            rel_path=rel_path,
            line=line_number,
            method=method["name"],
        )
    else:
        message = ES_CTX_READ_WARN_MESSAGE.format(
            rel_path=rel_path,
            line=line_number,
        )

    return {
        "check": ES_CTX_READ_RULE_ID,
        "file": rel_path,
        "line": line_number,
        "message": message,
        "severity": severity,
        "rule_id": ES_CTX_READ_RULE_ID,
    }


def check_es_ctx_read_unchecked(stripped_source, rel_path):
    errors = []
    warnings = []
    lines = stripped_source.split("\n")
    methods = find_method_regions(stripped_source)

    for method in methods:
        param_name = find_params_read_context_param_name(method)
        if param_name is None:
            continue

        read_re = compile_ctx_read_re(param_name)
        for line_number in range(method["start_line"], method["end_line"] + 1):
            line_index = line_number - 1
            for _match in read_re.finditer(lines[line_index]):
                unsupported_reason = find_ctx_read_unsupported_reason(
                    lines, line_index, method, param_name
                )
                if unsupported_reason:
                    warnings.append(
                        build_es_ctx_read_unsupported_warning(
                            rel_path, line_number, unsupported_reason
                        )
                    )
                    continue

                if ctx_read_has_supported_check(lines, line_index, method, param_name):
                    continue

                severity = "WARN"
                if method_is_onstoreload(method):
                    severity = "FAIL"
                elif method_is_onrpc(method) and line_is_inside_server_guard(
                    method, line_number, lines
                ):
                    severity = "FAIL"

                finding = build_es_ctx_read_finding(
                    rel_path, line_number, method, severity
                )
                if severity == "FAIL":
                    errors.append(finding)
                else:
                    warnings.append(finding)

    return errors, warnings
