import bisect
import functools
import re

from detectors.es_cast_unrelated_types import (
    _CLASS_RE,
    IMPLICIT_ROOT,
    FileScopes,
    Hierarchy,
    _argument_type,
    _declaration_re,
    _declared_type,
)
from detectors.es_protected_method_cross_class import _CALL_RE
from detectors.es_undeclared_static_member import class_bodies
from detectors.es_variable_named_as_type import (
    _UNKNOWN_MODULE,
    module_rank,
    usable_vanilla_key,
    vanilla_sources,
)
from shared.dead_branches import dead_lines, line_branches


ES_PROTO_ARGUMENT_DOWNCAST_RULE_ID = "ES-PROTO-ARGUMENT-DOWNCAST"


# claim: CLAIM-ENFORCE-PROTO-ARGUMENT-DOWNCAST
# A name passed to a parameter of a `proto` method, when the parameter's
# class derives from the class the name is declared as. Pipeline inbox
# fb-20261006-030019-e074, DayZ 1.30.164014 server:
#
#   DayZPhysics.RaycastRV(from, to, pos, dir, comp, hits, hitEntity,
#       m_Human, true, false, ObjIntersectGeom)
#
# with hitEntity an IEntity (the out argument of CollisionMoveTest) at the
# Object parameter 6 was refused with "Unsafe down-casting, use
# 'Object.Cast'", "Types 'IEntity' and 'Object' are unrelated" and "Cannot
# convert 'IEntity' to 'Object' for argument '6' to method 'RaycastRV'", and
# the World module did not compile. The compiler counts arguments from 0.
# DayZDiag 1.30.164289 (2026-11-09, pipeline inbox e074, a mod's 4_World
# script) refused that call again, and refused an Object passed to the
# EntityAI parameter 0 of ItemPreviewWidget.SetItem, the shape this rule
# had found in a mod:
#
#   static void Show(ItemPreviewWidget preview, Object obj)
#   {
#       preview.SetItem(obj);
#   }
#
# with "Unsafe down-casting, use 'EntityAI.Cast' for safe down-casting",
# "Types 'Object' and 'EntityAI' are unrelated" and "Cannot convert
# 'Object' to 'EntityAI' for argument '0' to method 'SetItem'", and the
# World module did not compile; a retail build is not measured for it.
# That Object derives from IEntity, and EntityAI from Object, is read from
# the vanilla tree when the rule runs. Only those two pairs are measured,
# so an IEntity where a proto takes an Object and an Object where it takes
# an EntityAI are FAIL, and any other class above the parameter's is WARN.
# An argument of a script method, an argument of an unrelated class and a
# down-cast in an assignment are not judged.
#
# Judged only when everything is known, otherwise skipped without a word:
#   - the call is in a method that shared/method_recognition.py reads (not
#     one whose return type has template arguments, `array<T> F(`);
#   - it is `recv.Method(` with recv a class, or a plain name with one
#     plain declared type, as a local still open at the call, a parameter or
#     a member of the enclosing class (the lookup of ES-CAST-UNRELATED-TYPES),
#     or else as a member of another body of that class or of the nearest
#     class up its chain that declares it. Of another file, a body counts
#     when both files are under N_Module folders (1_Core to 5_Mission) and
#     its module is not later than the call's (a later one is compiled
#     after it); when either is under no such folder, a declaration there
#     leaves the name unknown. A declaration under an #if, #ifdef or #ifndef
#     leaves the name unknown, unless it is in the call's file under blocks
#     that are all around the call. A name that the method declares before
#     the call only where that declaration is no longer open at the call (a
#     for or foreach variable, for a call in the loop's body or after it, or
#     a local of a block closed before the call) is unknown, also where a
#     member has that name; a call in that for's own header, as in its
#     condition, takes the variable's type;
#   - up the `extends` chain of that class, resolved as in
#     ES-CAST-UNRELATED-TYPES, the first class with a declaration (modded
#     included) whose body names Method before a `(` at its top level
#     declares it `proto` in every one of them, with one parameter list. A
#     declaration whose `(` is on a line that never compiles does not
#     count, and one with a line from its start to its `(` under an #if,
#     #ifdef or #ifndef leaves the method unknown;
#   - the argument is a plain name with one plain declared type, looked up
#     as the receiver is, and the parameter at its index is neither `out`
#     nor `inout` and has a plain class type whose chain resolves;
#   - that chain holds the argument's class above the parameter's own.
#     Class, the implicit root, is not judged as the argument's class.
# A call whose arguments hold `<`, `>` or a directive is skipped, and so is
# one with more arguments than parameters. Proto methods are read from the
# addon, every --external-scripts root and the vanilla tree (comments
# dropped, strings blanked), so without a vanilla tree no vanilla proto is
# judged. Lines that never compile (shared/dead_branches.py) are not judged.

