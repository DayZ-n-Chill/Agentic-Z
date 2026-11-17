import re

from shared.method_recognition import find_block_end_line


ES_ATTACHMENTS_APPEND_CROSSPBO_RULE_ID = "ES-ATTACHMENTS-COMPOUND-APPEND-CROSSPBO"


# kt_roadkill_armed bug-007 (verified with CfgConvert -xml). `attachments[] +=`
# in a class whose parent is defined in ANOTHER PBO (external / forward-only)
# does not reliably inherit the base list -> the effective config keeps only the
# appended items and ALL vehicle slots break. Materialize the full list instead.
_CLASS_HEADER_RE = re.compile(r"^\s*class\s+(?P<name>\w+)(?:\s*:\s*(?P<parent>\w+))?")
_ATTACH_APPEND_RE = re.compile(r"attachments\s*\[\s*\]\s*\+=")


ES_ATTACHMENTS_APPEND_CROSSPBO_MESSAGE = (
    "[WARN] {rel_path} line {line}: `attachments[] +=` in class '{name}' whose "
    "parent '{parent}' is not defined in this config (external/cross-PBO). "
    "Compound-append over a cross-PBO parent may not materialize the inherited "
    "list, breaking all attachment slots. Declare the full list with `=`."
)


def _classify_config_classes(lines):
    """Return list of dicts: name, parent, has_body, header_index, brace_index."""
    classes = []
    i = 0
    while i < len(lines):
        header = _CLASS_HEADER_RE.match(lines[i])
        if not header or not re.match(r"^\s*class\s+\w+", lines[i]):
            i += 1
            continue

        # accumulate until we hit '{' (body) or ';' (forward decl)
        buf = lines[i]
        j = i
        while "{" not in buf and ";" not in buf and j + 1 < len(lines):
            j += 1
            buf += " " + lines[j]

        brace_pos = buf.find("{")
        semi_pos = buf.find(";")
        has_body = brace_pos != -1 and (semi_pos == -1 or brace_pos < semi_pos)

        brace_index = None
        if has_body:
            for k in range(i, j + 1):
                if "{" in lines[k]:
                    brace_index = k
                    break

        classes.append(
            {
                "name": header.group("name"),
                "parent": header.group("parent"),
                "has_body": has_body,
                "header_index": i,
                "brace_index": brace_index,
            }
        )
        i += 1

    return classes


def check_es_attachments_compound_append(config_source, rel_path):
    lines = config_source.split("\n")
    classes = _classify_config_classes(lines)
    defined_with_body = {c["name"] for c in classes if c["has_body"]}

    warnings = []
    for cls in classes:
        parent = cls["parent"]
        if not cls["has_body"] or parent is None:
            continue
        if parent in defined_with_body:
            continue  # local parent (same PBO) -> append is reliable

        end_line = find_block_end_line(lines, cls["brace_index"])  # 1-based close
        for k in range(cls["brace_index"] + 1, end_line):
            if k >= len(lines):
                break
            if _ATTACH_APPEND_RE.search(lines[k]):
                line_number = k + 1
                warnings.append(
                    {
                        "check": ES_ATTACHMENTS_APPEND_CROSSPBO_RULE_ID,
                        "file": rel_path,
                        "line": line_number,
                        "message": ES_ATTACHMENTS_APPEND_CROSSPBO_MESSAGE.format(
                            rel_path=rel_path, line=line_number,
                            name=cls["name"], parent=parent,
                        ),
                        "severity": "WARN",
                        "rule_id": ES_ATTACHMENTS_APPEND_CROSSPBO_RULE_ID,
                    }
                )
    return warnings
