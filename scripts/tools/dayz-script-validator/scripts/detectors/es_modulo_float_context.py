import re

from shared.dead_branches import compatible, dead_lines, line_branches


ES_MODULO_FLOAT_CONTEXT_RULE_ID = "ES-MODULO-FLOAT-CONTEXT"


# claim: CLAIM-ENFORCE-MODULO-FLOAT-CONTEXT
# `%` compiles between integers, but not inside an arithmetic expression that
# also holds a float literal, even when both operands of `%` are integers:
#
#   `((g % 5) - 2) * 7.0`, DayZDiag 1.29, 2026-09-28:
#     SCRIPT (E): lfpg_probe3d.c,255: Unknown operator '%'
#     SCRIPT (E): Can't compile "Mission" script module!
#   `float ox = (n % 4) * 0.7 - 1.05;`, DayZ 1.30 (Exp), 2026-09-24: the
#     same error, and the mission did not compile.
#   `float x = (cell % 103) * 150 + 150 * 0.5;` and the ticket's
#     `float x = (cell % SIDE) * STEP + STEP * 0.5;` (static const float STEP,
#     static const int SIDE), DayZDiag 1.30.164289, 2026-11-09, each in a
#     mod's 4_World script (pipeline inbox d35a):
#     SCRIPT (E): @"MCPProbeD35aB/scripts/4_World/mcpprobed35ab.c,6": Unknown operator '%'
#     SCRIPT (E): Can't compile "World" script module!
#     and the same at mcpprobed35ac.c,10. Both hold the literal 0.5, so
#     whether a static const float with no literal beside it fails is not
#     isolated. The ticket saw "Unknown operator ''" in a mission's init.c.
#
# The first two compiled once the `%` went into an int local first, and so
# did the ticket's on 1.30.164289:
#   `int col = cell % SIDE; float x = col * STEP; x = x + STEP * 0.5;`
# Vanilla 1.29 holds 69 `%` operators and none shares an expression with a
# float literal.
#
# The expression around a `%` is walked out through grouping parentheses and
# stops at `;` `,` `{` `}`, an assignment, a comparison or logical operator,
# `?` `:`, `return`, an index bracket, and the parentheses of a call or of
# if/while/for/switch. A float literal counts only at that level or inside
# grouping parentheses: one inside a call's arguments or an index belongs to
# another expression. An expression that holds a string literal anywhere, its
# first token included, is not judged: there `+` concatenates, and no failure
# is on record for that case. Quotes inside a comment are no string. A float
# VARIABLE is not seen (types are not tracked): only the literal case is found.
# What never compiles (shared/dead_branches.py) is not judged and is no part
# of any expression; neither is another branch of a block the `%` sits in.

_TOKEN_RE = re.compile(
    r"(?P<float>(?<![\w.])(?:\d+\.\d*|\.\d+)(?:[eE][-+]?\d+)?f?(?![\w.]))"
    r"|(?P<num>(?<![\w.])\d+(?:[eE][-+]?\d+)?\w*)"
    r"|(?P<ident>[A-Za-z_]\w*)"
    r"|(?P<op>==|!=|<=|>=|&&|\|\||\+=|-=|\*=|/=|%=|\|=|&=|\^=|<<=|>>=|<<|>>"
    r"|\+\+|--|[-+*/%<>=!?:;,.{}()\[\]&|^~])"
)

_STOP_OPS = {
    ";", ",", "{", "}", "=", "+=", "-=", "*=", "/=", "%=", "|=", "&=", "^=",
    "<<=", ">>=", "==", "!=", "<", ">", "<=", ">=", "&&", "||", "?", ":",
}
_STOP_WORDS = {"return", "case", "new", "delete"}


