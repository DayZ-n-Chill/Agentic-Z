import re

from shared.dead_branches import dead_lines


ES_UNBALANCED_BRACKETS_RULE_ID = "ES-UNBALANCED-BRACKETS"


# claim: CLAIM-ENFORCE-UNBALANCED-BRACKETS
# A `(`, `[` or `{` that is never closed, or a closer that meets another
# kind of opener, stops the script module from compiling. Pipeline inbox
# fb-20261004-040148-403a (SimpleGroup): `m_Objects.Clear();` sabotaged to
# `m_Objects.Clear(;` got PASS from this validator (the ticket files that
# PASS; no engine log of the file is cited). This rule is no parser:
# it counts brackets on the text the stripper leaves (comments and strings
# are blanks), so a file it passes can still fail to compile, and only the
# engine compile settles the syntax.
#
# Lines that never compile (shared/dead_branches.py) are not counted. The
# branches of one #ifdef/#ifndef/#if block never compile together, so each
# starts from the brackets open before the block. Vanilla-style blocks that
# write the same opening line twice, one per branch, end with the same
# brackets open and are counted once. When the branches of a block end with
# different brackets open, which build the rest of the file belongs to is
# not known, and the file is not judged.

_OPEN_RE = re.compile(r"^\s*#\s*(?:ifdef|ifndef|if)\b")
_BRANCH_RE = re.compile(r"^\s*#\s*(?:else|elif)\b")
_ENDIF_RE = re.compile(r"^\s*#\s*endif\b")

_PAIRS = {")": "(", "]": "[", "}": "{"}

ES_UNBALANCED_BRACKETS_UNCLOSED_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '{opener}' is never closed{where}. The "
    "compiler rejects the whole script module. This linter only counts "
    "brackets; the engine compile is the only full syntax check."
)

ES_UNBALANCED_BRACKETS_STRAY_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '{closer}' closes nothing. The compiler "
    "rejects the whole script module. This linter only counts brackets; the "
    "engine compile is the only full syntax check."
)


def _finding(rel_path, line, message):
    return [
        {
            "check": ES_UNBALANCED_BRACKETS_RULE_ID,
            "file": rel_path,
            "line": line,
            "message": message,
            "severity": "FAIL",
            "rule_id": ES_UNBALANCED_BRACKETS_RULE_ID,
        }
    ]


def _unclosed(rel_path, opener, where=""):
    char, line = opener
    return _finding(
        rel_path,
        line,
        ES_UNBALANCED_BRACKETS_UNCLOSED_MESSAGE.format(
            rel_path=rel_path, line=line, opener=char, where=where
        ),
    )


def _kinds(stack):
    return [char for char, _line in stack]


def check_es_unbalanced_brackets(stripped_source, rel_path):
    dead = dead_lines(stripped_source)
    # Open brackets: (char, line). Each block frame: (brackets open before
    # the block, brackets open at the end of each branch so far).
    stack = []
    blocks = []
    for number, line in enumerate(stripped_source.split("\n"), start=1):
        if _OPEN_RE.match(line):
            blocks.append((list(stack), []))
            continue
        if _BRANCH_RE.match(line):
            if blocks:
                before, ends = blocks[-1]
                ends.append(stack)
                stack = list(before)
            continue
        if _ENDIF_RE.match(line):
            if blocks:
                before, ends = blocks.pop()
                ends.append(stack)
                if len(ends) == 1:
                    # No #else: the build without the block keeps `before`.
                    ends.append(before)
                if any(_kinds(end) != _kinds(ends[0]) for end in ends):
                    return []
                stack = ends[0]
            continue
        if number in dead:
            continue
        for char in line:
            if char in "([{":
                stack.append((char, number))
            elif char in _PAIRS:
                if not stack:
                    return _finding(
                        rel_path,
                        number,
                        ES_UNBALANCED_BRACKETS_STRAY_MESSAGE.format(
                            rel_path=rel_path, line=number, closer=char
                        ),
                    )
                opener = stack.pop()
                if opener[0] != _PAIRS[char]:
                    return _unclosed(
                        rel_path,
                        opener,
                        " before the '%s' on line %d" % (char, number),
                    )
    if blocks:
        # An unterminated #ifdef: which branch the rest belongs to is unknown.
        return []
    if stack:
        return _unclosed(rel_path, stack[-1], " before the end of the file")
    return []
