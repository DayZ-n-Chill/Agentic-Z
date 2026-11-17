import re

from shared.method_recognition import find_block_end_line, find_method_regions
from shared.vanilla_reference import base_member_set


ES_MEMBER_REDECLARE_BASE_RULE_ID = "ES-MEMBER-REDECLARE-BASE"


# carscript.c:266 + kt_roadkill_armed_dev bug-004. A `class X extends <base>` or
# `modded class <base>` that re-declares a member variable already declared in
# the vanilla base chain -> compile error 'Multiple declaration of variable X'.
_CLASS_HEADER_RE = re.compile(
    r"^\s*(?:modded\s+)?class\s+(?P<name>\w+)"
    r"(?:\s*:\s*(?P<base_colon>\w+)|\s+extends\s+(?P<base_ext>\w+))?"
)

_MEMBER_RE = re.compile(
    r"^\s*"
    r"(?:(?:protected|private|static|ref|autoptr|const|proto|native)\s+)*"
    r"[A-Za-z_]\w*(?:\s*<[^;{}]*>)?"
    r"\s+"
    r"(?P<name>m_\w+)"
    r"\s*(?:;|=(?!=))"
)


ES_MEMBER_REDECLARE_BASE_MESSAGE = (
    "[FAIL] {rel_path} line {line}: member variable '{name}' is already declared "
    "in the vanilla base '{base}' (compile error 'Multiple declaration of "
    "variable {name}'). Remove the re-declaration; the base already provides it."
)


def _is_modded(line):
    return re.match(r"^\s*modded\s+class\b", line) is not None


def check_es_member_redeclare_base(stripped_source, rel_path):
    errors = []
    lines = stripped_source.split("\n")
    method_regions = find_method_regions(stripped_source)

    def inside_method(line_no):
        return any(
            m["start_line"] <= line_no <= m["end_line"] for m in method_regions
        )

    index = 0
    while index < len(lines):
        header = _CLASS_HEADER_RE.match(lines[index])
        if not header:
            index += 1
            continue

        # locate opening brace line
        brace_index = None
        for j in range(index, min(index + 4, len(lines))):
            if "{" in lines[j]:
                brace_index = j
                break
        if brace_index is None:
            index += 1
            continue

        end_line = find_block_end_line(lines, brace_index)  # 1-based close line

        # effective base whose members we check against
        if _is_modded(lines[index]):
            effective_base = header.group("name")
        else:
            effective_base = header.group("base_colon") or header.group("base_ext")

        members = base_member_set(effective_base) if effective_base else set()
        if members:
            for line_no in range(brace_index + 2, end_line):  # body lines, 1-based
                if inside_method(line_no):
                    continue
                body_line = lines[line_no - 1]
                # Destructor bodies are not method-regions (`void ~Class()`),
                # so `delete m_Root;` would otherwise look like a member decl.
                if re.match(r"^\s*(?:delete|return|break|continue)\b", body_line):
                    continue
                m = _MEMBER_RE.match(body_line)
                if m and m.group("name") in members:
                    name = m.group("name")
                    errors.append(
                        {
                            "check": ES_MEMBER_REDECLARE_BASE_RULE_ID,
                            "file": rel_path,
                            "line": line_no,
                            "message": ES_MEMBER_REDECLARE_BASE_MESSAGE.format(
                                rel_path=rel_path, line=line_no,
                                name=name, base=effective_base,
                            ),
                            "severity": "FAIL",
                            "rule_id": ES_MEMBER_REDECLARE_BASE_RULE_ID,
                        }
                    )
        index = end_line if end_line > index else index + 1

    return errors