_IDENT_RE = re.compile(r"[A-Za-z_]\w*")
_NAME_RE = re.compile(r"[A-Za-z_]\w*\Z")
_STRING_RE = re.compile(r'"(?:\\.|[^"\\\n])*"')
_ATTRIBUTES_RE = re.compile(r"(?:\[[^\]]*\]\s*)*")
_BRACKET_RE = re.compile(r"[()\[\]]")
_MARK_RE = re.compile(r"[<>#]")
# What may stand before a parameter's type. The method writes an `out` or
# `inout` argument, and that direction is not judged.
_PARAMETER_MODIFIERS = frozenset({
    "out", "inout", "notnull", "const", "owned", "ref", "autoptr", "local",
})
_WRITTEN = frozenset({"out", "inout"})
# (argument's class, parameter's class) of each refusal on record, and
# where it was refused, for the FAIL message.
_MEASURED = {
    ("IEntity", "Object"): (
        "DayZ 1.30, at DayZPhysics.RaycastRV, where it also said \"Types "
        "'IEntity' and 'Object' are unrelated\""
    ),
    ("Object", "EntityAI"): (
        "DayZDiag 1.30.164289, at ItemPreviewWidget.SetItem, argument '0', "
        "where it also said \"Types 'Object' and 'EntityAI' are unrelated\""
    ),
}

ES_PROTO_ARGUMENT_DOWNCAST_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '{recv}.{method}(': argument {index} "
    "(counted from 0), '{arg}', is declared as {arg_type}, and the proto "
    "{owner}.{method} takes {param_type} there, which derives from it "
    "({param_chain}). The compiler refuses the implicit down-cast with "
    "\"Cannot convert '{arg_type}' to '{param_type}' for argument '{index}' "
    "to method '{method}'\" and the whole script module does not compile "
    "({measured}). Pass {param_type}.Cast({arg}), "
    "which is null when it is not one, or declare '{arg}' as {param_type}."
)
ES_PROTO_ARGUMENT_DOWNCAST_WARN_MESSAGE = (
    "[WARN] {rel_path} line {line}: '{recv}.{method}(': argument {index} "
    "(counted from 0), '{arg}', is declared as {arg_type}, and the proto "
    "{owner}.{method} takes {param_type} there, which derives from it "
    "({param_chain}): an implicit down-cast. DayZ 1.30 refused two, an "
    "IEntity where DayZPhysics.RaycastRV takes an Object and an Object "
    "where ItemPreviewWidget.SetItem takes an EntityAI, and the script "
    "module did not compile; whether it refuses {arg_type} where "
    "{param_type} is taken is not measured. Pass {param_type}.Cast({arg}), "
    "which is null when it is not one, or declare '{arg}' as {param_type}."
)


def _closing(text, at, opener, closer):
    """Offset of the bracket that closes the `opener` at `at`, or None."""
    depth = 0
    for index in range(at, len(text)):
        if text[index] == opener:
            depth += 1
        elif text[index] == closer:
            depth -= 1
            if depth == 0:
                return index
    return None


def _heads(body):
    """(offset, text) of the top-level statements of a class body, each up to
    `;` or a body.

    None when a bracket does not close: the body cannot be read.
    """
    heads = []
    start = 0
    braces = parens = 0
    for index, char in enumerate(body):
        if braces:
            if char == "{":
                braces += 1
            elif char == "}":
                braces -= 1
                if not braces:
                    start = index + 1
            continue
        if parens == 0 and char in "{;":
            heads.append((start, body[start:index]))
            start = index + 1
            braces = 1 if char == "{" else 0
            continue
        if char == "(":
            parens += 1
        elif char == ")":
            parens -= 1
    if braces or parens:
        return None
    heads.append((start, body[start:]))
    return heads


def _parameters(text):
    """((modifiers, type) or None, ...) of a parameter list.

    type is None for a type that is not a plain name (a template, an array);
    a parameter that does not read as modifiers, a type and a name is None.
    """
    pieces = []
    depth = 0
    start = 0
    for index, char in enumerate(text):
        if char in "(<[":
            depth += 1
        elif char in ")>]":
            depth -= 1
        elif char == "," and depth == 0:
            pieces.append(text[start:index])
            start = index + 1
    pieces.append(text[start:])
    parameters = []
    for piece in pieces:
        declaration = piece.split("=", 1)[0]
        words = _IDENT_RE.findall(declaration)
        if len(words) < 2 or not set(words[:-2]) <= _PARAMETER_MODIFIERS:
            parameters.append(None)
            continue
        # A template is no modifier, so only an array is left to refuse.
        plain = "[" not in declaration
        parameters.append((frozenset(words[:-2]), words[-2] if plain else None))
    return tuple(parameters)


