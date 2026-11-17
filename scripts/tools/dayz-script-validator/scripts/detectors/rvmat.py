import re


RVMAT_RULE_ID = "RVMAT-NO-NORMALMAPMACRO"


RVMAT_SHADER_RE = re.compile(
    r"^\s*shader\s*=\s*NormalMapMacro\s*;",
    re.IGNORECASE,
)


RVMAT_MESSAGE = (
    "[FAIL] {rel_path} line {line}: rvmat uses 'shader = NormalMapMacro;'. "
    "Causes dedicated server crash at model load (pitfalls-advanced.md:99). "
    "Replace with 'shader = Super;'."
)


def strip_rvmat_line_comment(line):
    marker = line.find("//")
    if marker == -1:
        return line
    return line[:marker]


def check_rvmat_normalmapmacro(text, rel_path):
    errors = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        check_line = strip_rvmat_line_comment(line)
        if RVMAT_SHADER_RE.search(check_line):
            message = RVMAT_MESSAGE.format(rel_path=rel_path, line=line_number)
            errors.append(
                {
                    "check": RVMAT_RULE_ID,
                    "file": rel_path,
                    "line": line_number,
                    "message": message,
                    "severity": "FAIL",
                    "rule_id": RVMAT_RULE_ID,
                }
            )

    return errors
