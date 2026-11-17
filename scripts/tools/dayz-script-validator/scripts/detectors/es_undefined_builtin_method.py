import bisect
import functools
import pathlib
import re

from detectors.es_cast_unrelated_types import (
    _CLASS_RE,
    IMPLICIT_ROOT,
    FileScopes,
    _argument_type,
    _declaration_re,
    _declared_type,
)
from detectors.es_protected_method_cross_class import _CALL_RE
from detectors.es_undeclared_static_member import (
    CLASS_ROOT_MEMBERS,
    class_bodies,
    top_level_names,
)
from detectors.es_undefined_class_ref import vanilla_definitions
from detectors.es_variable_named_as_type import usable_vanilla_key, vanilla_sources
from shared.dead_branches import line_branches, line_tests
from stripper import strip_enforce_comments_and_strings


ES_UNDEFINED_BUILTIN_METHOD_RULE_ID = "ES-UNDEFINED-BUILTIN-METHOD"


# claim: CLAIM-ENFORCE-UNDEFINED-BUILTIN-METHOD
# A call to a method that the game's own declaration of a built-in type does
# not have stops the whole script module from compiling. Pipeline inbox
# fb-20261103-150432-9f93 (LFSkateboard), DayZDiag 1.30.164200 server,
# 2026-11-03:
#
#   vector gU = gF.Cross(gR);
#   gR = gU.Cross(gF);
#
# with gF, gR and gU vector locals, stopped the server at script compile with
# "Undefined function 'vector.Cross'". The 1.30.164014 Exp scripts declare
# vector.Cross (1_Core/proto/EnConvert.c:239-246); the 1.30.164200 scripts the
# game compiled do not. The linter passed the call against either tree: no
# rule looked a method up on a built-in type.
#
# The built-in types are the classes the scripts declare for the engine's own
# types: bool, int, float, vector, string, typename, array, set and map (in
# 1.30.164200, 1_Core/proto/EnConvert.c, EnString.c and EnScript.c). Their
# members are read from the vanilla tree, so a verdict holds for the build
# that tree comes from; --game-root warns when it is not the game's
# (shared/vanilla_build.py).
#
# Judged only when everything is known, otherwise skipped without a word:
#   - the call is `T.Method(` with T a built-in type or a typedef of one,
#     and no variable of the file is named T (`Widget map;` then
#     `map.ClearFlags(`, which ES-VARIABLE-NAMED-AS-TYPE reports), or
#     `name.Method(` with name a plain name (not a call's result, a member
#     access or an index) whose one declared type, as a local still open at
#     the call, a parameter of the same function or a member of the enclosing
#     class body (the lookup of ES-CAST-UNRELATED-TYPES, where a declaration
#     under an #ifdef that is not around the call leaves the name unknown),
#     is a built-in type, a template of one (`array<string> names` is an
#     array; a `<...>` that the lookup read across other parameters leaves
#     the name unknown) or a typedef of one. A typedef counts when its name
#     has one target, no `[]` (`typedef int[] Physics` is a handle, not an
#     int) and no class declaration anywhere: `ResourceName` is a typedef of
#     string and also a class derived from it, so it is not judged;
#   - the vanilla tree declares the type as a class with a readable body;
#   - Method is no name at the top level of any declaration of that class,
#     in the vanilla tree, the addon or an --external-scripts root (`modded`
#     included, under any #ifdef, comments and strings dropped), nor of
#     Class, the implicit root of every class, nor any name written before a
#     `(` from such a declaration's header to the next class header. A
#     method, a field, a type, a modifier or a call there all count: the rule
#     may miss a bad call, it does not invent one.
# Lines that never compile (shared/dead_branches.py) are not judged, nor are
# lines that need a DayZ version macro defined. The engine defines one
# DAYZ_<major>_<minor>, that of the running build (1_Core/defines.c:11-14 in
# 1.30.164200; DAYZ_1_30 in the defines of that server's script log), and the
# vanilla tree does not say which build it is. Mods test an older one around
# the code of every later build (`#ifndef DAYZ_1_29`, LFSkateboard and
# DayZ-MCP): those lines are judged. A line under `#ifdef DAYZ_1_29`, or under
# the #else of `#ifndef DAYZ_1_29`, compiles on that one build, which may not
# be the tree's.

