import re

from shared.method_recognition import (
    collect_method_signature,
    find_method_regions,
)
from shared.vanilla_reference import override_param_names


ES_OVERRIDE_PARAM_NAME_MISMATCH_RULE_ID = "ES-OVERRIDE-PARAM-NAME-MISMATCH"


# animatedactionbase.c:175 + kt_roadkill_armed_dev bug-006. Enforce requires an
# override's parameter NAMES to match the base signature exactly (unlike
# C++/C#/Java). A mismatch -> 'Can't find variable X' when the param is used.
_OVERRIDE_RE = re.compile(r"\boverride\b")
_PARAM_NAME_RE = re.compile(r"(?P<name>[A-Za-z_]\w*)\s*$")


ES_OVERRIDE_PARAM_NAME_MISMATCH_MESSAGE = (
    "[FAIL] {rel_path} line {line}: override '{method}' parameter '{got}' must "
    "be named '{want}' to match the vanilla base signature (Enforce binds "
    "override params by name). Rename it to '{want}'."
)


def _param_name(param):
    param = param.strip()
    if not param:
        return None
    # Default values (`bool updateCached = true`, `ActionData data = NULL`)
    # are not the parameter name. Stripping them keeps the name-binding check
    # aligned with Enforce and avoids treating `true`/`NULL` as names.
    param = re.sub(r"=.*$", "", param).strip()
    param = re.sub(r"\[\d*\]\s*$", "", param).strip()
    if not param:
        return None
    match = _PARAM_NAME_RE.search(param)
    return match.group("name") if match else None


def check_es_override_param_name_mismatch(stripped_source, rel_path):
    errors = []
    lines = stripped_source.split("\n")

    for method in find_method_regions(stripped_source):
        expected = override_param_names(method["name"])
        if expected is None:
            continue

        signature, _ = collect_method_signature(lines, method["start_line"] - 1)
        if not _OVERRIDE_RE.search(signature):
            continue

        got_names = [
            _param_name(part) for part in method["params"].split(",")
        ]
        got_names = [n for n in got_names if n]
        if len(got_names) != len(expected):
            continue  # arity differs -> not the same override, skip conservatively

        for position, (got, want) in enumerate(zip(got_names, expected)):
            if got != want:
                errors.append(
                    {
                        "check": ES_OVERRIDE_PARAM_NAME_MISMATCH_RULE_ID,
                        "file": rel_path,
                        "line": method["start_line"],
                        "message": ES_OVERRIDE_PARAM_NAME_MISMATCH_MESSAGE.format(
                            rel_path=rel_path, line=method["start_line"],
                            method=method["name"], got=got, want=want,
                        ),
                        "severity": "FAIL",
                        "rule_id": ES_OVERRIDE_PARAM_NAME_MISMATCH_RULE_ID,
                    }
                )

    return errors
