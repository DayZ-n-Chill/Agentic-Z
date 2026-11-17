import re

from detectors.es_cast_unrelated_types import Hierarchy
from detectors.es_undeclared_static_member import class_bodies
from detectors.es_variable_named_as_type import usable_vanilla_key, vanilla_sources
from shared.control_flow import (
    compute_ifdef_stack_at,
    find_server_ifdef_block_for_line,
    ifdef_stack_is_definitely_server_side,
    line_is_inside_server_if_guard,
)
from shared.method_recognition import (
    find_block_end_line,
    find_method_for_line,
    find_method_regions,
)
from stripper import strip_enforce_comments_and_strings


ES_SYNCVAR_RULE_ID = "ES-SYNCVAR-CONTRACT"


ES_SYNCVAR_UNSUPPORTED_RULE_ID = "ES-SYNCVAR-UNSUPPORTED-PATTERN"


ES_SYNCVAR_CLASS_UNKNOWN_RULE_ID = "ES-SYNCVAR-CLASS-UNKNOWN"


ES_SYNCVAR_CONSTRUCTION_HOOK = "RegisterConstructionSyncVariables"


ES_SYNCVAR_REGISTER_RE = re.compile(
    r"\bRegisterNetSyncVariable(?:Bool|Int|Float)?\s*\(\s*\"(?P<var>[^\"]+)\""
)


ES_SYNCVAR_REGISTER_CALL_RE = re.compile(
    r"\bRegisterNetSyncVariable(?:Bool|Int|Float)?"
)


ES_SYNCVAR_CLASS_HEADER_RE = re.compile(
    r"^\s*(?:modded\s+)?class\s+(?P<class>\w+)"
    r"(?:\s*(?::|extends)\s+\w+)?\s*\{"
)


ES_SYNCVAR_CLASS_HEADER_NEXT_LINE_RE = re.compile(
    r"^\s*(?:modded\s+)?class\s+(?P<class>\w+)"
    r"(?:\s*(?::|extends)\s+\w+)?\s*$"
)


ES_SYNCVAR_CLASS_CANDIDATE_RE = re.compile(r"^\s*(?:modded\s+)?class\s+\w+")


ES_SYNCVAR_SET_DIRTY_RE = re.compile(r"\bSetSynchDirty\s*\(\s*\)")


ES_SYNCVAR_REGISTER_OUTSIDE_CTOR_MESSAGE = (
    "[FAIL] {rel_path} line {line}: RegisterNetSyncVariable*('{var}') called "
    "outside constructor. SyncVars must register in constructor "
    "(networking.md:42)."
)


ES_SYNCVAR_WRITE_NO_IFDEF_MESSAGE = (
    "[FAIL] {rel_path} line {line}: SyncVar '{var}' assigned outside '#ifdef "
    "SERVER'. Write must be server-only (SKILL.md rule 17, networking.md:59)."
)


ES_SYNCVAR_WRITE_NO_DIRTY_MESSAGE = (
    "[FAIL] {rel_path} line {line}: SyncVar '{var}' assigned inside '#ifdef "
    "SERVER' but missing 'SetSynchDirty()' in the same block. Clients won't "
    "see the change (networking.md:59)."
)


ES_SYNCVAR_ALT_GUARD_UNSUPPORTED_MESSAGE = (
    "[WARN] {rel_path} line {line}: SyncVar '{var}' assigned inside "
    "alternative guard 'if (GetGame().IsServer())' (or equivalent); phase 1 "
    "only supports '#ifdef SERVER' literal. Move write under #ifdef SERVER or "
    "accept this as known limitation."
)


ES_SYNCVAR_IFDEF_BRANCH_UNSUPPORTED_MESSAGE = (
    "[WARN] {rel_path} line {line}: SyncVar '{var}' assigned inside unsupported "
    "preprocessor branch; phase 1 treats #else/#elif under '#ifdef SERVER' as "
    "unsupported. Move write under literal '#ifdef SERVER' branch or accept "
    "this as known limitation."
)


ES_SYNCVAR_METHOD_UNPARSED_UNSUPPORTED_MESSAGE = (
    "[WARN] {rel_path} line {line}: SyncVar '{var}' assigned inside '#ifdef "
    "SERVER', but method enclosing the assignment could not be parsed (likely "
    "generic return type); set dirty check skipped."
)


ES_SYNCVAR_CLASS_UNKNOWN_MESSAGE = (
    "[WARN] {rel_path} line {line}: class declaration not recognized; SyncVar "
    "checks skipped for this block (rule_id: ES-SYNCVAR-CLASS-UNKNOWN)."
)


