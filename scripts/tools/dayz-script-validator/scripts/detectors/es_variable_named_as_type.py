import functools
import pathlib
import re

from detectors.es_reserved_word_identifier import (
    _FIRST_DECL_RE,
    _MODIFIERS,
    _NOT_A_TYPE,
    _TYPE,
)
from detectors.es_undefined_class_ref import (
    VANILLA_ANCHOR_CLASS,
    Definitions,
    _inside_template_args,
    _template_spans,
    blank_template_arguments,
    declarator_commas,
    vanilla_definitions,
)
from shared.dead_branches import (
    compatible,
    dead_lines,
    line_branches,
    line_tests,
    tests_agree,
)


ES_VARIABLE_NAMED_AS_TYPE_RULE_ID = "ES-VARIABLE-NAMED-AS-TYPE"


# claim: CLAIM-ENFORCE-VARIABLE-NAMED-AS-TYPE
# A variable, member or parameter whose name is already a type name stops the
# whole script module from compiling. Measured twice:
#
#   member  `bool Debug;` in a settings class (scripts/4_World), DayZDiag
#           1.29, 2026-09-28, pipeline inbox fb-20260928-025254-35c1
#           (corrected by 7ce1): the client refused the module with
#           `Variable name 'Debug' already used as type name`. Debug is a
#           vanilla class (3_game/tools/debug.c).
#   local   `Widget map = root.FindAnyWidget("mapWidget")`:
#           `Variable name 'map' already used as type name`, then
#           `Can't compile "Mission" script module!`
#           (enforce-script-reference pitfalls-advanced.md, SP-317).
#
# Parameters, and names that are an enum or a typedef rather than a class,
# have no failure on record; they are judged the same way because the error
# names a type, not a class. The match is exact case: Enforce identifiers are
# case-sensitive (enforce-script-reference SKILL.md, "A method named exactly
# like a vanilla class"), and no failure with a case-only match is on record,
# so a member `debug` is not reported.
#
# Type names come from the addon, every --external-scripts root and the
# vanilla tree. A module sees only the types of its own and lower modules, so
# a name is judged against the types declared in a module at or below the
# file's. A file outside any N_Module folder may compile in any module, so
# it is judged only against the types of 1_Core, which every module sees, and
# those of its own file; a type outside any N_Module folder counts only in
# its own file. (Mods pass of #113, 2026-10-17: in a mod recovered without
# its module folders, the rule reported a member `Attachments`, against the
# 5_Mission class Attachments, in a class that 4_World code uses.) Without a
# usable vanilla tree only the addon and the external roots are judged, and
# the vanilla part is listed as skipped in the report.
# The name fails wherever it compiles, so code under another mod's #ifdef is
# judged too; what never compiles (shared/dead_branches.py) is not. A type the
# addon or an external root declares only where it never compiles is no type,
# and a name is not judged against a type its own file declares only where the
# name never compiles with it: in another branch of the same block (`#ifdef X`
# type, `#else` member), or under the opposite test of a macro the file never
# #defines or #undefs (`#ifdef X` type, a later `#ifndef X` member). Blocks of
# different files are not related.

# `Type <name>` followed by what can only follow a declared name, as in
# ES-RESERVED-WORD-IDENTIFIER, with any name.
_DECL_RE = re.compile(
    r"(?:^|[;{}(,])[ \t]*" + _MODIFIERS + _TYPE
    + r"\s+(?P<name>[A-Za-z_]\w*)\s*(?=;|=(?!=)|\[|,|\)|:(?!:))",
    re.M,
)
_LATER_NAME_RE = re.compile(r",\s*(?P<name>[A-Za-z_]\w*)\s*(?=;|=(?!=)|\[|,)")

_MODULE_RE = re.compile(r"(?:^|[\\/])(?P<rank>[1-5])_[A-Za-z]+[\\/]")
_UNKNOWN_MODULE = 99
_CORE_MODULE = 1

