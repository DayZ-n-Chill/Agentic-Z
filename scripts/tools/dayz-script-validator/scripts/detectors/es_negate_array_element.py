# QUARANTINED — not imported by script_validator.py and not executed.
# The premise is FALSE. `!arr[i]` compiles in Enforce Script: vanilla negates
# an array<int> element in code that ships -
#   4_world/classes/basebuilding/constructionpart.c:549
#     if (!animSourceBehaviorInvetrtedOverrides[i])
# (the array is declared at :541; the same form appears at :572, :595, :647).
# See pitfalls-advanced.md, section "Comparisons and control flow".
# The file remains as a record of the rejected rule. Do not re-wire it.

import re


ES_NEGATE_ARRAY_ELEMENT_RULE_ID = "ES-NEGATE-ARRAY-ELEMENT"


# Rejected rule: it claimed `!arr[i]` does not compile. It does (see the
# header). The negative lookahead `(?!\s*\.)` excludes `!arr[i].Method()` / `!arr[i].field`
# (there the `!` negates the call/field result, which compiles). The trailing
# lookahead requires an expression boundary after `]`.
ES_NEGATE_ARRAY_ELEMENT_RE = re.compile(
    r"!\s*[\w.]+\[[^\]]*\]"
    r"(?!\s*\.)"
    r"(?=\s*(?:\)|\]|&&|\|\||;|,|==|!=|<=|>=|<|>|$))"
)


ES_NEGATE_ARRAY_ELEMENT_MESSAGE = (
    "[FAIL] {rel_path} line {line}: logical negation of an array element "
    "(`!arr[i]`). Rejected rule kept for the record: this form compiles "
    "(vanilla constructionpart.c:549), so this message is never reported."
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
