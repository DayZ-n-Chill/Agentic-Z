import bisect
import re

from detectors.es_reserved_word_identifier import _MODIFIERS, _NOT_A_TYPE
from detectors.es_undefined_class_ref import (
    _ENUM_DEF_RE,
    _LAST_IDENT_RE,
    _TYPEDEF_RE,
    Definitions,
)
from detectors.es_variable_named_as_type import usable_vanilla_key, vanilla_sources
from shared.dead_branches import dead_lines
from shared.method_recognition import find_method_regions


ES_CAST_UNRELATED_TYPES_RULE_ID = "ES-CAST-UNRELATED-TYPES"


# claim: CLAIM-ENFORCE-CAST-UNRELATED-TYPES
# `X.Cast(y)` where neither X nor the declared type of y derives from the
# other stops the whole script module from compiling. Pipeline inbox
# fb-20261009-122148-c852, DayZDiag 1.29:
#
#   Mission mission = GetGame().GetMission();
#   hud = IngameHud.Cast(mission);
#
# refused the Mission module with `Types 'IngameHud' and 'Mission' are not
# related`. The message is the evidence that neither class derives from the
# other; that IngameHud derives from Hud is the ticket's word, not re-read on
# a vanilla tree for this rule.
#
# Judged only when everything is known, otherwise skipped without a word:
#   - y is a plain name (not a call or a member access) declared in
#     the same function, as a local still open at the cast or a parameter,
#     or else as a member of the enclosing class itself, with one type and
#     no template arguments or array brackets; a later declarator
#     (`int a, y;`) in the function makes y unknown;
#   - X and that type are classes of the addon, the vanilla tree (comments
#     dropped) or an --external-scripts root, not a typedef, an enum, a
#     template or its parameter, nor a primitive;
#   - the whole `extends` chain of both resolves: each class has a
#     declaration that is not `modded` (a modded class does not change the
#     hierarchy) and one parent across all of them (a forward `class X;` is
#     no declaration); a class without a parent ends the chain. Class, the implicit root, is related to everything.
#     A header that a directive splits (`class D` / `#ifdef X` / `: B` /
#     `#endif`) has a parent _CLASS_RE cannot read, so its chain does not
#     resolve.
# Without a vanilla tree a chain that reaches a vanilla class does not
# resolve, so the cast is not judged. Lines that never compile
# (shared/dead_branches.py) are not judged.

_CLASS_RE = re.compile(
    r"^[ \t]*(?P<mods>(?:(?:modded|sealed|proto|native|inherited|static|"
    r"external)\s+)*)class\s+(?P<name>[A-Za-z_]\w*)(?P<params>\s*<[^;{}>]*>)?"
    r"(?:\s*(?::|\bextends\b)\s*(?P<parent>[A-Za-z_]\w*))?(?P<after>\s*;)?",
    re.M,
)
_CAST_RE = re.compile(
    r"(?<![\w.])(?P<target>[A-Za-z_]\w*)\s*\.\s*Cast\s*\(\s*"
    r"(?P<arg>[A-Za-z_]\w*)\s*\)"
)

IMPLICIT_ROOT = "Class"
# The parent of a class whose header a directive splits: no class has it.
UNREAD_PARENT = "#"
PRIMITIVES = {
    "int", "float", "bool", "string", "vector", "typename", "void", "auto",
    "func",
}

ES_CAST_UNRELATED_TYPES_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '{target}.Cast({arg})': '{arg}' is "
    "declared as {arg_type}, and neither class derives from the other "
    "({target_chain}; {arg_chain}). The compiler refuses it with \"Types "
    "'{target}' and '{arg_type}' are not related\" and the whole script "
    "module does not compile. Get the object from an API that returns a "
    "related type (a HUD from the mission's GetHud(), not from the mission)."
)