def _method(head):
    """(name, is proto, parameters, offset of its start, offset of its `(`)
    of a method head, or None. Offsets are in head.

    Blank lines and directives before the declaration are dropped; it starts
    at its attributes. A parameter whose text holds a directive does not
    read as modifiers, a type and a name.
    """
    lines = head.split("\n")
    # By index: dropping each line from the front of the list cost the
    # square of their number (Codex review of #125, N5).
    first = 0
    while first < len(lines) and (
        not lines[first].strip() or lines[first].lstrip().startswith("#")
    ):
        first += 1
    rest = "\n".join(lines[first:]).lstrip()
    start = len(head) - len(rest)
    rest = rest[_ATTRIBUTES_RE.match(rest).end():]
    open_at = rest.find("(")
    if open_at < 0:
        return None
    before = rest[:open_at]
    if "=" in before:
        return None  # a field set by a call
    words = _IDENT_RE.findall(before)
    if not words:
        return None
    close_at = _closing(rest, open_at, "(", ")")
    return (
        words[-1],
        "proto" in words,
        _parameters(rest[open_at + 1:close_at]),
        start,
        len(head) - len(rest) + open_at,
    )


class _Lines:
    """Whether the lines of one text compile, read when first asked
    (shared/dead_branches.py)."""

    def __init__(self, text):
        self.text = text
        self._read = None

    def _branches(self):
        """(dead_lines(), line_branches()) of the text, () without a directive."""
        if self._read is None:
            self._read = (
                (dead_lines(self.text), line_branches(self.text))
                if "#" in self.text else ()
            )
        return self._read

    def blocks(self, at):
        """None when the line of `at` never compiles, otherwise the #if,
        #ifdef and #ifndef blocks around it, () for none."""
        read = self._branches()
        if not read:
            return ()
        dead, branches = read
        line = self.text.count("\n", 0, at) + 1
        return None if line in dead else branches[line]

    def plain(self, start, end):
        """True when no line from that of `start` to that of `end` is under
        a block (a line that never compiles and is under none is a
        directive)."""
        read = self._branches()
        if not read:
            return True
        branches = read[1]
        first = self.text.count("\n", 0, start) + 1
        last = first + self.text.count("\n", start, end)
        return not any(branches[line] for line in range(first, last + 1))