BUILTIN_TYPES = (
    "bool", "int", "float", "vector", "string", "typename", "array", "set", "map",
)

_HEADER_RE = re.compile(
    r"^[ \t]*(?:(?:modded|sealed|proto|native|inherited|static|external)\s+)*"
    r"class\s+(?:" + "|".join(BUILTIN_TYPES + (IMPLICIT_ROOT,)) + r")\b",
    re.M,
)
# `typedef array<string> TStringArray;`: the target's name, its template
# arguments, then the new name. Vanilla writes some typedefs without the `;`.
# In `typedef int[] Physics;` a `[` stands where the name should, so a handle
# never reads as an int.
_TYPEDEF_RE = re.compile(
    r"^[ \t]*typedef[ \t]+(?P<type>[A-Za-z_]\w*)(?:[ \t]*<[^;{}()\n]*>)?"
    r"[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*(?:;|$)",
    re.M,
)
_VERSION_MACRO_RE = re.compile(r"DAYZ_\d+_\d+\Z")
_CALLED_RE = re.compile(r"([A-Za-z_]\w*)\s*\(")

ES_UNDEFINED_BUILTIN_METHOD_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '{recv}.{method}(': {what}, and no "
    "declaration of {builtin} names '{method}': not the vanilla tree's "
    "({where}), no modded {builtin} of the addon or an --external-scripts "
    "root, not Class. The compiler stops with \"Undefined function "
    "'{builtin}.{method}'\" and the whole script module does not compile "
    "(DayZ 1.30.164200, on vector.Cross, which the 1.30.164014 Exp and "
    "1.30.164078 scripts declare). Check the method in the scripts of the "
    "build the addon runs on, and pass that tree as --vanilla-root."
)


def _one_template(targs):
    """True when targs is one template argument list: the `<` it opens
    closes at its end.

    _declaration_re() reads `<...>` lazily up to any `>` before the name, so
    in `F(array<ref X> a, bool b, map<string, int> m)` the match for m runs
    from array's `<` to map's `>` and names array as the type (measured on
    two mods, 2026-11-03: `m.GetKey(` and `m.Contains(` reported on array).
    """
    depth = 0
    text = targs.strip()
    for index, char in enumerate(text):
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
            if depth == 0:
                return index == len(text) - 1
    return False


def _declared_or_template(match):
    """_declared_type(), except that a declaration with one template
    argument list and no array brackets gives the template: `array<string>
    names` is an array. A match whose `<...>` spans other declarations stays
    unknown ("")."""
    declared = _declared_type(match)
    if (
        declared == ""
        and match.group("targs")
        and _one_template(match.group("targs"))
        and not match.group("arr")
        and match.group("next") != "["
    ):
        return match.group("type")
    return declared


def _declares_variable(stripped, name, scopes):
    """True when a line of the text that compiles declares a variable, member
    or parameter `name`. scopes: the FileScopes of stripped."""
    return any(
        _declared_type(match) is not None
        and scopes.line(match.start("type")) not in scopes.dead
        for match in _declaration_re(name).finditer(stripped)
    )