def class_parent(text, match):
    """The parent of a _CLASS_RE match, None, or UNREAD_PARENT.

    The header runs from the match to the first `{` or `;`; a `#` in it is a
    directive (comments and strings are gone), and the parent behind it is
    not read.
    """
    ends = [
        i for i in (text.find("{", match.end()), text.find(";", match.end()))
        if i >= 0
    ]
    if "#" in text[match.end():min(ends, default=len(text))]:
        return UNREAD_PARENT
    return match.group("parent")


class Hierarchy:
    """Class declarations of every scanned tree, with their parents."""

    def __init__(self):
        self.declarations = {}
        self.definitions = Definitions()
        self.not_classes = set()

    def add_source(self, text):
        self.definitions.add_source(text, variables=False)
        for match in _ENUM_DEF_RE.finditer(text):
            self.not_classes.add(match.group("name"))
        for match in _TYPEDEF_RE.finditer(text):
            last = _LAST_IDENT_RE.search(match.group("body").split("//", 1)[0])
            if last:
                self.not_classes.add(last.group("name"))
        for match in _CLASS_RE.finditer(text):
            if match.group("after"):
                continue  # `class X;`: a forward declaration
            self.declarations.setdefault(match.group("name"), []).append(
                (
                    "modded" in match.group("mods").split(),
                    class_parent(text, match),
                    bool(match.group("params")),
                )
            )

    def is_plain_class(self, name):
        """A class and nothing else: no typedef, enum, template, primitive."""
        if name in PRIMITIVES or name in self.not_classes:
            return False
        if name in self.definitions.template_params:
            return False
        entries = self.declarations.get(name, ())
        return bool(entries) and not any(
            templated for _m, _p, templated in entries
        )

    def chain(self, name):
        """[name, parent, ...] up to a class without a parent, or None."""
        chain = []
        while name is not None:
            if name in chain or not self.is_plain_class(name):
                return None
            parents = {
                parent
                for modded, parent, _templated in self.declarations[name]
                if not modded
            }
            if len(parents) != 1:
                return None
            chain.append(name)
            name = parents.pop()
        return chain


# A declaration may follow a `case` or `default` label on its line, `case 0:
# Object hit;` (Codex review of #125, F1): a `:` before the type counts only
# there, where the text after the last `;`, `{`, `}` or `:` before it on its
# line is a label, so a second label (`case 0: case 1:`) counts too. Checked
# in the pattern, the label made it a third slower; searched for, a long line
# took a time that grew with its square (Codex review of #125, G4).
_LABEL_RE = re.compile(r"[ \t]*(?:case\b[^;{}:\n]*|default[ \t]*)")


def _after_a_label(text, colon):
    """True when the `:` at `colon` ends a `case` or `default` label."""
    start = colon
    while start and text[start - 1] not in ";{}:\n":
        start -= 1
    return _LABEL_RE.fullmatch(text, start, colon) is not None


# Neither a template's arguments nor an array's size hold a `:`, so neither
# part runs past one: from each `:` before a type they ran on to the end of
# the line, and a line of `: Object<` took a time that grew with its square
# (Codex review of #125, H2).
def _declaration_re(name):
    return re.compile(
        r"(?:^|[;{}(,:])[ \t]*" + _MODIFIERS
        + r"(?P<type>[A-Za-z_]\w*)(?P<targs>[ \t]*<[^;{}()\n:]*?>)?"
        r"(?P<arr>[ \t]*\[[^\]\n:]*\])?\s+" + re.escape(name)
        + r"\s*(?P<next>;|=(?!=)|\[|,|\)|:(?!:))",
        re.M,
    )


def _declared_type(match):
    """The plain type of a declaration match, or "" when not plain."""
    if match.group("type") in _NOT_A_TYPE:
        return None
    text, at = match.string, match.start()
    if text[at] == ":" and not _after_a_label(text, at):
        return None
    if match.group("targs") or match.group("arr") or match.group("next") == "[":
        return ""
    return match.group("type")


def _still_open(text, start, end):
    """True when no bracket open at `start` is closed before `end`."""
    depth = 0
    for char in text[start:end]:
        if char in "({":
            depth += 1
        elif char in ")}":
            depth -= 1
            if depth < 0:
                return False
    return True


