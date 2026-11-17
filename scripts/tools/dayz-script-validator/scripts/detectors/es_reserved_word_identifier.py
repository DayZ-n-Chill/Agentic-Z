import re

from detectors.es_undefined_class_ref import (
    _TEMPLATE,
    blank_template_arguments,
    declarator_commas,
)
from shared.dead_branches import dead_lines


ES_RESERVED_WORD_IDENTIFIER_RULE_ID = "ES-RESERVED-WORD-IDENTIFIER"


# claim: CLAIM-ENFORCE-RESERVED-WORD-NAME
# A variable, member or parameter named with an Enforce keyword stops the
# whole script module from compiling, and the error rarely names the word.
# Only words whose use as a name failed in a real compile are listed:
#
#   sealed  parameter `vector sealed`, DayZDiag 1.29.163709, 2026-10-02:
#           `Expected name, not a keyword 'sealed'`, then
#           `Can't compile "World" script module!`
#   local   local `vector local;`, DayZDiag 1.30.164014 (Exp), 2026-09-28:
#           `Broken expression (missing ';'?)`, then
#           `Can't compile "Mission" script module!`
#   owned   local `EntityAI owned;`, 2026-07-20: `Broken expression (missing
#           ';'?)` (enforce-script-reference SKILL.md, SP-073)
#   out     a local named `out`: `Broken expression (missing ';'?)`
#           (enforce-script-reference SKILL.md, "Three ways to break the
#           compiler that do not produce a readable error")
#
# Vanilla uses all four as keywords, never as names: `sealed class Contact`
# (1_core/physics/contact.c:9), `local array<string> overridden`
# (4_world/plugins/pluginbase/pluginconfigviewer.c:153), `proto owned string
# GetModule()` (1_core/proto/enconvert.c:536), `out array<Man> players`
# (3_game/global/game.c:947). Other modifiers vanilla uses the same way
# (notnull, inout, autoptr, reference, volatile, external, event...) are left
# out until a compile failure is on record for them.
#
# The name fails wherever it compiles, so code under another mod's #ifdef is
# judged too; what never compiles (shared/dead_branches.py) is not.
RESERVED_WORDS = ("sealed", "local", "owned", "out")

_NOT_A_TYPE = {
    "return", "new", "delete", "else", "case", "typedef", "class", "enum",
    "goto", "extends", "modded", "override", "proto", "native", "static",
    "const", "private", "protected", "ref", "autoptr", "notnull", "inout",
    "out", "owned", "local", "reference", "event", "external", "volatile",
    "thread", "sealed", "if", "while", "for", "foreach", "switch", "break",
    "continue", "default",
}

_MODIFIERS = (
    r"(?:(?:ref|autoptr|const|static|private|protected|owned|notnull|out|"
    r"inout|local|reference)[ \t]+)*"
)
_TYPE = (
    r"(?P<type>[A-Za-z_]\w*)(?:[ \t]*" + _TEMPLATE + r")?(?:[ \t]*\[[^\]\n]*\])?"
)
_WORD = r"(?P<name>" + "|".join(RESERVED_WORDS) + r")\b"

# `Type <word>` followed by what can only follow a declared name: `;`, `=`
# (not `==`), `[`, `,`, `)`, or the `:` of a foreach. The leading `(` / `,`
# covers parameters and foreach variables; the leading `;`, `{`, `}` or start
# of line covers locals and members. The name may sit on the next line.
_DECL_RE = re.compile(
    r"(?:^|[;{}(,])[ \t]*" + _MODIFIERS + _TYPE
    + r"\s+" + _WORD + r"\s*(?=;|=(?!=)|\[|,|\)|:(?!:))",
    re.M,
)

# A later declarator of a declaration statement, `int a = 1, out = 0;`: a
# statement that opens with `Type name` and, outside every bracket, a comma
# followed by the word and then `;`, `=`, `[` or `,`.
_FIRST_DECL_RE = re.compile(
    r"(?:^|[;{}(])[ \t]*" + _MODIFIERS + _TYPE
    + r"\s+[A-Za-z_]\w*\s*(?=[=,;\[])",
    re.M,
)
_LATER_NAME_RE = re.compile(r",\s*" + _WORD + r"\s*(?=;|=(?!=)|\[|,)")


def _later_declarators(stripped, blanked):
    """(offset, word) of each reserved word named after a comma of a declaration.

    blanked: stripped through blank_template_arguments(), which _FIRST_DECL_RE
    reads.
    """
    starts = [
        match.end()
        for match in _FIRST_DECL_RE.finditer(blanked)
        if match.group("type") not in _NOT_A_TYPE
    ]
    for comma in declarator_commas(stripped, starts):
        later = _LATER_NAME_RE.match(stripped, comma)
        if later:
            yield later.start("name"), later.group("name")

ES_RESERVED_WORD_IDENTIFIER_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '{name}' is an Enforce keyword and cannot "
    "name a variable, member or parameter. The compiler rejects the whole "
    "script module, often with an error that does not name the word "
    "(\"Broken expression (missing ';'?)\", or \"Expected name, not a keyword "
    "'{name}'\"). Rename it."
)


def _declared_words(stripped_source):
    """(offset, word) of every reserved word in a declared-name position."""
    blanked = blank_template_arguments(stripped_source)
    for match in _DECL_RE.finditer(blanked):
        if match.group("type") not in _NOT_A_TYPE:
            yield match.start("name"), match.group("name")
    yield from _later_declarators(stripped_source, blanked)


def check_es_reserved_word_identifier(stripped_source, rel_path):
    errors = []
    seen = set()
    dead = None
    # Offsets come in order, so lines are counted on from the last one:
    # counting from the start for each word grew with the square of the
    # words (Codex review of e6d6, E9).
    line, counted = 1, 0
    for offset, name in sorted(_declared_words(stripped_source)):
        line += stripped_source.count("\n", counted, offset)
        counted = offset
        if dead is None:
            dead = dead_lines(stripped_source)
        if (line, name) in seen or line in dead:
            continue
        seen.add((line, name))
        errors.append(
            {
                "check": ES_RESERVED_WORD_IDENTIFIER_RULE_ID,
                "file": rel_path,
                "line": line,
                "message": ES_RESERVED_WORD_IDENTIFIER_MESSAGE.format(
                    rel_path=rel_path, line=line, name=name
                ),
                "severity": "FAIL",
                "rule_id": ES_RESERVED_WORD_IDENTIFIER_RULE_ID,
            }
        )
    return errors