def _string_spans(source):
    """(start, end) of every string literal, found the way stripper.py does.

    The stripper turns strings and comments alike into spaces, so the stripped
    text cannot tell them apart; this walks the source through the same
    states (line comment, block comment, string with backslash escapes).
    """
    spans = []
    index = 0
    length = len(source)
    while index < length:
        pair = source[index:index + 2]
        if pair == "//":
            end = source.find("\n", index)
            index = length if end < 0 else end
            continue
        if pair == "/*":
            end = source.find("*/", index + 2)
            index = length if end < 0 else end + 2
            continue
        if source[index] == '"':
            cursor = index + 1
            escaped = False
            while cursor < length:
                char = source[cursor]
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    break
                cursor += 1
            spans.append((index, min(cursor + 1, length)))
            index = cursor + 1
            continue
        index += 1
    return spans


def _tokens(source, stripped):
    """(kind, text, line, start, end) for every token, string literals included.

    The stripper keeps every offset and line, so a string found in the source
    sits where the stripped text holds its blanks.
    """
    found = [
        (match.start(), match.end(), match.lastgroup, match.group())
        for match in _TOKEN_RE.finditer(stripped)
    ]
    found.extend((start, end, "string", '"') for start, end in _string_spans(source))
    found.sort()
    tokens = []
    line = 1
    pos = 0
    for start, end, kind, text in found:
        line += stripped.count("\n", pos, start)
        pos = start
        tokens.append((kind, text, line, start, end))
    return tokens


def _matching(tokens):
    """Index of the partner of every bracket token; unbalanced ones map to None."""
    partner = {}
    stack = []
    pairs = {")": "(", "]": "["}
    for index, token in enumerate(tokens):
        text = token[1]
        if text in ("(", "["):
            stack.append(index)
        elif text in (")", "]"):
            while stack and tokens[stack[-1]][1] != pairs[text]:
                partner[stack.pop()] = None
            if stack:
                opener = stack.pop()
                partner[opener] = index
                partner[index] = opener
            else:
                partner[index] = None
        elif text in ("{", "}", ";"):
            while stack:
                partner[stack.pop()] = None
    while stack:
        partner[stack.pop()] = None
    return partner


def _is_call_or_control(tokens, open_index):
    """An opening parenthesis that belongs to a call or to if/while/for/switch."""
    if open_index == 0:
        return False
    kind, text = tokens[open_index - 1][:2]
    if kind == "ident":
        return text not in _STOP_WORDS
    return text in (")", "]")


def _is_stop(token):
    kind, text = token[:2]
    return text in _STOP_OPS or (kind == "ident" and text in _STOP_WORDS)


def _span(tokens, partner, index):
    """(first, last) token indexes of the arithmetic expression holding `index`."""
    first = index
    cursor = index - 1
    while cursor >= 0:
        text = tokens[cursor][1]
        if text in (")", "]"):
            opener = partner.get(cursor)
            if opener is None:
                break
            first = opener
            cursor = opener - 1
            continue
        if text == "(":
            if _is_call_or_control(tokens, cursor):
                break
            first = cursor
            cursor -= 1
            continue
        if text == "[" or _is_stop(tokens[cursor]):
            break
        first = cursor
        cursor -= 1
    last = index
    cursor = index + 1
    while cursor < len(tokens):
        text = tokens[cursor][1]
        if text in ("(", "["):
            closer = partner.get(cursor)
            if closer is None:
                break
            last = closer
            cursor = closer + 1
            continue
        if text == ")":
            opener = partner.get(cursor)
            if opener is None or _is_call_or_control(tokens, opener):
                break
            last = cursor
            cursor += 1
            continue
        if text == "]" or _is_stop(tokens[cursor]):
            break
        last = cursor
        cursor += 1
    return first, last


_BOOLEAN_OPS = {"==", "!=", "<", ">", "<=", ">=", "&&", "||"}


def _after_cast_operand(tokens, partner, cursor):
    """Index of the token after the first operand of a cast, signs included.

    A call's arguments or an index that follow a name are skipped by the
    caller anyway, so the operand ends with its literal, name or parentheses.
    """
    while cursor < len(tokens) and tokens[cursor][1] in ("-", "+", "!", "~"):
        cursor += 1
    if cursor < len(tokens) and tokens[cursor][1] == "(":
        closer = partner.get(cursor)
        return len(tokens) if closer is None else closer + 1
    return cursor + 1


