import re

from shared.control_flow import compute_ifdef_stack_at
from shared.method_recognition import (
    collect_method_signature,
    find_block_end_line,
    find_method_regions,
)
from shared.vanilla_reference import platform_gated_method


ES_OVERRIDE_OF_PLATFORM_GATED_METHOD_RULE_ID = (
    "ES-OVERRIDE-OF-PLATFORM-GATED-METHOD"
)


# Vanilla sometimes declares a method only inside a preprocessor guard that a
# PC+RELEASE compile does not define. The method is then absent from the
# compiled base class. An `override` in a mod that is not wrapped in the same
# guard fails with `no function to override in base class`, the whole module
# is dropped, and the client freezes on the loading screen -- no crash and no
# useful RPT line.
#
# Coverage comes from a curated table (vanilla_reference). Partial on
# purpose: unknown gated methods are false negatives; an entry is added only
# when the vanilla declaration and its guard are cited, so this check does
# not invent positives.
#
# A hit requires all of: the method name is in the table, the signature
# contains `override`, the enclosing class is the tabulated owner (or
# extends it), and the ifdef stack at the signature does not include
# `#ifdef <macro>`. Other classes that happen to reuse the method name are
# left alone.
_CLASS_HEADER_RE = re.compile(
    r"^\s*(?:modded\s+)?class\s+(?P<name>\w+)"
    + r"(?:\s*:\s*(?P<base_colon>\w+)|\s+extends\s+(?P<base_ext>\w+))?"
)

_OVERRIDE_RE = re.compile(r"\boverride\b")


ES_OVERRIDE_OF_PLATFORM_GATED_METHOD_MESSAGE = (
    "[FAIL] {rel_path} line {line}: override of `{owner}.{method}` is not "
    "wrapped in `#ifdef {macro}`. Vanilla declares that method only under "
    "that guard ({citation}). On a PC+RELEASE compile the base method is "
    "absent, so the override fails with `no function to override in base "
    "class`, the module is dropped, and the client freezes on the loading "
    "screen (no crash, no useful RPT line). Wrap the override in "
    "`#ifdef {macro}`."
)


def _iter_classes(lines):
    index = 0
    while index < len(lines):
        header = _CLASS_HEADER_RE.match(lines[index])
        if not header:
            index += 1
            continue

        brace_index = None
        for probe in range(index, min(index + 4, len(lines))):
            if "{" in lines[probe]:
                brace_index = probe
                break
        if brace_index is None:
            index += 1
            continue

        end_line = find_block_end_line(lines, brace_index)
        yield {
            "name": header.group("name"),
            "base": header.group("base_colon") or header.group("base_ext"),
            "start_line": index + 1,
            "end_line": end_line,
        }
        index = end_line if end_line > index else index + 1


def _class_containing(classes, line_number):
    containing = [
        item
        for item in classes
        if item["start_line"] <= line_number <= item["end_line"]
    ]
    if not containing:
        return None
    return max(containing, key=lambda item: item["start_line"])


def _class_owns_entry(klass, owner):
    if klass is None:
        return False
    if klass["name"] == owner:
        return True
    return klass["base"] == owner


def _ifdef_stack_has_macro(stack, macro):
    for frame in stack:
        if frame.get("directive") == "ifdef" and frame.get("macro") == macro:
            return True
    return False


def check_es_override_of_platform_gated_method(stripped_source, rel_path):
    errors = []
    lines = stripped_source.split("\n")
    classes = list(_iter_classes(lines))

    for method in find_method_regions(stripped_source):
        entry = platform_gated_method(method["name"])
        if entry is None:
            continue

        signature, _ = collect_method_signature(lines, method["start_line"] - 1)
        if not _OVERRIDE_RE.search(signature):
            continue

        klass = _class_containing(classes, method["start_line"])
        if not _class_owns_entry(klass, entry["owner"]):
            continue

        stack = compute_ifdef_stack_at(lines, method["start_line"] - 1)
        if _ifdef_stack_has_macro(stack, entry["macro"]):
            continue

        message = ES_OVERRIDE_OF_PLATFORM_GATED_METHOD_MESSAGE.format(
            rel_path=rel_path,
            line=method["start_line"],
            owner=entry["owner"],
            method=method["name"],
            macro=entry["macro"],
            citation=entry["citation"],
        )
        errors.append(
            {
                "check": ES_OVERRIDE_OF_PLATFORM_GATED_METHOD_RULE_ID,
                "file": rel_path,
                "line": method["start_line"],
                "message": message,
                "severity": "FAIL",
                "rule_id": ES_OVERRIDE_OF_PLATFORM_GATED_METHOD_RULE_ID,
            }
        )

    return errors