def build_es_syncvar_error(rel_path, line_number, var_name, message_template):
    message = message_template.format(
        rel_path=rel_path,
        line=line_number,
        var=var_name,
    )
    return {
        "check": ES_SYNCVAR_RULE_ID,
        "file": rel_path,
        "line": line_number,
        "message": message,
        "severity": "FAIL",
        "rule_id": ES_SYNCVAR_RULE_ID,
    }


def build_es_syncvar_unsupported_warning(
    rel_path, line_number, var_name, message_template
):
    message = message_template.format(
        rel_path=rel_path,
        line=line_number,
        var=var_name,
    )
    return {
        "check": ES_SYNCVAR_UNSUPPORTED_RULE_ID,
        "file": rel_path,
        "line": line_number,
        "message": message,
        "severity": "WARN",
        "rule_id": ES_SYNCVAR_UNSUPPORTED_RULE_ID,
    }


def build_es_syncvar_class_unknown_warning(rel_path, line_number):
    return {
        "check": ES_SYNCVAR_CLASS_UNKNOWN_RULE_ID,
        "file": rel_path,
        "line": line_number,
        "message": ES_SYNCVAR_CLASS_UNKNOWN_MESSAGE.format(
            rel_path=rel_path,
            line=line_number,
        ),
        "severity": "WARN",
        "rule_id": ES_SYNCVAR_CLASS_UNKNOWN_RULE_ID,
    }


def syncvar_register_match_is_code(match, stripped_source):
    call_match = ES_SYNCVAR_REGISTER_CALL_RE.match(match.group(0))
    if call_match is None:
        return False
    return stripped_source.startswith(call_match.group(0), match.start())


def find_es_syncvar_registers(source, stripped_source):
    registers = []
    for match in ES_SYNCVAR_REGISTER_RE.finditer(source):
        if not syncvar_register_match_is_code(match, stripped_source):
            continue
        line_number = stripped_source.count("\n", 0, match.start()) + 1
        registers.append(
            {
                "line": line_number,
                "var": match.group("var"),
                "start": match.start(),
            }
        )
    return registers


