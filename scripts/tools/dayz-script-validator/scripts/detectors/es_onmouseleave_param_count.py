import re


ES_ONMOUSELEAVE_PARAM_COUNT_RULE_ID = "ES-ONMOUSELEAVE-PARAM-COUNT"


# dayz-ui-development SKILL.md:635 (TROUBLESHOOTING row "OnMouseLeave never
# fires | Wrong parameter count (3 instead of 4)"). Engine proto verified at
# P:\scripts\1_core\proto\enwidgets.c:666:
#     bool OnMouseLeave(Widget w, Widget enterW, int x, int y);
# OnMouseEnter takes 3 params; copying its arity produces an overload the
# engine dispatch never calls, so the handler compiles but never fires.
#
# Scope: only classes declaring `extends ScriptedWidgetEventHandler` are
# checked. Delegate/page classes legitimately re-implement a 3-param
# OnMouseLeave invoked manually from the real handler (LBmaster production:
# LBGroupUI.c:293 forwards to plain-class LBGroupPage.c:110) -- flagging
# those is a false positive, so classes without the handler base are
# skipped. Known FN: handlers extending an intermediate base class, and
# declarations with a non-bool return type.
ES_SWEH_CLASS_HEADER_RE = re.compile(
    r"\bclass\s+\w+\s+extends\s+ScriptedWidgetEventHandler\b[^{]*\{"
)

ES_ONMOUSELEAVE_DECL_RE = re.compile(r"\bbool\s+OnMouseLeave\s*\(([^)]*)\)")

ES_ONMOUSELEAVE_EXPECTED_PARAMS = 4


ES_ONMOUSELEAVE_PARAM_COUNT_MESSAGE = (
    "[WARN] {rel_path} line {line}: `OnMouseLeave` declared with {count} "
    "parameter(s) in a ScriptedWidgetEventHandler class; the engine dispatch "
    "signature is `OnMouseLeave(Widget w, Widget enterW, int x, int y)` -- 4 "
    "params (enwidgets.c:666). With any other arity the handler compiles but "
    "never fires. OnMouseEnter takes 3 params -- do not copy its arity "
    "(dayz-ui-development SKILL.md:635)."
)


def count_top_level_params(params_text):
    # Comma count at angle/paren depth 0; generics (`map<int, int>`) and
    # parenthesised defaults do not split a parameter.
    text = params_text.strip()
    if not text:
        return 0
    depth_angle = 0
    depth_paren = 0
    count = 1
    for char in text:
        if char == "<":
            depth_angle += 1
        elif char == ">":
            if depth_angle > 0:
                depth_angle -= 1
        elif char == "(":
            depth_paren += 1
        elif char == ")":
            if depth_paren > 0:
                depth_paren -= 1
        elif char == "," and depth_angle == 0 and depth_paren == 0:
            count += 1
    return count


def find_sweh_class_spans(stripped_source):
    # Body span of every `class X extends ScriptedWidgetEventHandler {...}`,
    # resolved by brace counting on the stripped source (strings/comments
    # already removed, so every brace is structural).
    spans = []
    for header in ES_SWEH_CLASS_HEADER_RE.finditer(stripped_source):
        depth = 1
        pos = header.end()
        while pos < len(stripped_source) and depth > 0:
            char = stripped_source[pos]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            pos += 1
        spans.append((header.end(), pos))
    return spans


def check_es_onmouseleave_param_count(stripped_source, rel_path):
    warnings = []
    spans = find_sweh_class_spans(stripped_source)
    if not spans:
        return warnings

    for match in ES_ONMOUSELEAVE_DECL_RE.finditer(stripped_source):
        if not any(start <= match.start() < end for start, end in spans):
            continue
        param_count = count_top_level_params(match.group(1))
        if param_count == ES_ONMOUSELEAVE_EXPECTED_PARAMS:
            continue
        line_number = stripped_source.count("\n", 0, match.start()) + 1
        message = ES_ONMOUSELEAVE_PARAM_COUNT_MESSAGE.format(
            rel_path=rel_path, line=line_number, count=param_count
        )
        warnings.append(
            {
                "check": ES_ONMOUSELEAVE_PARAM_COUNT_RULE_ID,
                "file": rel_path,
                "line": line_number,
                "message": message,
                "severity": "WARN",
                "rule_id": ES_ONMOUSELEAVE_PARAM_COUNT_RULE_ID,
            }
        )

    return warnings