class ClassBodies:
    """Every class body of the scanned trees, with the methods at its top level."""

    def __init__(self):
        # {class: [(module rank, lines, (open, close) or None, None for a body
        #  that cannot be read, or {method: [(is proto, parameters, offset of
        #  its start, offset of its `(`), ...]}), ...]}
        self.bodies = {}
        self.names = set()
        # {(class, name): what _declarations() read}
        self._members = {}

    def add_source(self, text, rank):
        """rank: the module_rank() of the file of text."""
        lines = _Lines(text)
        for match, span in class_bodies(text):
            heads = None if span is None else _heads(text[span[0] + 1:span[1]])
            methods = None
            if heads is not None:
                methods = {}
                for start, head in heads:
                    found = _method(head)
                    if found is None:
                        continue
                    name, proto, parameters, begin, at = found
                    offset = span[0] + 1 + start
                    methods.setdefault(name, []).append(
                        (proto, parameters, offset + begin, offset + at)
                    )
                    if proto:
                        self.names.add(name)
            self.bodies.setdefault(match.group("name"), []).append(
                (rank, lines, span, methods)
            )

    def extend(self, other):
        for name, bodies in other.bodies.items():
            self.bodies.setdefault(name, []).extend(bodies)
        self.names |= other.names

    def proto(self, chain, method):
        """(class, parameters) of the proto `method` that chain[0] reaches, or None."""
        for cls in chain:
            bodies = self.bodies.get(cls)
            if not bodies or any(methods is None for _r, _l, _s, methods in bodies):
                return None
            found = []
            for _rank, lines, _span, methods in bodies:
                for proto, parameters, start, at in methods.get(method, ()):
                    if lines.blocks(at) is None:
                        continue  # its `(` never compiles
                    # A word before the `(` may not compile, as `proto` under
                    # #if 0 (Codex review of #125, N2).
                    if not lines.plain(start, at):
                        return None
                    found.append((proto, parameters))
            if not found:
                continue
            signatures = {parameters for _proto, parameters in found}
            if not all(proto for proto, _parameters in found) or len(signatures) != 1:
                return None
            return cls, signatures.pop()
        return None

    def _declarations(self, cls, name):
        """[(module rank, lines, None for a body that cannot be read, or
        [(type, its blocks), ...] of the declarations of `name` at its top
        level on lines that compile), ...], one per body of cls.

        Read once per class and name: every call of every file asks again.
        """
        key = (cls, name)
        if key in self._members:
            return self._members[key]
        declaration_re = _declaration_re(name)
        read = []
        for rank, lines, span, methods in self.bodies.get(cls, ()):
            if methods is None:
                read.append((rank, lines, None))
                continue
            open_brace, close_brace = span
            text = lines.text
            declarations = []
            for match in declaration_re.finditer(text, open_brace, close_brace):
                at = match.start("type")
                blocks = lines.blocks(at)
                if blocks is None:
                    continue
                inner = text[open_brace:at]
                if inner.count("{") - inner.count("}") != 1 or inner.count(
                    "("
                ) != inner.count(")"):
                    continue  # inside a method, or a parameter
                declared = _declared_type(match)
                if declared is not None:
                    declarations.append((declared, blocks))
            read.append((rank, lines, declarations))
        self._members[key] = read
        return read

    def member(self, cls, name, rank, text, blocks):
        """The type of the member `name` at the top level of the bodies of
        cls, as a call in `text`, a file of module `rank`, sees it from a
        line under `blocks` (line_branches()).

        A body in a later module than the call's is not seen (Codex review
        of #125, N3). None when no body seen declares it; "" when it is not
        one plain type or may not be: a body cannot be read, a body of
        another file or the call is of no known module, or a declaration is
        under a block that is not around the call (in another file, under
        any block: Codex review of #125, N1).
        """
        found = set()
        for body_rank, lines, declarations in self._declarations(cls, name):
            here = lines.text is text
            ranked = _UNKNOWN_MODULE not in (body_rank, rank)
            if not here and ranked and body_rank > rank:
                continue
            if declarations is None:
                return ""
            for declared, around in declarations:
                if here:
                    sure = around == blocks[:len(around)]
                else:
                    sure = ranked and not around
                found.add(declared if sure else "")
        if not found:
            return None
        return found.pop() if len(found) == 1 and "" not in found else ""


@functools.lru_cache(maxsize=4)
def _vanilla_index(vanilla_key):
    """The Hierarchy and ClassBodies of the vanilla tree, strings blanked.

    Built once per tree: the 3042 files of 1.30 took about 2.8 s to read on
    every call (Codex review of #125, D9). Callers copy what they extend.
    """
    hierarchy = Hierarchy()
    bodies = ClassBodies()
    for rel_path, text in vanilla_sources(vanilla_key):
        text = _STRING_RE.sub(lambda m: " " * len(m.group(0)), text)
        hierarchy.add_source(text)
        bodies.add_source(text, module_rank(rel_path))
    return hierarchy, bodies


def _body_classes(stripped):
    """{offset of the `{` of each class body, as FileScopes reads it: class},
    None for a brace two headers share."""
    classes = {}
    for match in _CLASS_RE.finditer(stripped):
        if match.group("after"):
            continue
        brace = stripped.find("{", match.end())
        classes[brace] = None if brace in classes else match.group("name")
    return classes


def _inherited_member(
    hierarchy, bodies, classes, rank, text, open_brace, name, blocks
):
    """The type of the member `name` that the class whose body opens at
    open_brace (classes: _body_classes()) declares in another body, or
    else the nearest class up its chain that declares it, as a call under
    `blocks` in text, a file of module rank, sees it (ClassBodies.member());
    or None."""
    cls = classes.get(open_brace)
    for owner in (hierarchy.chain(cls) if cls else None) or ():
        declared = bodies.member(owner, name, rank, text, blocks)
        if declared is not None:
            return declared or None
    return None


def _brackets(stripped):
    """({offset of each `(` or `[`: offset of the bracket that closes it},
    sorted offsets of each `<`, `>` and `#`) of one file."""
    closes = {}
    opened = []
    for match in _BRACKET_RE.finditer(stripped):
        if match.group() in "([":
            opened.append(match.start())
        elif opened:
            closes[opened.pop()] = match.start()
    return closes, [match.start() for match in _MARK_RE.finditer(stripped)]


