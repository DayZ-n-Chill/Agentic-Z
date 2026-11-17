import re


ES_REF_AUTOPTR_COMBINED_RULE_ID = "ES-REF-AUTOPTR-COMBINED"


# enforce-script-reference SKILL.md:38 (rule 13, under section header :21
# "Syntax Restrictions (compiler enforced or runtime crash)"):
# "Never combine `ref` and `autoptr` on the same field — pick one".
# Match the two qualifiers adjacent (the leading qualifiers of a field
# declaration). Adjacency excludes the legitimate generic forms
# `ref array<autoptr T>` / `autoptr array<ref T>`, where the qualifiers are
# separated by the `<...>` and never sit next to each other.
ES_REF_AUTOPTR_COMBINED_RE = re.compile(
    r"\b(?:ref\s+autoptr|autoptr\s+ref)\b"
)


ES_REF_AUTOPTR_COMBINED_MESSAGE = (
    "[WARN] {rel_path} line {line}: `ref` and `autoptr` combined on the same "
    "field declaration. Enforce allows only one strong-reference qualifier "
    "per field — pick one (enforce-script-reference SKILL.md:38). "
    "`ref array<autoptr T>` (separated by a generic) is valid and not flagged."
)


def check_es_ref_autoptr_combined(stripped_source, rel_path):
    warnings = []

    for match in ES_REF_AUTOPTR_COMBINED_RE.finditer(stripped_source):
        line_number = stripped_source.count("\n", 0, match.start()) + 1
        message = ES_REF_AUTOPTR_COMBINED_MESSAGE.format(
            rel_path=rel_path, line=line_number
        )
        warnings.append(
            {
                "check": ES_REF_AUTOPTR_COMBINED_RULE_ID,
                "file": rel_path,
                "line": line_number,
                "message": message,
                "severity": "WARN",
                "rule_id": ES_REF_AUTOPTR_COMBINED_RULE_ID,
            }
        )

    return warnings
