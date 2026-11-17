"""Lines of a script that the preprocessor provably never compiles.

Used by rules whose finding is wrong wherever the code compiles (a keyword
used as a name, `%` in a float expression). A branch under another mod's
#ifdef is still judged, because it compiles once that mod is loaded. What is
never compiled is not judged:

  - lines under `#if` / `#elif` (Enforce scripts use #ifdef / #ifndef; an
    `#if 0` block is how code is switched off);
  - the `#ifndef X` branch, or the `#else` of `#ifdef X`, when this file
    #defines X before that point on a line it always keeps (outside every
    block, or under an #ifdef of a macro it #defined the same way).

line_branches() and compatible() tell apart lines in different branches of
one block, which never compile in the same build. Blocks are not related
through their macros there: `#ifdef X` and a later `#ifndef X` are two
unrelated blocks, so lines of both can be read together. line_tests() and
tests_agree() relate them, for a macro the file never #defines or #undefs:
lines under `#ifdef X` and under `#ifndef X` never compile together.
"""

import re

_OPEN_RE = re.compile(r"^\s*#\s*(?P<kind>ifdef|ifndef)\s+(?P<macro>\w+)")
_IF_RE = re.compile(r"^\s*#\s*if\b")
_ELIF_RE = re.compile(r"^\s*#\s*elif\b")
_ELSE_RE = re.compile(r"^\s*#\s*else\b")
_ENDIF_RE = re.compile(r"^\s*#\s*endif\b")
_DEFINE_RE = re.compile(r"^\s*#\s*define\s+(?P<name>\w+)")
_SET_RE = re.compile(r"^\s*#\s*(?:define|undef)\s+(?P<name>\w+)")


def dead_lines(stripped):
    """Set of 1-based line numbers that never compile (directives included)."""
    dead = set()
    defined = set()
    # Each entry: (macro or None, branch taken when the macro is defined).
    stack = []
    for number, line in enumerate(stripped.split("\n"), start=1):
        opened = _OPEN_RE.match(line)
        if opened:
            stack.append((opened.group("macro"), opened.group("kind") == "ifdef"))
            dead.add(number)
            continue
        if _IF_RE.match(line):
            stack.append((None, True))
            dead.add(number)
            continue
        if _ELIF_RE.match(line):
            if stack:
                stack[-1] = (None, True)
            dead.add(number)
            continue
        if _ELSE_RE.match(line):
            if stack:
                macro, when_defined = stack[-1]
                stack[-1] = (macro, not when_defined)
            dead.add(number)
            continue
        if _ENDIF_RE.match(line):
            if stack:
                stack.pop()
            dead.add(number)
            continue
        if line.lstrip().startswith("#"):
            define = _DEFINE_RE.match(line)
            always = all(
                macro is not None and macro in defined and when_defined
                for macro, when_defined in stack
            )
            if define and always:
                defined.add(define.group("name"))
            dead.add(number)
            continue
        if any(
            macro is None or (macro in defined and not when_defined)
            for macro, when_defined in stack
        ):
            dead.add(number)
    return dead


def line_branches(stripped):
    """{1-based line: the conditional blocks around it, outermost first}.

    Each block is a (block, branch) pair: `block` numbers the #if, #ifdef and
    #ifndef of the file in order, and `branch` counts the #elif and #else
    clauses before the line. Blocks open and close exactly as in dead_lines().
    """
    branches = {}
    stack = []
    opened = 0
    for number, line in enumerate(stripped.split("\n"), start=1):
        if _OPEN_RE.match(line) or _IF_RE.match(line):
            opened += 1
            stack.append((opened, 0))
        elif _ELIF_RE.match(line) or _ELSE_RE.match(line):
            if stack:
                block, branch = stack[-1]
                stack[-1] = (block, branch + 1)
        elif _ENDIF_RE.match(line):
            if stack:
                stack.pop()
        branches[number] = tuple(stack)
    return branches


def compatible(branches_a, branches_b):
    """False when two lines sit in different branches of the same block."""
    taken = dict(branches_a)
    return all(taken.get(block, branch) == branch for block, branch in branches_b)


def line_tests(stripped):
    """{1-based line: frozenset of the (macro, defined) states it compiles under}.

    An #ifdef X branch needs X defined and its #else needs X undefined; the
    reverse for #ifndef. Branches after an #elif, and a macro the file
    #defines or #undefs anywhere (its state can change inside the file), give
    no state. Blocks open and close exactly as in dead_lines().
    """
    lines = stripped.split("\n")
    # Line by line, as dead_lines() reads directives: over the whole text, \s*
    # ran on across blank lines and the scan grew with the square of a run.
    changing = {match.group("name") for match in map(_SET_RE.match, lines) if match}
    tests = {}
    # Each entry: (macro, defined), or None when the branch tests no macro.
    stack = []
    for number, line in enumerate(lines, start=1):
        opened = _OPEN_RE.match(line)
        if opened:
            macro = opened.group("macro")
            stack.append(
                None if macro in changing
                else (macro, opened.group("kind") == "ifdef")
            )
        elif _IF_RE.match(line):
            stack.append(None)
        elif _ELIF_RE.match(line):
            if stack:
                stack[-1] = None
        elif _ELSE_RE.match(line):
            if stack and stack[-1] is not None:
                macro, defined = stack[-1]
                stack[-1] = (macro, not defined)
        elif _ENDIF_RE.match(line):
            if stack:
                stack.pop()
        tests[number] = frozenset(test for test in stack if test is not None)
    return tests


def tests_agree(tests_a, tests_b):
    """False when one set needs a macro defined and the other needs it undefined.

    A line whose own set disagrees with itself never compiles.
    """
    return not any((macro, not defined) in tests_b for macro, defined in tests_a)
