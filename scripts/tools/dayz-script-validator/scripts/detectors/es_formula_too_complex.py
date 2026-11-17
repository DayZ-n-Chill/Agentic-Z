from detectors.es_modulo_float_context import _tokens
from shared.dead_branches import dead_lines, line_branches


ES_FORMULA_TOO_COMPLEX_RULE_ID = "ES-FORMULA-TOO-COMPLEX"


# claim: CLAIM-ENFORCE-FORMULA-TOO-COMPLEX
# One statement that joins many terms with `+` stops the script module with
# "Formula too complex". Measured on DayZDiag 1.30.164289, 2026-11-09, in a
# mod's 4_World script (pipeline inbox 7b9e/7ce1), with one statement on one
# line that alternates a string literal, an int, a string literal and a
# float's ToString():
#
#   string s = "a" + i0 + " b" + f0.ToString() + " c" + i0 + ...;
#
# 14 and 17 terms compiled; 18 and 20 did not:
#   SCRIPT (E): @"MCPProbeTerms18/scripts/4_World/mcpprobeterms18.c,6": Formula too complex
#   SCRIPT (E): @"MCPProbeTerms18/scripts/4_World/mcpprobeterms18.c,6": Incompatible parameter 'i0'
#   SCRIPT (E): Can't compile "World" script module!
# The second line is a cascade of the first.
#
# The limit is measured for that pattern only. Other operand types and a
# statement over several lines are not measured, so the rule is a WARN. A
# statement is reported when it holds a string literal and at least 18 terms
# joined by binary `+`: `++`, `+=` and a unary `+` join nothing, and a `+` in
# a string or a comment is none. Every binary `+` of the statement counts,
# one inside parentheses or a call's arguments too; whether the compiler
# counts those is not measured either. A chain with no string literal adds
# numbers and is not judged. What never compiles (shared/dead_branches.py) is
# not read. Terms are counted outside every block and along one branch of
# nested blocks at a time: two branches of one block, or two blocks side by
# side, are never counted together.

_TERMS = 18

_ENDS = {"num", "float", "string"}
_NOT_OPERANDS = {"return", "case"}


def _ends_operand(view, index):
    """True when the token before view[index] closes an operand."""
    if index == 0:
        return False
    kind, text = view[index - 1][:2]
    if kind in _ENDS:
        return True
    if kind == "ident":
        return text not in _NOT_OPERANDS
    if text in ("++", "--"):
        # A postfix increment closes its operand; a prefix one opens it.
        return _ends_operand(view, index - 1)
    return text in (")", "]")


def _statements(tokens):
    """Runs of tokens between `;`, `{` and `}`."""
    statement = []
    for token in tokens:
        if token[1] in (";", "{", "}"):
            if statement:
                yield statement
            statement = []
            continue
        statement.append(token)
    if statement:
        yield statement


def _joins(view):
    """(binary `+` count, holds a string literal) for one compiled view."""
    joins = sum(
        1 for index, token in enumerate(view)
        if token[1] == "+" and _ends_operand(view, index)
    )
    return joins, any(token[0] == "string" for token in view)


ES_FORMULA_TOO_COMPLEX_MESSAGE = (
    "[WARN] {rel_path} line {line}: one statement joins {terms} terms with "
    "'+' and holds a string literal. On DayZDiag 1.30.164289 a statement on "
    "one line that alternates string literals with an int and a float's "
    "ToString() compiled with 17 terms and failed with 18 and 20: \"Formula "
    "too complex\" on its line, then \"Incompatible parameter\" as a cascade, "
    "and the script module did not compile. Other operand types and a "
    "statement over several lines are not measured. Build the string in "
    "steps (s = s + part;)."
)


def check_es_formula_too_complex(source, stripped_source, rel_path):
    if "+" not in stripped_source:
        return []
    dead = dead_lines(stripped_source)
    branches = line_branches(stripped_source)
    live = [t for t in _tokens(source, stripped_source) if t[2] not in dead]
    warnings = []
    for statement in _statements(live):
        # One view per set of nested blocks a token sits in: the tokens
        # outside every block and in those same branches, which compile in
        # one build.
        joins = 0
        for where in {branches[t[2]] for t in statement}:
            view = [
                t for t in statement
                if where[:len(branches[t[2]])] == branches[t[2]]
            ]
            count, has_string = _joins(view)
            if has_string:
                joins = max(joins, count)
        if joins + 1 < _TERMS:
            continue
        line = statement[0][2]
        warnings.append(
            {
                "check": ES_FORMULA_TOO_COMPLEX_RULE_ID,
                "file": rel_path,
                "line": line,
                "message": ES_FORMULA_TOO_COMPLEX_MESSAGE.format(
                    rel_path=rel_path, line=line, terms=joins + 1
                ),
                "severity": "WARN",
                "rule_id": ES_FORMULA_TOO_COMPLEX_RULE_ID,
            }
        )
    return warnings
