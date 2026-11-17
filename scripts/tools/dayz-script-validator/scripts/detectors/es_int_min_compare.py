import re


ES_INT_MIN_COMPARE_RULE_ID = "ES-INT-MIN-COMPARISON"


# Engine bug pitfalls-advanced.md:5-14 — `1 < int.MIN` returns TRUE due to
# integer overflow in the comparison operator. Detect comparisons against
# either the symbolic `int.MIN` or its literal value `-2147483648`.
#
# Note: `-2147483647` is the example shown in the source ("also returns TRUE")
# but is NOT actually int.MIN (which is -2147483648). We flag both because the
# source explicitly demonstrates both as broken.
ES_INT_MIN_COMPARE_RE = re.compile(
    r"""
    (?:
        (?:<=|>=|<|>)\s*int\.MIN\b
      |
        \bint\.MIN\s*(?:<=|>=|<|>)
      |
        (?:<=|>=|<|>)\s*-?2147483648\b
      |
        \b-?2147483648\s*(?:<=|>=|<|>)
      |
        (?:<=|>=|<|>)\s*-?2147483647\b
      |
        \b-?2147483647\s*(?:<=|>=|<|>)
    )
    """,
    re.VERBOSE,
)


ES_INT_MIN_COMPARE_MESSAGE = (
    "[WARN] {rel_path} line {line}: comparison against int.MIN "
    "(-2147483648). Engine bug: `1 < int.MIN` returns TRUE due to integer "
    "overflow in the comparison logic (pitfalls-advanced.md:5-14). Use a "
    "different sentinel value or split the check."
)


def check_es_int_min_compare(stripped_source, rel_path):
    warnings = []

    for match in ES_INT_MIN_COMPARE_RE.finditer(stripped_source):
        line_number = stripped_source.count("\n", 0, match.start()) + 1
        message = ES_INT_MIN_COMPARE_MESSAGE.format(
            rel_path=rel_path, line=line_number
        )
        warnings.append(
            {
                "check": ES_INT_MIN_COMPARE_RULE_ID,
                "file": rel_path,
                "line": line_number,
                "message": message,
                "severity": "WARN",
                "rule_id": ES_INT_MIN_COMPARE_RULE_ID,
            }
        )

    return warnings
