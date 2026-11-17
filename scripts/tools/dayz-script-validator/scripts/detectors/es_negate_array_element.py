# QUARANTINED — not imported by script_validator.py and not executed.
# The rule is sound (`!arr[i]` does not compile in Enforce Script; use
# `arr[i] == 0`; `!arr[i].Method()` is excluded and compiles). The detector
# has no tests and has not passed review. Wiring it would repeat BUG-014
# (unreviewed detectors produced ~65% false positives).
# To wire: add tests for tests/fixtures/es/*negate_array*, review the regex
# against a real corpus, then import and call it from script_validator.py.

import re


ES_NEGATE_ARRAY_ELEMENT_RULE_ID = "ES-NEGATE-ARRAY-ELEMENT"


# pitfalls-advanced.md:16-24 — `!arr[i]` does not compile in Enforce Script.
# The correct form is an explicit comparison (`arr[i] == 0`).
# The negative lookahead `(?!\s*\.)` excludes `!arr[i].Method()` / `!arr[i].field`
# (there the `!` negates the call/field result, which compiles). The trailing
# lookahead requires an expression boundary after `]`.
ES_NEGATE_ARRAY_ELEMENT_RE = re.compile(
    r"!\s*[\w.]+\[[^\]]*\]"
    r"(?!\s*\.)"
    r"(?=\s*(?:\)|\]|&&|\|\||;|,|==|!=|<=|>=|<|>|$))"
)


ES_NEGATE_ARRAY_ELEMENT_MESSAGE = (
    "[FAIL] {rel_path} line {line}: logical negation of an array element "
    "(`!arr[i]`) does not compile in Enforce Script (pitfalls-advanced.md:16-24). "
    "Use an explicit comparison such as `arr[i] == 0`."
)


def check_es_negate_array_element(stripped_source, rel_path):
    errors = []

    for match in ES_NEGATE_ARRAY_ELEMENT_RE.finditer(stripped_source):
        line_number = stripped_source.count("\n", 0, match.start()) + 1
        message = ES_NEGATE_ARRAY_ELEMENT_MESSAGE.format(
            rel_path=rel_path, line=line_number
        )
        errors.append(
            {
                "check": ES_NEGATE_ARRAY_ELEMENT_RULE_ID,
                "file": rel_path,
                "line": line_number,
                "message": message,
                "severity": "FAIL",
                "rule_id": ES_NEGATE_ARRAY_ELEMENT_RULE_ID,
            }
        )

    return errors
