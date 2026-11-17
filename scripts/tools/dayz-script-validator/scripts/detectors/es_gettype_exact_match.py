import re


ES_GETTYPE_EXACT_MATCH_RULE_ID = "ES-GETTYPE-EXACT-MATCH"


# `.GetType() ==` / `.GetType() !=` falls on inherited/modded variants. The
# server-side RPC handler will silently reject actions whose client-side
# ActionCondition uses `IsKindOf`. Documented in pitfalls-advanced.md:257-274
# and SKILL.md:84-85 (rules 31 and 32).
#
# Phase 1 covers only the direct form: `.GetType() ==` or `.GetType() !=`
# immediately followed by the comparison. The "via intermediate variable"
# variant (`string h = obj.GetType(); ... h == "X"`) is a known false negative
# of phase 1; promotion to phase 2 with method-aware tracking.
ES_GETTYPE_EXACT_MATCH_RE = re.compile(
    r"\.GetType\s*\(\s*\)\s*(?:==|!=)"
)


ES_GETTYPE_ENUM_COMPARISON_RE = re.compile(
    r"\s*(?P<container>\w+)\s*\.\s*\w+"
)


ES_GETTYPE_ENUM_CONTAINERS = {"InventoryLocationType"}


ES_GETTYPE_EXACT_MATCH_MESSAGE = (
    "[WARN] {rel_path} line {line}: `.GetType()` compared with `==`/`!=`. "
    "Exact match fails on inherited or modded variants; the server may "
    "silently reject actions whose client check uses IsKindOf "
    "(pitfalls-advanced.md:257-274, SKILL.md rules 31-32). Use "
    "`obj.IsKindOf(\"TypeName\")` for full inheritance-chain checks."
)


def gettype_match_is_allowed_enum_compare(stripped_source, match):
    operand_match = ES_GETTYPE_ENUM_COMPARISON_RE.match(stripped_source, match.end())
    if operand_match is None:
        return False
    return operand_match.group("container") in ES_GETTYPE_ENUM_CONTAINERS


def check_es_gettype_exact_match(stripped_source, rel_path):
    warnings = []

    for match in ES_GETTYPE_EXACT_MATCH_RE.finditer(stripped_source):
        if gettype_match_is_allowed_enum_compare(stripped_source, match):
            continue
        line_number = stripped_source.count("\n", 0, match.start()) + 1
        message = ES_GETTYPE_EXACT_MATCH_MESSAGE.format(
            rel_path=rel_path, line=line_number
        )
        warnings.append(
            {
                "check": ES_GETTYPE_EXACT_MATCH_RULE_ID,
                "file": rel_path,
                "line": line_number,
                "message": message,
                "severity": "WARN",
                "rule_id": ES_GETTYPE_EXACT_MATCH_RULE_ID,
            }
        )

    return warnings