@functools.lru_cache(maxsize=4)
def _vanilla_builtins(vanilla_key):
    """(files, typedefs) of the vanilla tree, read once per tree.

    files: ((relative path, stripped text), ...) of the files that declare a
    built-in class or Class, read again from disk and stripped as the addon
    is, so their lines keep their numbers (vanilla_sources() folds a block
    comment into one space). typedefs: ((name, target), ...).
    """
    root = pathlib.Path(vanilla_key)
    files = []
    typedefs = []
    for rel_path, text in vanilla_sources(vanilla_key):
        typedefs.extend(
            (match.group("name"), match.group("type"))
            for match in _TYPEDEF_RE.finditer(text)
        )
        if not _HEADER_RE.search(text):
            continue
        try:
            raw = (root / rel_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        files.append((rel_path, strip_enforce_comments_and_strings(raw, rel_path)[0]))
    return tuple(files), tuple(typedefs)


class _Builtins:
    """The members of each built-in class, and the typedefs that name one."""

    def __init__(self, vanilla_key, sources):
        """sources: (rel_path, stripped text) of the addon and external roots."""
        files, typedefs = _vanilla_builtins(vanilla_key)
        self.members = {}
        self.where = {}
        self.unreadable = set()
        self.root_members = set(CLASS_ROOT_MEMBERS)
        self.classes = set(vanilla_definitions(vanilla_key).classes)
        self.typedefs = {}
        for name, target in typedefs:
            self.typedefs.setdefault(name, set()).add(target)
        for rel_path, text in files:
            self._add_bodies(text, rel_path)
        # Only a type the vanilla tree declares is judged: its members are
        # known there. The addon and the external roots only add to them.
        self.judged = set(self.where) - self.unreadable
        for _rel_path, text in sources:
            for match in _CLASS_RE.finditer(text):
                self.classes.add(match.group("name"))
            for match in _TYPEDEF_RE.finditer(text):
                self.typedefs.setdefault(match.group("name"), set()).add(
                    match.group("type")
                )
            if _HEADER_RE.search(text):
                self._add_bodies(text, None)
        self._resolved = {}
        self._members_of = {}
        self.type_names = sorted(
            name for name in set(BUILTIN_TYPES) | set(self.typedefs)
            if self.resolve(name)
        )
        # `Type name` for each type above: a superset of the declarations
        # _argument_type() can read as one of them.
        self._declaration_re = re.compile(
            r"\b(?:" + "|".join(map(re.escape, self.type_names)) + r")\b"
            r"(?:[ \t]*<[^;{}()\n]*?>)?(?:[ \t]*\[[^\]\n]*\])?"
            r"\s+(?P<name>[A-Za-z_]\w*)"
        ) if self.type_names else None

    def _add_bodies(self, text, vanilla_path):
        """vanilla_path: the file's path in the vanilla tree, None elsewhere.

        A class's names are those at the top level of its body, and every name
        written before a `(` from its header to the next class header. Counting
        brackets alone loses each name after a `(` that only one branch of an
        #ifdef closes, as in a declaration split across the branches (Grok
        review, 2026-11-03: `Length` and `Normalize` reported on vector).
        """
        headers = [match.start() for match in _CLASS_RE.finditer(text)]
        for match, span in class_bodies(text):
            name = match.group("name")
            if name != IMPLICIT_ROOT and name not in BUILTIN_TYPES:
                continue
            if vanilla_path is not None and name != IMPLICIT_ROOT:
                line = text.count("\n", 0, match.start("name")) + 1
                self.where.setdefault(name, []).append(
                    "%s:%d" % (vanilla_path, line)
                )
                if span is None:
                    self.unreadable.add(name)
            if span is None:
                continue
            following = bisect.bisect_right(headers, match.start())
            end = headers[following] if following < len(headers) else len(text)
            names = top_level_names(text[span[0] + 1:span[1]]) | set(
                _CALLED_RE.findall(text, match.end(), end)
            )
            if name == IMPLICIT_ROOT:
                self.root_members |= names
            else:
                self.members.setdefault(name, set()).update(names)

    def resolve(self, name):
        """The judged built-in type that a type or typedef name is, or None."""
        if name not in self._resolved:
            self._resolved[name] = self._resolve(name)
        return self._resolved[name]

    def _resolve(self, name):
        seen = set()
        while name not in BUILTIN_TYPES:
            targets = self.typedefs.get(name)
            if not targets or len(targets) != 1 or name in self.classes:
                return None
            if name in seen:
                return None
            seen.add(name)
            name = next(iter(targets))
        return name if name in self.judged else None

    def members_of(self, builtin):
        if builtin not in self._members_of:
            self._members_of[builtin] = (
                self.members.get(builtin, set()) | self.root_members
            )
        return self._members_of[builtin]

    def candidates(self, stripped):
        """Names the text declares after a judged type: the only receivers
        whose lookup can end on one."""
        if self._declaration_re is None:
            return set()
        return {
            match.group("name") for match in self._declaration_re.finditer(stripped)
        }


def _skip(reason):
    return {
        "rule_id": ES_UNDEFINED_BUILTIN_METHOD_RULE_ID,
        "status": "SKIP",
        "reason": reason,
    }


def check_es_undefined_builtin_method(
    addon_sources, external_sources, vanilla_root, vanilla_skip_reason=None
):
    """Return (errors, skipped).

    addon_sources / external_sources: lists of (rel_path, stripped_source).
    `skipped` lists what the rule could not judge, for the report's info
    block; it never changes the status.
    """
    if not addon_sources:
        return [], []
    vanilla_key = usable_vanilla_key(vanilla_root)
    if vanilla_key is None:
        if vanilla_root is None:
            return [], [_skip(
                "%s. Without the vanilla tree the members of vector, string, "
                "array and the other built-in types are unknown, so the rule "
                "does not run." % (vanilla_skip_reason or "vanilla tree not available")
            )]
        return [], [_skip(
            "the vanilla tree %s declares no class Managed, so it is not a DayZ "
            "scripts tree; the members of the built-in types are unknown, so "
            "the rule does not run." % vanilla_root
        )]

    builtins = _Builtins(
        vanilla_key, list(addon_sources) + list(external_sources or [])
    )
    errors = []
    for rel_path, stripped in addon_sources:
        candidates = None
        scopes = None
        variables = {}
        for match in _CALL_RE.finditer(stripped):
            recv, method = match.group("recv"), match.group("method")
            static = builtins.resolve(recv)
            if static is not None:
                if method in builtins.members_of(static):
                    continue
            else:
                if candidates is None:
                    candidates = builtins.candidates(stripped)
                if recv not in candidates:
                    continue
            if scopes is None:
                scopes = FileScopes(stripped)
                around = line_branches(stripped)
                tests = line_tests(stripped)
            line = scopes.line(match.start())
            if line in scopes.dead or any(
                defined and _VERSION_MACRO_RE.match(macro)
                for macro, defined in tests[line]
            ):
                continue
            declared = None
            builtin = static
            if builtin is not None:
                # `Widget map = ...; map.ClearFlags(...)` names a variable
                # after the type, which ES-VARIABLE-NAMED-AS-TYPE reports: the
                # call is not the type's (measured on a mod's backup,
                # 2026-11-03).
                if recv not in variables:
                    variables[recv] = _declares_variable(stripped, recv, scopes)
                if variables[recv]:
                    continue
            else:
                declared = _argument_type(
                    stripped, scopes, recv, match.start(), around=around,
                    declared_type=_declared_or_template,
                )
                builtin = builtins.resolve(declared) if declared else None
                if builtin is None or method in builtins.members_of(builtin):
                    continue
            if declared is None:
                what = (
                    "'%s' is a built-in type" % recv if recv == builtin
                    else "'%s' is a typedef of %s" % (recv, builtin)
                )
            elif declared == builtin:
                what = "'%s' is declared as %s" % (recv, builtin)
            else:
                what = "'%s' is declared as %s, a typedef of %s" % (
                    recv, declared, builtin
                )
            errors.append(
                {
                    "check": ES_UNDEFINED_BUILTIN_METHOD_RULE_ID,
                    "file": rel_path,
                    "line": line,
                    "message": ES_UNDEFINED_BUILTIN_METHOD_MESSAGE.format(
                        rel_path=rel_path, line=line, recv=recv, method=method,
                        what=what, builtin=builtin,
                        where=", ".join(builtins.where[builtin]),
                    ),
                    "severity": "FAIL",
                    "rule_id": ES_UNDEFINED_BUILTIN_METHOD_RULE_ID,
                }
            )
    return errors, []
