from shared.control_flow import (
    ES_EMPTY_IFDEF_RE_CLOSE,
    ES_EMPTY_IFDEF_RE_OPEN,
    ES_EMPTY_IFDEF_RE_UNSUPPORTED_DIRECTIVE,
    ES_EMPTY_IFDEF_RE_UNSUPPORTED_IFDEF,
    mark_supported_ifdef_stack_has_statement,
    unsupported_directive_opens_block,
)


ES_EMPTY_IFDEF_RULE_ID = "ES-EMPTY-IFDEF"


ES_EMPTY_IFDEF_UNSUPPORTED_RULE_ID = "ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN"


# An #ifdef or #ifndef block with no statement in it, comments aside. It was
# FAIL on a reported segfault. WARN since pipeline inbox dada: on DayZDiag
# 1.30.164289 (2026-11-09), in a mod's 4_World scripts, a block holding only
# a comment compiled and ran on server and client, at file scope, in a class
# body and in a method body, each with DIAG_DEVELOPER (which DayZDiag defines
# on both) and with a macro nobody defines; the method's marker was printed
# and neither process hung. Vanilla 1.30 ships one at
# 4_world/classes/environment/environment.c:1-3. Not measured: a block with
# nothing at all inside, a retail build, DayZ 1.29.
ES_EMPTY_IFDEF_MESSAGE = (
    "[WARN] {rel_path} line {line}: '#{directive} {macro}' block contains no "
    "statements (comments do not count). Such blocks were reported to "
    "segfault, and no measurement shows it: on DayZDiag 1.30.164289 a block "
    "holding only a comment compiled and ran on server and client, at file "
    "scope, in a class body and in a method body, with a macro DayZDiag "
    "defines and with one nobody defines (enforce-script-reference "
    "pitfalls-advanced.md, section 5). Not measured: a block with nothing at "
    "all inside, a retail build, DayZ 1.29. Remove the block if it holds no "
    "code."
)


ES_EMPTY_IFDEF_UNSUPPORTED_MESSAGE = (
    "[WARN] {rel_path} line {line}: unsupported preprocessor pattern for "
    "ES-EMPTY-IFDEF. Phase 1 supports only '#ifdef <macro>'/'#ifndef <macro>' "
    "paired with '#endif'; #if/#elif/#else and complex conditions are not "
    "analyzed."
)


ES_EMPTY_IFDEF_UNTERMINATED_MESSAGE = (
    "[WARN] {rel_path} line {line}: unterminated #{directive} {macro} block "
    "starting at line {line}."
)


ES_EMPTY_IFDEF_STRAY_ENDIF_MESSAGE = (
    "[WARN] {rel_path} line {line}: stray #endif without matching #ifdef."
)


def build_es_empty_ifdef_unsupported_warning(rel_path, line_number):
    return {
        "check": ES_EMPTY_IFDEF_UNSUPPORTED_RULE_ID,
        "file": rel_path,
        "line": line_number,
        "message": ES_EMPTY_IFDEF_UNSUPPORTED_MESSAGE.format(
            rel_path=rel_path,
            line=line_number,
        ),
        "severity": "WARN",
        "rule_id": ES_EMPTY_IFDEF_UNSUPPORTED_RULE_ID,
    }


def build_es_empty_ifdef_unterminated_warning(
    rel_path, line_number, directive, macro
):
    return {
        "check": ES_EMPTY_IFDEF_UNSUPPORTED_RULE_ID,
        "file": rel_path,
        "line": line_number,
        "message": ES_EMPTY_IFDEF_UNTERMINATED_MESSAGE.format(
            rel_path=rel_path,
            line=line_number,
            directive=directive,
            macro=macro,
        ),
        "severity": "WARN",
        "rule_id": ES_EMPTY_IFDEF_UNSUPPORTED_RULE_ID,
    }


def build_es_empty_ifdef_stray_endif_warning(rel_path, line_number):
    return {
        "check": ES_EMPTY_IFDEF_UNSUPPORTED_RULE_ID,
        "file": rel_path,
        "line": line_number,
        "message": ES_EMPTY_IFDEF_STRAY_ENDIF_MESSAGE.format(
            rel_path=rel_path,
            line=line_number,
        ),
        "severity": "WARN",
        "rule_id": ES_EMPTY_IFDEF_UNSUPPORTED_RULE_ID,
    }


def check_es_empty_ifdef(stripped_source, rel_path):
    errors = []
    warnings = []
    lines = stripped_source.split("\n")
    stack = []

    for line_number, line in enumerate(lines, start=1):
        open_match = ES_EMPTY_IFDEF_RE_OPEN.match(line)
        if open_match:
            stack.append(
                {
                    "unsupported": False,
                    "line": line_number,
                    "directive": open_match.group("directive"),
                    "macro": open_match.group("macro"),
                    "has_statement": False,
                }
            )
            continue

        if ES_EMPTY_IFDEF_RE_UNSUPPORTED_IFDEF.match(line):
            warnings.append(
                build_es_empty_ifdef_unsupported_warning(rel_path, line_number)
            )
            mark_supported_ifdef_stack_has_statement(stack)
            stack.append({"unsupported": True, "line": line_number})
            continue

        if ES_EMPTY_IFDEF_RE_UNSUPPORTED_DIRECTIVE.match(line):
            warnings.append(
                build_es_empty_ifdef_unsupported_warning(rel_path, line_number)
            )
            mark_supported_ifdef_stack_has_statement(stack)
            if unsupported_directive_opens_block(line):
                stack.append({"unsupported": True, "line": line_number})
            continue

        if ES_EMPTY_IFDEF_RE_CLOSE.match(line):
            if stack:
                frame = stack.pop()
                if frame["unsupported"]:
                    continue
                if not frame["has_statement"]:
                    message = ES_EMPTY_IFDEF_MESSAGE.format(
                        rel_path=rel_path,
                        line=frame["line"],
                        directive=frame["directive"],
                        macro=frame["macro"],
                    )
                    warnings.append(
                        {
                            "check": ES_EMPTY_IFDEF_RULE_ID,
                            "file": rel_path,
                            "line": frame["line"],
                            "message": message,
                            "severity": "WARN",
                            "rule_id": ES_EMPTY_IFDEF_RULE_ID,
                        }
                    )
                continue
            warnings.append(build_es_empty_ifdef_stray_endif_warning(rel_path, line_number))
            continue

        if line.strip() != "":
            mark_supported_ifdef_stack_has_statement(stack)

    for frame in stack:
        if frame["unsupported"]:
            continue
        warnings.append(
            build_es_empty_ifdef_unterminated_warning(
                rel_path, frame["line"], frame["directive"], frame["macro"]
            )
        )

    return errors, warnings