# Vanilla is read raw: comments are dropped (a block comment line that starts
# with `class X` would declare X), strings are kept so a `//` or `/*` inside
# one does not cut the text.
_RAW_TOKEN_RE = re.compile(r'"(?:\\.|[^"\\\n])*"|//[^\n]*|/\*.*?\*/', re.S)

ES_VARIABLE_NAMED_AS_TYPE_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '{name}' names a variable, member or "
    "parameter, but '{name}' is already a type ({where}). The compiler "
    "refuses it with \"Variable name '{name}' already used as type name\" and "
    "the whole script module does not compile. Rename it."
)


def module_rank(rel_path):
    """1..5 for a file under N_Module/, _UNKNOWN_MODULE otherwise."""
    match = _MODULE_RE.search(str(rel_path).replace("\\", "/"))
    return int(match.group("rank")) if match else _UNKNOWN_MODULE


def _without_comments(text):
    return _RAW_TOKEN_RE.sub(
        lambda m: m.group(0) if m.group(0).startswith('"') else " ", text
    )


def declared_type_names(text):
    """Class, enum and typedef names declared in one text."""
    definitions = Definitions()
    definitions.add_source(text, variables=False)
    return definitions.types


@functools.lru_cache(maxsize=4)
def vanilla_sources(vanilla_key):
    """((relative path, text without comments), ...) of the vanilla tree."""
    root = pathlib.Path(vanilla_key)
    sources = []
    for path in sorted(root.rglob("*.c")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        sources.append((path.relative_to(root).as_posix(), _without_comments(text)))
    return tuple(sources)


@functools.lru_cache(maxsize=4)
def vanilla_type_ranks(vanilla_key):
    """{type name: lowest module rank that declares it} over the vanilla tree."""
    ranks = {}
    for rel_path, text in vanilla_sources(vanilla_key):
        rank = module_rank(rel_path)
        for name in declared_type_names(text):
            ranks[name] = min(rank, ranks.get(name, _UNKNOWN_MODULE))
    return ranks


def usable_vanilla_key(vanilla_root):
    """Resolved key of a vanilla tree that declares class Managed, or None."""
    if vanilla_root is None:
        return None
    key = str(pathlib.Path(vanilla_root).resolve())
    if VANILLA_ANCHOR_CLASS not in vanilla_definitions(key).classes:
        return None
    return key


def _compiled_type_names(stripped):
    """{type name: [(blocks, tests) of each declaration]} of the lines that compile.

    Blocks and tests are those of shared.dead_branches.line_branches() and
    line_tests(). Read line by line, so a `class` or `enum` whose name stands
    on the next line is missed.
    """
    dead = dead_lines(stripped)
    branches = line_branches(stripped)
    tests = line_tests(stripped)
    declared = {}
    for number, line in enumerate(stripped.split("\n"), start=1):
        if (
            number in dead
            or not tests_agree(tests[number], tests[number])
            or not any(word in line for word in ("class", "enum", "typedef"))
        ):
            continue
        for name in declared_type_names(line):
            declared.setdefault(name, []).append((branches[number], tests[number]))
    return declared


def _declared_names(stripped):
    """(offset, name) of every name in a declared-name position."""
    spans = _template_spans(stripped, spaced=True)
    # _TYPE reads blanked template arguments (blank_template_arguments); the
    # walk below reads stripped.
    blanked = blank_template_arguments(stripped)
    for match in _DECL_RE.finditer(blanked):
        if match.group("type") in _NOT_A_TYPE:
            continue
        if stripped[match.start()] == "," and _inside_template_args(
            spans, match.start()
        ):
            continue
        yield match.start("name"), match.group("name")
    starts = [
        match.end()
        for match in _FIRST_DECL_RE.finditer(blanked)
        if match.group("type") not in _NOT_A_TYPE
    ]
    for comma in declarator_commas(stripped, starts, spans):
        later = _LATER_NAME_RE.match(stripped, comma)
        if later:
            yield later.start("name"), later.group("name")


def _visible(rank, path, file_rank, rel_path):
    """True when rel_path, of module file_rank, sees a type of module rank.

    `path` is the addon file that declares the type, None outside the addon.
    """
    if path == rel_path:
        return True
    if rank == _UNKNOWN_MODULE:
        return False
    if file_rank == _UNKNOWN_MODULE:
        return rank == _CORE_MODULE
    return rank <= file_rank


def check_es_variable_named_as_type(
    addon_sources, external_sources, vanilla_root, vanilla_skip_reason=None
):
    """Return (errors, skipped).

    addon_sources / external_sources: lists of (rel_path, stripped_source).
    """
    if not addon_sources:
        return [], []
    # {name: [(rank, where, addon file, declarations)]}, the addon first so it
    # names the declaration. File and declarations are None outside the addon.
    types = {}
    for sources, where, own in (
        (addon_sources, "declared in the addon", True),
        (external_sources or [], "declared in an --external-scripts root", False),
    ):
        for rel_path, stripped in sources:
            rank = module_rank(rel_path)
            for name, declarations in _compiled_type_names(stripped).items():
                types.setdefault(name, []).append(
                    (rank, where, rel_path if own else None, declarations)
                )
    skipped = []
    vanilla_key = usable_vanilla_key(vanilla_root)
    if vanilla_key is None:
        if vanilla_root is None:
            reason = vanilla_skip_reason or "vanilla tree not available"
        else:
            reason = "the vanilla tree %s declares no class %s" % (
                vanilla_root, VANILLA_ANCHOR_CLASS
            )
        skipped.append(
            {
                "rule_id": ES_VARIABLE_NAMED_AS_TYPE_RULE_ID,
                "status": "SKIP",
                "reason": (
                    "%s. Names were judged only against the types the addon "
                    "and the --external-scripts roots declare; a name that is "
                    "a vanilla type (such as Debug) was not judged." % reason
                ),
            }
        )
    else:
        for name, rank in vanilla_type_ranks(vanilla_key).items():
            types.setdefault(name, []).append(
                (rank, "declared in the vanilla scripts tree", None, None)
            )

    errors = []
    for rel_path, stripped in addon_sources:
        file_rank = module_rank(rel_path)
        seen = set()
        dead = branches = tests = None
        # Offsets come in order, so lines are counted on from the last one:
        # counting from the start for each name grew with the square of the
        # names (fourth Codex review of #113, L2).
        line, counted = 1, 0
        for offset, name in sorted(_declared_names(stripped)):
            candidates = [
                entry for entry in types.get(name, ())
                if _visible(entry[0], entry[2], file_rank, rel_path)
            ]
            if not candidates:
                continue
            line += stripped.count("\n", counted, offset)
            counted = offset
            if dead is None:
                dead = dead_lines(stripped)
                branches = line_branches(stripped)
                tests = line_tests(stripped)
            if (
                (line, name) in seen
                or line in dead
                or not tests_agree(tests[line], tests[line])
            ):
                continue
            where = next(
                (
                    w for _rank, w, path, declarations in candidates
                    if path != rel_path
                    or any(
                        compatible(b, branches[line]) and tests_agree(t, tests[line])
                        for b, t in declarations
                    )
                ),
                None,
            )
            if where is None:
                continue
            seen.add((line, name))
            errors.append(
                {
                    "check": ES_VARIABLE_NAMED_AS_TYPE_RULE_ID,
                    "file": rel_path,
                    "line": line,
                    "message": ES_VARIABLE_NAMED_AS_TYPE_MESSAGE.format(
                        rel_path=rel_path, line=line, name=name, where=where
                    ),
                    "severity": "FAIL",
                    "rule_id": ES_VARIABLE_NAMED_AS_TYPE_RULE_ID,
                }
            )
    return errors, skipped