def find_unknown_class_brace_line(lines, start_index):
    if "{" in lines[start_index]:
        return start_index

    for index in range(start_index + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped == "":
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("{"):
            return index
        return start_index

    return start_index


def range_contains_register(registers, start_line, end_line):
    for register in registers:
        if start_line <= register["line"] <= end_line:
            return True
    return False


def find_es_syncvar_classes(stripped_source, registers, rel_path):
    lines = stripped_source.split("\n")
    classes = []
    warnings = []

    for index, line in enumerate(lines):
        if not ES_SYNCVAR_CLASS_CANDIDATE_RE.match(line):
            continue

        supported_match = ES_SYNCVAR_CLASS_HEADER_RE.match(line)
        if supported_match:
            end_line = find_block_end_line(lines, index)
            classes.append(
                {
                    "class": supported_match.group("class"),
                    "start_line": index + 1,
                    "end_line": end_line,
                }
            )
            continue

        next_line_match = ES_SYNCVAR_CLASS_HEADER_NEXT_LINE_RE.match(line)
        if next_line_match:
            brace_line_index = find_unknown_class_brace_line(lines, index)
            if brace_line_index != index and lines[brace_line_index].strip() == "{":
                end_line = find_block_end_line(lines, brace_line_index)
                classes.append(
                    {
                        "class": next_line_match.group("class"),
                        "start_line": index + 1,
                        "end_line": end_line,
                    }
                )
                continue

        brace_line_index = find_unknown_class_brace_line(lines, index)
        end_line = find_block_end_line(lines, brace_line_index)
        if range_contains_register(registers, index + 1, end_line):
            warnings.append(
                build_es_syncvar_class_unknown_warning(rel_path, index + 1)
            )

    return classes, warnings


def vanilla_declares_construction_hook(vanilla_root):
    """Whether the vanilla tree's EntityAI declares the construction hook.

    DayZ 1.30 does (3_game/entities/entityai.c:3481); 1.29 does not. Only a
    method of EntityAI counts, read with strings stripped as well as comments:
    a field or a string of that name does not, and a brace in a string does
    not hide the method. Without a usable vanilla tree the answer is False, so
    the rule keeps the behaviour it has on 1.29, the build the pack is
    anchored on.
    """
    vanilla_key = usable_vanilla_key(vanilla_root)
    if vanilla_key is None:
        return False
    for _rel_path, text in vanilla_sources(vanilla_key):
        if ES_SYNCVAR_CONSTRUCTION_HOOK not in text:
            continue
        stripped, _warnings = strip_enforce_comments_and_strings(text)
        for match, span in class_bodies(stripped):
            if match.group("name") != "EntityAI" or span is None:
                continue
            body = stripped[span[0] + 1:span[1]]
            if any(
                method["name"] == ES_SYNCVAR_CONSTRUCTION_HOOK
                for method in find_method_regions(body)
            ):
                return True
    return False


def method_is_syncvar_registration_target(
    method, class_name, lines, construction_hook
):
    if method is None:
        return False
    if method["name"] in (
        class_name,
        "Init",
        "InitItemSounds",
        "InitItemVariables",
    ):
        return True
    # DayZ 1.30: EntityAI() calls ConstructionInit() when the type's
    # CfgVehicles entry has a Construction class
    # (3_game/entities/entityai.c:248-249), which calls this hook (:3469);
    # BuildingBase registers its m_SyncParts ints in its override
    # (4_world/entities/game/super/building.c:29-44). Only an override is that
    # hook, with no parameters as EntityAI declares it (:3481), and only when
    # the vanilla tree declares it (construction_hook): 1.29 has none, so
    # there a method of this name, override or not, is the mod's own and runs
    # whenever the mod calls it. The class must also derive from EntityAI,
    # which one file cannot tell: check_es_syncvar_construction_hook_classes
    # judges that once every file is read.
    return (
        construction_hook
        and method["name"] == ES_SYNCVAR_CONSTRUCTION_HOOK
        and not method["params"].strip()
        and "override" in lines[method["start_line"] - 1].split("(")[0].split()
    )


def compile_syncvar_assignment_re(var_name):
    escaped = re.escape(var_name)
    return re.compile(
        r"(?:^|[^\w.])(?:this\.)?\b"
        + escaped
        + r"\b(?:\s*(?:\+\+|--|[+\-*/%&|^]?=)(?!=)|\s*=\s*[^=])"
    )


def compile_syncvar_field_declaration_re(var_name):
    escaped = re.escape(var_name)
    return re.compile(
        r"^\s*"
        r"(?:static\s+|const\s+|protected\s+|private\s+|ref\s+|autoptr\s+|proto\s+)*"
        r"\w[\w<>,\s]*\s+"
        + escaped
        + r"\s*="
    )


def syncvar_assignment_has_set_dirty(lines, method, server_block):
    if method is None or server_block is None:
        return False

    start_line = max(method["start_line"], server_block[0])
    end_line = min(method["end_line"], server_block[1])
    for line_number in range(start_line, end_line + 1):
        if ES_SYNCVAR_SET_DIRTY_RE.search(lines[line_number - 1]):
            return True

    return False


def unique_in_order(values):
    unique = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        unique.append(value)
        seen.add(value)
    return unique


def check_es_syncvar_contract(
    source, stripped_source, rel_path, construction_hook=False,
    hook_registrations=None,
):
    errors = []
    warnings = []
    lines = stripped_source.split("\n")
    registers = find_es_syncvar_registers(source, stripped_source)
    if not registers:
        return errors, warnings

    classes, class_warnings = find_es_syncvar_classes(
        stripped_source, registers, rel_path
    )
    warnings.extend(class_warnings)
    methods = find_method_regions(stripped_source)

    for class_info in classes:
        class_methods = [
            method
            for method in methods
            if class_info["start_line"] <= method["start_line"]
            and method["end_line"] <= class_info["end_line"]
        ]
        class_registers = [
            register
            for register in registers
            if class_info["start_line"] <= register["line"] <= class_info["end_line"]
        ]
        if not class_registers:
            continue

        for register in class_registers:
            method = find_method_for_line(class_methods, register["line"])
            error = build_es_syncvar_error(
                rel_path,
                register["line"],
                register["var"],
                ES_SYNCVAR_REGISTER_OUTSIDE_CTOR_MESSAGE,
            )
            if method_is_syncvar_registration_target(
                method, class_info["class"], lines, construction_hook
            ):
                if (
                    hook_registrations is not None
                    and method["name"] == ES_SYNCVAR_CONSTRUCTION_HOOK
                    and method["name"] != class_info["class"]
                ):
                    hook_registrations.append((class_info["class"], error))
                continue
            errors.append(error)

        for var_name in unique_in_order(
            [register["var"] for register in class_registers]
        ):
            assignment_re = compile_syncvar_assignment_re(var_name)
            field_declaration_re = compile_syncvar_field_declaration_re(var_name)
            for line_number in range(
                class_info["start_line"], class_info["end_line"] + 1
            ):
                line = lines[line_number - 1]
                for _match in assignment_re.finditer(line):
                    if field_declaration_re.match(line):
                        continue
                    ifdef_stack = compute_ifdef_stack_at(lines, line_number - 1)
                    method = find_method_for_line(class_methods, line_number)
                    if not ifdef_stack_is_definitely_server_side(ifdef_stack):
                        if method is not None and line_is_inside_server_if_guard(
                            method, line_number, lines
                        ):
                            warnings.append(
                                build_es_syncvar_unsupported_warning(
                                    rel_path,
                                    line_number,
                                    var_name,
                                    ES_SYNCVAR_ALT_GUARD_UNSUPPORTED_MESSAGE,
                                )
                            )
                            continue
                        if any(
                            frame["directive"] == "unsupported"
                            for frame in ifdef_stack
                        ):
                            warnings.append(
                                build_es_syncvar_unsupported_warning(
                                    rel_path,
                                    line_number,
                                    var_name,
                                    ES_SYNCVAR_IFDEF_BRANCH_UNSUPPORTED_MESSAGE,
                                )
                            )
                            continue
                        # WRITE_NO_IFDEF quarantined 2026-08-18. The premise -
                        # "a SyncVar write must sit under #ifdef SERVER" - is not
                        # the contract vanilla implements. ItemBase.SetQuantity
                        # writes m_VarQuantity at itembase.c:3377 with NO side
                        # guard at all, and publishes with
                        # SetVariableMask(VARIABLE_QUANTITY) at :3406, also
                        # unguarded. Corrected 2026-08-19: the quarantine note
                        # first read the `if (g_Game.IsServer() || ...)` at :3379
                        # as guarding that write. It does not - it sits AFTER the
                        # assignment and wraps an inventory-sound block. Re-reading
                        # the file makes the premise MORE clearly false, not less.
                        # Items register in InitItemVariables (:254-270), not the
                        # constructor.
                        # Measured over the vanilla tree this fired 122 times, and
                        # once the class parser learned `extends` it rose to 317:
                        # the better the parser, the more it invents. That is the
                        # signature of a false premise, not of a near-miss detector.
                        # To re-wire: a desync repro from an unguarded client write,
                        # plus a check that accepts ctor / Init / InitItemVariables,
                        # g_Game or GetGame().IsServer(), #ifdef SERVER, *Server
                        # methods, and SetSynchDirty OR SetVariableMask in the same
                        # method. The register-outside-ctor half stays live.
                        continue

                    if method is None:
                        warnings.append(
                            build_es_syncvar_unsupported_warning(
                                rel_path,
                                line_number,
                                var_name,
                                ES_SYNCVAR_METHOD_UNPARSED_UNSUPPORTED_MESSAGE,
                            )
                        )
                        continue

                    server_block = find_server_ifdef_block_for_line(
                        lines, line_number
                    )
                    if syncvar_assignment_has_set_dirty(lines, method, server_block):
                        continue
                    errors.append(
                        build_es_syncvar_error(
                            rel_path,
                            line_number,
                            var_name,
                            ES_SYNCVAR_WRITE_NO_DIRTY_MESSAGE,
                        )
                    )

    return errors, warnings


def check_es_syncvar_construction_hook_classes(
    hook_registrations, addon_sources, external_sources, vanilla_root
):
    """FAILs for the hook registrations of classes not derived from EntityAI.

    hook_registrations: (class name, FAIL) of every SyncVar that
    check_es_syncvar_contract accepted only as registered in the construction
    hook. Only EntityAI calls that hook (3_game/entities/entityai.c:3469), so a
    class whose base classes all resolve across the addon, the external roots
    and the vanilla tree, none of them EntityAI, registers whenever the mod
    calls the method. A class whose chain does not resolve (a parent from a mod
    that was not passed, a header a directive splits) keeps the hook.
    """
    if not hook_registrations:
        return []
    hierarchy = Hierarchy()
    for _rel_path, stripped in list(addon_sources) + list(external_sources or []):
        hierarchy.add_source(stripped)
    vanilla_key = usable_vanilla_key(vanilla_root)
    if vanilla_key is not None:
        for _rel_path, text in vanilla_sources(vanilla_key):
            hierarchy.add_source(text)
    errors = []
    for class_name, error in hook_registrations:
        chain = hierarchy.chain(class_name)
        if chain is not None and "EntityAI" not in chain:
            errors.append(error)
    return errors