def _group_value_start(tokens, partner, opener, closer):
    """First token of a grouping parenthesis whose floats reach its value.

    Behind a `?` only the two results do; a comparison or logical operator
    without one makes the group a condition, whose floats never reach it.
    """
    condition = False
    cursor = opener + 1
    while cursor < closer:
        text = tokens[cursor][1]
        if text == "?":
            return cursor + 1
        if text in _BOOLEAN_OPS:
            condition = True
        if text in ("(", "["):
            inner = partner.get(cursor)
            if inner is None:
                return None
            cursor = inner + 1
            continue
        cursor += 1
    return None if condition else opener + 1


def _float_literal_at_level(tokens, partner, first, last):
    # Groups are entered through an explicit stack, not by recursion, so no
    # depth of parentheses can exhaust the interpreter's stack. Each entry is
    # a stretch still to read; an unbalanced bracket ends only its stretch.
    stretches = [(first, last)]
    while stretches:
        cursor, last = stretches.pop()
        while cursor <= last:
            kind, text = tokens[cursor][:2]
            if kind == "float":
                return text
            if text == "[" or (text == "(" and _is_call_or_control(tokens, cursor)):
                closer = partner.get(cursor)
                if closer is None:
                    break
                cursor = closer + 1
                continue
            if text == "(":
                closer = partner.get(cursor)
                if closer is None or closer > last:
                    # The expression starts inside this parenthesis: read on.
                    cursor += 1
                    continue
                if closer == cursor + 2 and tokens[cursor + 1][1] == "int":
                    # `(int)x`: the cast's operand is an int, whatever it holds.
                    cursor = _after_cast_operand(tokens, partner, closer + 1)
                    continue
                start = _group_value_start(tokens, partner, cursor, closer)
                if start is not None:
                    # Read the group first, then what follows it.
                    stretches.append((closer + 1, last))
                    cursor, last = start, closer - 1
                    continue
                cursor = closer + 1
                continue
            cursor += 1
    return None


def _holds_string_literal(tokens, first, last):
    return any(tokens[cursor][0] == "string" for cursor in range(first, last + 1))


ES_MODULO_FLOAT_CONTEXT_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '%' is used in an expression that also "
    "holds the float literal {literal}. Enforce types the whole expression as "
    "float and has no float '%': the compiler stops with \"Unknown operator "
    "'%'\" and the script module fails to load. Compute the '%' into an int "
    "local first, then use that local in the float expression."
)


def check_es_modulo_float_context(source, stripped_source, rel_path):
    if "%" not in stripped_source:
        return []
    dead = dead_lines(stripped_source)
    branches = line_branches(stripped_source)
    # Tokens of lines that never compile take no part in any expression.
    live = [t for t in _tokens(source, stripped_source) if t[2] not in dead]
    # One view of the file per set of blocks a `%` sits in: the live tokens
    # that can compile in the same build as that `%`.
    views = {}
    errors = []
    seen_lines = set()
    for token in live:
        if token[1] != "%":
            continue
        line = token[2]
        where = branches[line]
        if where not in views:
            tokens = [t for t in live if compatible(where, branches[t[2]])]
            index_of = {t[3]: position for position, t in enumerate(tokens)}
            views[where] = (tokens, _matching(tokens), index_of)
        tokens, partner, index_of = views[where]
        first, last = _span(tokens, partner, index_of[token[3]])
        literal = _float_literal_at_level(tokens, partner, first, last)
        if literal is None or line in seen_lines:
            continue
        if _holds_string_literal(tokens, first, last):
            continue
        seen_lines.add(line)
        errors.append(
            {
                "check": ES_MODULO_FLOAT_CONTEXT_RULE_ID,
                "file": rel_path,
                "line": line,
                "message": ES_MODULO_FLOAT_CONTEXT_MESSAGE.format(
                    rel_path=rel_path, line=line, literal=literal
                ),
                "severity": "FAIL",
                "rule_id": ES_MODULO_FLOAT_CONTEXT_RULE_ID,
            }
        )
    return errors