def _arguments(stripped, open_at, closes, marks):
    """The arguments, stripped, of the call whose `(` is at open_at, or None.

    closes and marks: the _brackets() of stripped. An argument that holds a
    bracket is "": it is no plain name, and copying it out made a call of
    nested calls cost the square of its depth (Codex review of #125, D8).
    None when the arguments hold `<` or `>` (template arguments and
    comparisons put commas the split cannot tell apart) or a directive, or
    never close.
    """
    close_at = closes.get(open_at)
    if close_at is None:
        return None
    if bisect.bisect_left(marks, open_at) != bisect.bisect_left(marks, close_at):
        return None
    pieces = []
    start = index = open_at + 1
    nested = False
    while index < close_at:
        char = stripped[index]
        if char in "([":
            nested = True
            index = closes[index]
        elif char == ",":
            pieces.append("" if nested else stripped[start:index].strip())
            start = index + 1
            nested = False
        index += 1
    pieces.append("" if nested else stripped[start:close_at].strip())
    return pieces


def check_es_proto_argument_downcast(addon_sources, external_sources, vanilla_root):
    """addon_sources / external_sources: lists of (rel_path, stripped_source).

    Returns (errors, warnings).
    """
    if not any(_CALL_RE.search(stripped) for _rel_path, stripped in addon_sources):
        return [], []
    hierarchy = Hierarchy()
    bodies = ClassBodies()
    vanilla_key = usable_vanilla_key(vanilla_root)
    if vanilla_key is not None:
        vanilla_hierarchy, vanilla_bodies = _vanilla_index(vanilla_key)
        hierarchy.declarations = {
            name: list(entries)
            for name, entries in vanilla_hierarchy.declarations.items()
        }
        hierarchy.definitions.merge(vanilla_hierarchy.definitions)
        hierarchy.not_classes |= vanilla_hierarchy.not_classes
        bodies.extend(vanilla_bodies)
    for rel_path, stripped in list(addon_sources) + list(external_sources or []):
        hierarchy.add_source(stripped)
        bodies.add_source(stripped, module_rank(rel_path))

    errors = []
    warnings = []
    for rel_path, stripped in addon_sources:
        scopes = None
        for match in _CALL_RE.finditer(stripped):
            recv, method = match.group("recv"), match.group("method")
            if method not in bodies.names:
                continue
            if scopes is None:
                scopes = FileScopes(stripped)
                closes, marks = _brackets(stripped)
                around = line_branches(stripped)
                inherited = functools.partial(
                    _inherited_member, hierarchy, bodies, _body_classes(stripped),
                    module_rank(rel_path), stripped,
                )
            line = scopes.line(match.start())
            if line in scopes.dead or scopes.method(line) is None:
                continue
            recv_type = (
                recv if hierarchy.is_plain_class(recv)
                else _argument_type(
                    stripped, scopes, recv, match.start(), inherited, around
                )
            )
            chain = hierarchy.chain(recv_type) if recv_type else None
            found = bodies.proto(chain, method) if chain else None
            if found is None:
                continue
            owner, parameters = found
            arguments = _arguments(stripped, match.end() - 1, closes, marks)
            if arguments is None or len(arguments) > len(parameters):
                continue
            for index, (arg, parameter) in enumerate(zip(arguments, parameters)):
                if parameter is None or _NAME_RE.match(arg) is None:
                    continue
                modifiers, param_type = parameter
                if modifiers & _WRITTEN or param_type is None:
                    continue
                param_chain = hierarchy.chain(param_type)
                if param_chain is None:
                    continue
                arg_type = _argument_type(
                    stripped, scopes, arg, match.start(), inherited, around
                )
                if arg_type == IMPLICIT_ROOT or arg_type not in param_chain[1:]:
                    continue
                measured = _MEASURED.get((arg_type, param_type))
                message = (
                    ES_PROTO_ARGUMENT_DOWNCAST_MESSAGE if measured
                    else ES_PROTO_ARGUMENT_DOWNCAST_WARN_MESSAGE
                )
                (errors if measured else warnings).append(
                    {
                        "check": ES_PROTO_ARGUMENT_DOWNCAST_RULE_ID,
                        "file": rel_path,
                        "line": line,
                        "message": message.format(
                            rel_path=rel_path, line=line, recv=recv,
                            method=method, index=index, arg=arg,
                            arg_type=arg_type, owner=owner,
                            param_type=param_type,
                            param_chain=" > ".join(param_chain),
                            measured=measured,
                        ),
                        "severity": "FAIL" if measured else "WARN",
                        "rule_id": ES_PROTO_ARGUMENT_DOWNCAST_RULE_ID,
                    }
                )
    return errors, warnings