def _line_offsets(stripped):
    offsets = [0]
    for index, char in enumerate(stripped):
        if char == "\n":
            offsets.append(index + 1)
    return offsets


def _class_regions(stripped):
    """(start, end) offsets of the body of each class of the file."""
    regions = []
    for match in _CLASS_RE.finditer(stripped):
        if match.group("after"):
            continue
        brace = stripped.find("{", match.end())
        if brace < 0:
            continue
        depth = 0
        for index in range(brace, len(stripped)):
            char = stripped[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    regions.append((brace, index))
                    break
    return regions


class FileScopes:
    """The lines, methods and class bodies of one file, read once.

    _argument_type() asks for them at every cast or call. Counting the lines
    from the start of the file and going through every method and class body
    each time kept ES-PROTECTED-METHOD-CROSS-CLASS running for more than 20
    minutes on a 10 MB file (mods pass of #113, 2026-10-17).
    """

    def __init__(self, stripped):
        self.dead = dead_lines(stripped)
        self.offsets = _line_offsets(stripped)
        # In file order, and none inside another: each search starts after
        # the end of the method before.
        self.methods = find_method_regions(stripped)
        self._method_starts = [method["start_line"] for method in self.methods]
        # In file order. Matched braces nest or are apart, so each body has
        # one innermost body around it (its index here, -1 for none).
        self.regions = _class_regions(stripped)
        self._region_starts = [start for start, _end in self.regions]
        self._region_parents = []
        around = []
        for index, (start, _end) in enumerate(self.regions):
            while around and self.regions[around[-1]][1] < start:
                around.pop()
            self._region_parents.append(around[-1] if around else -1)
            around.append(index)
        # {(class body open, name, blocks around the cast or call, reader of
        #  the declared type): its type as a member of that body}
        self.members = {}
        # {(class body open, name, reader of the declared type): [(type,
        #  line), ...] of its declarations at the top level of that body}
        self.declarations = {}

    def line(self, at):
        """The 1-based line of offset `at`."""
        return bisect.bisect_right(self.offsets, at)

    def method(self, line):
        """The method around `line`, the one find_method_for_line() gives."""
        index = bisect.bisect_right(self._method_starts, line) - 1
        if index >= 0 and line <= self.methods[index]["end_line"]:
            return self.methods[index]
        return None

    def class_body(self, at):
        """(open, close) of the innermost class body around `at`, or None."""
        index = bisect.bisect_left(self._region_starts, at) - 1
        while index >= 0:
            if at < self.regions[index][1]:
                return self.regions[index]
            index = self._region_parents[index]
        return None


def _apart(around, line, blocks):
    """True when around, a line_branches(), puts `line` under a conditional
    block that is not one of `blocks`."""
    return around is not None and around[line] != blocks[:len(around[line])]


def _argument_type(
    stripped, scopes, arg, cast_at, inherited=None, around=None,
    declared_type=_declared_type,
):
    """The one plain declared type of `arg` at `cast_at`, or None.

    scopes: the FileScopes of `stripped`. around, when given, is the
    line_branches() of stripped: a declaration under an #if, #ifdef or
    #ifndef block that is not also around cast_at leaves the type unknown,
    and so does one in the method before cast_at that is not open there (a
    for or foreach variable after its header, a local of a block closed
    before cast_at), where a member of that name would be taken.
    inherited(open, arg, blocks), when given, is asked for a member that the
    enclosing class body (open: the offset of its `{`) does not declare,
    with the blocks around cast_at, and gives its type or None.
    declared_type(match) reads the type of each declaration, as
    _declared_type() does by default.
    """
    line = scopes.line(cast_at)
    blocks = () if around is None else around[line]
    declaration_re = _declaration_re(arg)
    method = scopes.method(line)
    if method is not None:
        start = scopes.offsets[method["start_line"] - 1]
        body = stripped.find("{", scopes.offsets[method["brace_line"] - 1])
        scope = stripped[start:cast_at]
        if re.search(r",\s*" + re.escape(arg) + r"\s*(?=;|=(?!=)|\[)", scope):
            return None
        found = set()
        closed = False
        for match in declaration_re.finditer(stripped, start, cast_at):
            at = match.start("type")
            if scopes.line(at) in scopes.dead:
                continue
            declared = declared_type(match)
            if declared is None:
                continue
            if at < body or _still_open(stripped, match.end(), cast_at):
                found.add("" if _apart(around, scopes.line(at), blocks) else declared)
            else:
                closed = True
        if found:
            return found.pop() if len(found) == 1 and "" not in found else None
        # `foreach (Object hit : list)` closes its `(` before a call in the
        # loop, which then took the type of a member `IEntity hit` (Codex
        # review of #125, E1).
        if closed and around is not None:
            return None
    enclosing = scopes.class_body(cast_at)
    if enclosing is None:
        return None
    open_brace, close_brace = enclosing
    # The same for every cast or call in the body under the same blocks:
    # read once per name.
    key = (open_brace, arg, blocks, declared_type)
    if key in scopes.members:
        return scopes.members[key]
    # The body is scanned once per name, whatever the blocks: scanning it
    # for each set of blocks around the calls made the rule 21 % slower than
    # the second version over the mods (third round of the review of #125).
    body_key = (open_brace, arg, declared_type)
    if body_key not in scopes.declarations:
        declarations = []
        for match in declaration_re.finditer(stripped, open_brace, close_brace):
            at = match.start("type")
            if scopes.line(at) in scopes.dead:
                continue
            inner = stripped[open_brace:at]
            if inner.count("{") - inner.count("}") != 1 or inner.count(
                "("
            ) != inner.count(")"):
                continue  # inside a method, or a parameter
            declared = declared_type(match)
            if declared is not None:
                declarations.append((declared, scopes.line(at)))
        scopes.declarations[body_key] = declarations
    found = {
        "" if _apart(around, declared_line, blocks) else declared
        for declared, declared_line in scopes.declarations[body_key]
    }
    if found:
        member = found.pop() if len(found) == 1 and "" not in found else None
    elif inherited is not None:
        member = inherited(open_brace, arg, blocks)
    else:
        member = None
    scopes.members[key] = member
    return member


def check_es_cast_unrelated_types(addon_sources, external_sources, vanilla_root):
    """addon_sources / external_sources: lists of (rel_path, stripped_source)."""
    hierarchy = Hierarchy()
    for _rel_path, stripped in list(addon_sources) + list(external_sources or []):
        hierarchy.add_source(stripped)
    vanilla_key = usable_vanilla_key(vanilla_root)
    if vanilla_key is not None:
        for _rel_path, text in vanilla_sources(vanilla_key):
            hierarchy.add_source(text)

    errors = []
    for rel_path, stripped in addon_sources:
        scopes = None
        for match in _CAST_RE.finditer(stripped):
            target, arg = match.group("target"), match.group("arg")
            if target == IMPLICIT_ROOT:
                continue
            target_chain = hierarchy.chain(target)
            if target_chain is None:
                continue
            if scopes is None:
                scopes = FileScopes(stripped)
            line = scopes.line(match.start())
            if line in scopes.dead:
                continue
            arg_type = _argument_type(stripped, scopes, arg, match.start())
            if arg_type is None or arg_type == IMPLICIT_ROOT:
                continue
            arg_chain = hierarchy.chain(arg_type)
            if arg_chain is None:
                continue
            if target in arg_chain or arg_type in target_chain:
                continue
            errors.append(
                {
                    "check": ES_CAST_UNRELATED_TYPES_RULE_ID,
                    "file": rel_path,
                    "line": line,
                    "message": ES_CAST_UNRELATED_TYPES_MESSAGE.format(
                        rel_path=rel_path, line=line, target=target, arg=arg,
                        arg_type=arg_type,
                        target_chain=" > ".join(target_chain),
                        arg_chain=" > ".join(arg_chain),
                    ),
                    "severity": "FAIL",
                    "rule_id": ES_CAST_UNRELATED_TYPES_RULE_ID,
                }
            )
    return errors
