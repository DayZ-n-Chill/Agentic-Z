import re

from shared.control_flow import (
    compute_ifdef_then_else_path,
    ifdef_paths_are_exclusive,
)
from shared.method_recognition import find_method_regions


ES_LOCAL_VAR_REDECLARE_RULE_ID = "ES-LOCAL-VAR-REDECLARE"


# pitfalls-advanced.md:320-362 — Enforce gives function scope to ALL local
# declarations (no block scope). Declaring the same local name twice in one
# method ("multiple declaration") is a compile error: sibling if/else
# declarations, or an outer local shadowed by a `for (Type name ...)` init.
#
# Leading keywords that look like a "Type name" declaration but are not.
_NON_TYPE = {
    "return", "if", "else", "for", "while", "foreach", "switch", "case",
    "default", "break", "continue", "delete", "new", "super", "this", "do",
    "typedef", "class", "enum", "modded", "override", "import", "thread",
}

# Plain local declaration at statement start: optional storage qualifiers,
# a type (optionally templated), a name, then `;`, `=` or `,`.
_DECL_RE = re.compile(
    r"^\s*"
    r"(?:(?:ref|autoptr|const|auto|local|out|inout)\s+)*"
    r"(?P<type>[A-Za-z_]\w*(?:\s*<[^;{}]*>)?)"
    r"\s+"
    r"(?P<name>[A-Za-z_]\w*)"
    r"\s*(?:;|=(?!=)|,)"
)

# Declaration inside a for-init: `for (Type name = ...` / `for (Type name;`
_FOR_INIT_RE = re.compile(
    r"\bfor\s*\(\s*"
    r"(?:(?:ref|const)\s+)*"
    r"[A-Za-z_]\w*(?:\s*<[^;{}]*>)?"
    r"\s+"
    r"(?P<name>[A-Za-z_]\w*)"
    r"\s*(?:=(?!=)|;)"
)


ES_LOCAL_VAR_REDECLARE_MESSAGE = (
    "[FAIL] {rel_path} line {line}: local variable '{name}' is re-declared in "
    "the same method. Enforce Script uses function scope for all locals (no "
    "block scope), so this is a compile error 'multiple declaration' "
    "(pitfalls-advanced.md:320-362). Declare it once and reuse it."
)


def _leading_type_is_real(match):
    return match.group("type").split("<")[0].strip() not in _NON_TYPE


def check_es_local_var_redeclare(stripped_source, rel_path):
    errors = []
    lines = stripped_source.split("\n")
    methods = find_method_regions(stripped_source)

    for method in methods:
        # Collect (name, line, is_for_init) for declarations in the method body.
        decls = []
        for line_index in range(method["start_line"], method["end_line"]):
            # skip the signature line itself
            if line_index == method["start_line"]:
                continue
            line = lines[line_index - 1]
            path = compute_ifdef_then_else_path(lines, line_index - 1)

            for_match = _FOR_INIT_RE.search(line)
            if for_match:
                decls.append((for_match.group("name"), line_index, True, path))
                continue

            decl_match = _DECL_RE.match(line)
            if decl_match and _leading_type_is_real(decl_match):
                decls.append((decl_match.group("name"), line_index, False, path))

        by_name = {}
        for name, line_no, is_for, path in decls:
            by_name.setdefault(name, []).append((line_no, is_for, path))

        for name, occurrences in by_name.items():
            if len(occurrences) < 2:
                continue
            # Conservative: only flag when at least one occurrence is a plain
            # (non-for-init) declaration. Pure for/for reuse is left untouched.
            if all(is_for for _, is_for, _ in occurrences):
                continue
            previous = [occurrences[0]]
            for line_no, is_for, path in occurrences[1:]:
                can_coexist = any(
                    not ifdef_paths_are_exclusive(prev_path, path)
                    for _, _, prev_path in previous
                )
                previous.append((line_no, is_for, path))
                if not can_coexist:
                    continue
                errors.append(
                    {
                        "check": ES_LOCAL_VAR_REDECLARE_RULE_ID,
                        "file": rel_path,
                        "line": line_no,
                        "message": ES_LOCAL_VAR_REDECLARE_MESSAGE.format(
                            rel_path=rel_path, line=line_no, name=name
                        ),
                        "severity": "FAIL",
                        "rule_id": ES_LOCAL_VAR_REDECLARE_RULE_ID,
                    }
                )

    return errors
