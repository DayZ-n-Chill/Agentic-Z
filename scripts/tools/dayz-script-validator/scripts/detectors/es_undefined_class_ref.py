import bisect
import functools
import pathlib
import re

# Bohemia's own patches, by name: mods use the DZ_ prefix too.
from shared.vanilla_patches import VANILLA_PATCHES


ES_UNDEFINED_CLASS_REF_RULE_ID = "ES-UNDEFINED-CLASS-REF"


# claim: CLAIM-ENFORCE-UNDEFINED-TYPE-REF
# Observed on 2026-09-19 auditing netcopdev/TransferZ PR #12 (head 11da911): the
# PR deletes Scripts/4_World/TransferZ/TransferZ_ExternalStagingSortPlanner.c
# (class TransferZExternalStagingSortPlanner) while
# Scripts/5_Mission/TransferZ/TransferZ_MaintenanceClient.c:59 still calls
#
#   int sortResult = TransferZExternalStagingSortPlanner.Sort(player, source);
#
# The type exists in no module of the addon, of vanilla or of its one
# dependency (CF), so the Mission module cannot compile. The linter returned
# WARN with 0 errors on that tree: every rule read one file, and no rule asked
# whether a name used as a type is declared anywhere. The failure follows from
# the missing declaration; it was not booted.
#
# A reference is judged only where the identifier can only be a type:
#   - `Name.Method(`          static call, `Name.Cast(` included
#   - `new Name` / `new X<Name>`
#   - `Name var =|;|,|[`      typed declaration at the start of a line (locals,
#                             members, one-per-line parameters)
# and only for class-like names (first letter upper case). A static-call
# receiver can also be a variable, so a name declared as a variable, member or
# parameter anywhere in the scanned trees is not judged in that form.
#
# The universe of declarations is the addon, the vanilla scripts tree and every
# --external-scripts root. A verdict needs that universe to be complete, so the
# rule reports SKIP in the result's info block -- never a finding -- when:
#   - there is no usable vanilla tree (absent, or declaring no class Managed):
#     every vanilla type would look undefined;
#   - the addon requires, directly or through a scanned dependency, an addon
#     that is not a vanilla patch (shared/vanilla_patches.py) and that no
#     scanned root declares in CfgPatches, or a requiredAddons[] entry is not
#     a string literal: the type may live there;
#   - no config.cpp in the tree declares requiredAddons[] at all: the
#     dependencies are unknown.
# The SKIP lists the unresolved names; passing the dependency's root (the
# folder with its config.cpp) with --external-scripts turns them into verdicts.
# Code under #ifdef/#ifndef is judged only when the macro is known: tested by
# vanilla (engine and build flags), #define'd by the scanned scripts, or listed
# in a scanned CfgMods defines[]. Anything else is usually an optional mod's
# flag, and that code compiles only when the mod is loaded. A macro that a
# scanned script #defines, or a scanned CfgMods defines[] lists, on a line the
# preprocessor always keeps (outside every block, or under an #ifdef of a macro
# the same file defines before it) is always on, so its #ifndef and #else
# branches never compile and are not judged either.

_CLASS_LIKE_RE = re.compile(r"^[A-Z]")

# Vanilla is read raw, and writes `/*sealed*/ class SurfaceDetectionParameters`
# (3_game/surfaceinfo.c:74): a block comment may precede the keyword.
_LEADING_COMMENTS = r"(?:/\*.*?\*/[ \t]*)*"
_CLASS_DEF_RE = re.compile(
    r"^[ \t]*" + _LEADING_COMMENTS
    + r"(?:(?:modded|sealed|proto|native|inherited|static|external)\s+)*"
    r"class\s+(?P<name>[A-Za-z_]\w*)(?:\s*<(?P<params>[^;{}>]*)>)?",
    re.M,
)
_TEMPLATE_PARAM_RE = re.compile(r"\bClass\s+(?P<name>[A-Za-z_]\w*)")
_ENUM_DEF_RE = re.compile(
    r"^[ \t]*" + _LEADING_COMMENTS + r"enum\s+(?P<name>[A-Za-z_]\w*)", re.M
)
# Vanilla writes typedefs with and without the trailing `;`
# (`typedef map<InventoryItem, vector> TItemsMap`), often with a `//` note.
_TYPEDEF_RE = re.compile(r"^[ \t]*typedef\b(?P<body>[^;\n]*)", re.M)
_LAST_IDENT_RE = re.compile(r"(?P<name>[A-Za-z_]\w*)\s*$")
# Vanilla's tested macros are engine/build flags (SERVER, DIAG_DEVELOPER...):
# code under them compiles in some real build, so it is judged. A mod only
# contributes the macros it DEFINES; the ones it merely tests are usually
# another mod's flag, and that code compiles only when that mod is loaded.
_MACRO_TEST_RE = re.compile(r"^[ \t]*#[ \t]*(?:ifdef|ifndef)[ \t]+(?P<name>\w+)", re.M)
_MACRO_DEFINE_RE = re.compile(r"^[ \t]*#[ \t]*define[ \t]+(?P<name>\w+)", re.M)
# `Type Name` followed by what can only follow a declared name. Collected for
# class-like names only: those are the ones a static-call receiver could be.
# These patterns read a text whose template arguments are blanked
# (blank_template_arguments), where a template span is its `<`, spaces and
# its own `>` however deep it nested. A greedy `<...>` swallowed
# `Symptoms_primary` in `array<ref Param> Symptoms_primary, array<ref Param>
# Symptoms_secondary` (4_world/classes/playersymptoms/statemanager.c:827),
# and a lazy one could still run on to any later `>` of the statement, so
# every place a declaration can start read to its end: time quadratic in the
# length of a long statement (inbox fb-20261017-175254-e6d6). Vanilla closes
# some with one `>` too many (`map<string, int>> name;`, 3_game/global/
# ammotypes.c:80 and :100 on 1.30, :47 and :60 on 1.29), so a run of `>`
# closes one (Codex review of e6d6, E4).
_TEMPLATE = r"<[^<>;{}()\n]*>+"
_DECLARED_NAME_RE = re.compile(
    r"\b[A-Za-z_]\w*(?:[ \t]*" + _TEMPLATE + r")?(?:[ \t]*\[[^\]\n]*\])?"
    r"[ \t]+(?P<name>[A-Z]\w*)[ \t]*(?=[=;,)\[:])"
)
# The first declarator of `Type a, B;` (any case), so the names after its
# top-level commas can be collected too: `string errorMessage, path;` is
# vanilla (3_game/cfgplayerrestrictedareahandler.c:33).
_DECLARATION_START_RE = re.compile(
    r"\b[A-Za-z_]\w*(?:[ \t]*" + _TEMPLATE + r")?(?:[ \t]*\[[^\]\n]*\])?"
    r"[ \t]+[A-Za-z_]\w*[ \t]*(?=[=,\[])"
)
_NEXT_DECLARATOR_RE = re.compile(r"\s*(?P<name>[A-Za-z_]\w*)[ \t]*(?=[=;,)\[:])")

_STATIC_CALL_RE = re.compile(
    r"(?<![\w.])(?P<name>[A-Z]\w*)\s*\.\s*(?P<method>[A-Za-z_]\w*)\s*\("
)
_NEW_RE = re.compile(r"\bnew\s+(?P<name>[A-Za-z_]\w*)(?P<args>\s*<[^;{}()]*?>)?")
_DECL_RE = re.compile(
    r"^\s*(?:(?:ref|autoptr|const|static|private|protected|owned|notnull)\s+)*"
    r"(?P<name>[A-Za-z_]\w*)(?P<args>\s*<[^;{}()]*?>)?(?:\s*\[[^\]]*\])?"
    r"\s+[A-Za-z_]\w*\s*(?==|;|,|\[)"
)
_IDENT_RE = re.compile(r"[A-Za-z_]\w*")

_PP_OPEN_RE = re.compile(r"^\s*#\s*(?P<kind>ifdef|ifndef)\s+(?P<macro>\w+)")
_PP_OPEN_UNSUPPORTED_RE = re.compile(r"^\s*#\s*if\b")
_PP_ELIF_RE = re.compile(r"^\s*#\s*elif\b")
_PP_ELSE_RE = re.compile(r"^\s*#\s*else\b")
_PP_ENDIF_RE = re.compile(r"^\s*#\s*endif\b")

_MODULE_RE = re.compile(r"(?:^|[\\/])scripts[\\/](?P<module>[0-9]_[A-Za-z]+)[\\/]", re.I)

_REQUIRED_ADDONS_RE = re.compile(
    r"requiredAddons\s*\[\s*\]\s*=\s*\{(?P<body>[^}]*)\}", re.S
)
_DEFINES_RE = re.compile(r"\bdefines\s*\[\s*\]\s*=\s*\{(?P<body>[^}]*)\}", re.S)
_QUOTED_RE = re.compile(r'"(?P<value>[^"\n]*)"')
_CFGPATCHES_RE = re.compile(r"\bclass\s+CfgPatches\b")
_CLASS_NAME_RE = re.compile(r"\bclass\s+(?P<name>\w+)")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")

# A class every DayZ scripts tree declares (1_core/proto/enscript.c:117 in
# 1.29.0.163451 and 1.30.164014): a "vanilla tree" without it is an empty or
# wrong folder, and judging against it would call every vanilla type undefined.
VANILLA_ANCHOR_CLASS = "Managed"

ES_UNDEFINED_CLASS_REF_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '{name}' is used as a type ({form}) but no "
    "class, enum or typedef named '{name}' is declared in the addon, in the "
    "vanilla scripts tree or in any --external-scripts root. A script module "
    "that names an unknown type does not compile, so {module} fails to load. "
    "Restore the declaration or update the reference; if the type comes from a "
    "dependency mod, list it in config.cpp requiredAddons[] and pass its root "
    "(the folder with its config.cpp) with --external-scripts."
)


class Definitions:
    """Type names, template parameters, macros and class-like variable names."""

    def __init__(self):
        self.types = set()
        self.template_params = set()
        self.macros = set()
        self.variables = set()
        self.classes = set()

    def add_source(self, text, tested_macros_are_known=False, variables=True):
        for match in _CLASS_DEF_RE.finditer(text):
            self.types.add(match.group("name"))
            self.classes.add(match.group("name"))
            params = match.group("params")
            if params:
                for param in _TEMPLATE_PARAM_RE.finditer(params):
                    self.template_params.add(param.group("name"))
        for match in _ENUM_DEF_RE.finditer(text):
            self.types.add(match.group("name"))
        for match in _TYPEDEF_RE.finditer(text):
            body = match.group("body").split("//", 1)[0]
            last = _LAST_IDENT_RE.search(body)
            if last:
                self.types.add(last.group("name"))
        for match in _MACRO_DEFINE_RE.finditer(text):
            self.macros.add(match.group("name"))
        if tested_macros_are_known:
            for match in _MACRO_TEST_RE.finditer(text):
                self.macros.add(match.group("name"))
        if variables:
            self.variables |= declared_variables(text)

    def merge(self, other):
        self.types |= other.types
        self.template_params |= other.template_params
        self.macros |= other.macros
        self.variables |= other.variables
        self.classes |= other.classes

    def is_type(self, name):
        return name in self.types or name in self.template_params


def _template_end(text, index, spaced=False):
    """Index of the `>` that closes template arguments opened at `index`.

    Only a `<` right after a name, followed by nothing but names, spaces,
    commas and nested `<...>` up to its match, is a template
    (`Param3<int, X, int>`, `map<string, array<int>>`). Anything else, such
    as `a<b, C = false` or `a<=b`, is a comparison: None. With `spaced`,
    spaces and tabs may stand between the name and the `<`.
    """
    name_end = index
    if spaced:
        while name_end > 0 and text[name_end - 1] in " \t":
            name_end -= 1
    if name_end == 0 or not (
        text[name_end - 1].isalnum() or text[name_end - 1] == "_"
    ):
        return None
    depth = 0
    for position in range(index, len(text)):
        char = text[position]
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
            if depth == 0:
                return position
        elif not (char.isalnum() or char in "_, \t\r\n"):
            return None
    return None


# The first character _template_end rejects after a `<`, and the brackets it
# counts there.
_TEMPLATE_STOP_RE = re.compile(r"[^\w, \t\r\n<>]")
_TEMPLATE_BREAK_RE = re.compile(r"[;{}()\n]")
_ANGLE_BRACKET_RE = re.compile(r"[<>]")


def _closed_template_openers(stripped):
    """Offsets of the `<` that _template_end can close, found in one pass.

    Past its name check, _template_end returns the first `>` at which the
    depth counted from its `<` falls back to 0, and None at the first
    character it rejects or at the end of the file; within a run of the
    characters it accepts, that `>` is the one that pops the `<` from a
    stack, so a `<` the stack never pops gets None (a word character of a
    str pattern is one for which str.isalnum() holds, or `_`, the same test
    _template_end makes). Without this pass a `<` that opened no template
    was read up to the end of its statement, and a chain of shifts with no
    comma grew with the square of its length (Codex review of #115, N1).
    """
    closed = set()
    index = stripped.find("<")
    while index != -1:
        stop = _TEMPLATE_STOP_RE.search(stripped, index)
        end = stop.start() if stop else len(stripped)
        stack = []
        for match in _ANGLE_BRACKET_RE.finditer(stripped, index, end):
            if match.group() == "<":
                stack.append(match.start())
            elif stack:
                closed.add(stack.pop())
        index = stripped.find("<", end)
    return closed


def _template_spans(stripped, spaced=False):
    """(`<`, `>`) offsets of the template arguments of a file, in order.

    A comma between template arguments (`Param3<bool, vector, int>`,
    `typedef map<string, ref array<string>> Name;`) is not a declarator
    separator; vanilla control 2026-10-13 found 104 (1.29) and 109 (1.30)
    such false findings of ES-VARIABLE-NAMED-AS-TYPE before this check. A
    `<` opens template arguments only as _template_end reads them, so the
    comparison in `bool first = a < b, Debug = false;` hides no declarator.
    With `spaced`, spaces are allowed before it: `new Param3 <int, Object,
    int>(...)` (second Codex review of #113, J1).

    Template arguments never hold a `;`, `{` or `}`, so one pass over the
    file finds the ones a pass from the start of each statement finds.
    Reading from the start of the statement at each comma grew with the
    square of the names of one declaration (Codex review of #114, M2).
    """
    closed = _closed_template_openers(stripped)
    spans = []
    index = stripped.find("<")
    while index != -1:
        if index in closed:
            end = _template_end(stripped, index, spaced=spaced)
            if end is not None:
                spans.append((index, end))
                index = end
        index = stripped.find("<", index + 1)
    return spans


def _inside_template_args(spans, offset):
    """True when offset sits inside one of the template arguments in spans."""
    position = bisect.bisect_left(spans, (offset,)) - 1
    return position >= 0 and offset < spans[position][1]


_DECLARATOR_EVENT_RE = re.compile(r"[()\[\]{};,<]")


def declarator_commas(text, starts, spans=()):
    """Offsets of the commas before the later declarators of declarations.

    starts: offsets, in order, from which a declaration's later declarators
    are read: just past its first one. The declaration then runs to the `;`
    that ends its statement or to the bracket that closes around it, and a
    later declarator follows each of its commas outside every bracket.
    spans: (`<`, `>`) offsets of template arguments, in order, read as one
    token: their commas separate types, and a start inside them is none.

    One pass reads them all, keeping for each open bracket whether a
    declaration runs at its level. Reading each declaration from its own
    start read a statement once for each start it held: time quadratic in
    the length of `void F(int a0, int a1, ...)`, or of template arguments
    that a newline keeps from being blanked (Codex review of e6d6, E5).
    """
    ends = dict(spans)
    running = [False]
    commas = []
    next_start = 0
    index = 0
    while True:
        event = _DECLARATOR_EVENT_RE.search(text, index)
        at = event.start() if event else len(text)
        while next_start < len(starts) and starts[next_start] <= at:
            # A start a template span stepped over begins nothing.
            if starts[next_start] >= index:
                running[-1] = True
            next_start += 1
        if event is None:
            return commas
        char = event.group()
        index = at + 1
        if char == "<":
            if at in ends:
                index = ends[at]
        elif char in "([{":
            running.append(False)
        elif char in ")]}":
            if len(running) > 1:
                running.pop()
            else:
                running[0] = False
        elif char == ";":
            running[-1] = False
        elif running[-1]:
            commas.append(at)


def blank_template_arguments(text):
    """text with spaces inside each outermost `<...>`, at the same offsets.

    A `<...>` is a `<` closed by its own `>` with no `;`, `{`, `}`, `(`, `)`
    or newline between them, nested to any depth: what _TEMPLATE read, up to
    four deep, before it read blanked text (Codex review of e6d6, E1). No
    declaration is left to find among template arguments either: each `ref
    X,` of `new Param<ref X, ref X, ...>(1)` read like another declaration,
    and each was read to the end of the statement (E2). Each run of text
    between two of those breaks is read once, and only where it holds a `<`.
    """
    spans = []
    index = text.find("<")
    while index != -1:
        stop = _TEMPLATE_BREAK_RE.search(text, index)
        end = stop.start() if stop else len(text)
        openers = []
        for match in _ANGLE_BRACKET_RE.finditer(text, index, end):
            if match.group() == "<":
                openers.append(match.start())
            elif openers:
                opener = openers.pop()
                # The spans it closes over are blanked with it.
                while spans and spans[-1][0] > opener:
                    spans.pop()
                spans.append((opener, match.start()))
        index = text.find("<", end)
    if not spans:
        return text
    parts = []
    last = 0
    for opener, closer in spans:
        parts.append(text[last:opener + 1])
        parts.append(" " * (closer - opener - 1))
        last = closer
    parts.append(text[last:])
    return "".join(parts)


def declared_variables(text):
    # The patterns read the blanked text, the declarators the text itself:
    # template arguments are told from comparisons there by _template_end,
    # over lines too and after spaces or tabs (`new map <`), and no name is
    # declared among them (Codex review of e6d6, E5 and E8). The commas of
    # template arguments (`new Param3<int, X, int>(...)`) separate types, not
    # declarators.
    blanked = blank_template_arguments(text)
    spans = _template_spans(text, spaced=True)
    names = {
        match.group("name")
        for match in _DECLARED_NAME_RE.finditer(blanked)
        if not _inside_template_args(spans, match.start("name"))
    }
    starts = [match.end() for match in _DECLARATION_START_RE.finditer(blanked)]
    for comma in declarator_commas(text, starts, spans):
        declarator = _NEXT_DECLARATOR_RE.match(text, comma + 1)
        if declarator and _CLASS_LIKE_RE.match(declarator.group("name")):
            names.add(declarator.group("name"))
    return names


def _vanilla_texts(vanilla_root):
    for path in sorted(pathlib.Path(vanilla_root).rglob("*.c")):
        try:
            yield path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue


@functools.lru_cache(maxsize=4)
def vanilla_definitions(vanilla_root):
    """Types and macros of the vanilla tree, read once per process and root.

    Raw text, not stripped: a class named in a comment only makes the rule
    more lenient, and stripping 12 MB is a cost the quick-check hook would pay
    on every edit. Variable names are left to vanilla_variables().
    """
    definitions = Definitions()
    for text in _vanilla_texts(vanilla_root):
        definitions.add_source(text, tested_macros_are_known=True, variables=False)
    return definitions


@functools.lru_cache(maxsize=4)
def vanilla_variables(vanilla_root):
    """Class-like variable names declared in vanilla.

    Measured 2026-09-19: half of the vanilla scan (0.62 of ~1.3 s). Only an
    unresolved static-call receiver needs it, which is rare, so it is lazy.
    """
    names = set()
    for text in _vanilla_texts(vanilla_root):
        names |= declared_variables(text)
    return names


def _module_label(rel_path):
    match = _MODULE_RE.search(str(rel_path).replace("\\", "/"))
    if match:
        return "the %s script module" % match.group("module")
    return "the script module containing this file"


def _strip_config_comments(text):
    return _LINE_COMMENT_RE.sub("", _BLOCK_COMMENT_RE.sub("", text))


def _config_array_values(config_sources, array_re):
    values = set()
    for _rel_path, text in config_sources:
        for block in array_re.finditer(_strip_config_comments(text)):
            for item in _QUOTED_RE.finditer(block.group("body")):
                value = item.group("value").strip()
                if value:
                    values.add(value)
    return values


def required_addons(config_sources):
    """Every requiredAddons[] entry across the given raw config.cpp texts."""
    return _config_array_values(config_sources, _REQUIRED_ADDONS_RE)


def unquoted_required_addons(config_sources):
    """Tokens of requiredAddons[] that are not string literals (macros...).

    Their value is unknown, so the dependency they name is unknown too.
    """
    tokens = set()
    for _rel_path, text in config_sources:
        for block in _REQUIRED_ADDONS_RE.finditer(_strip_config_comments(text)):
            rest = _QUOTED_RE.sub(" ", block.group("body"))
            tokens |= {piece.strip() for piece in rest.split(",") if piece.strip()}
    return tokens


def dependency_closure(addon_configs, external_configs):
    """(required, unquoted) over the addon and every scanned dependency.

    A config.cpp under an --external-scripts root contributes its own
    requiredAddons[] once one of its CfgPatches classes is required: the type
    can live in a dependency of a dependency. `unquoted` holds the
    requiredAddons[] tokens that are not string literals along the way.
    """
    required = set(required_addons(addon_configs))
    unquoted = set(unquoted_required_addons(addon_configs))
    providers = [
        (
            declared_patches([config]),
            required_addons([config]),
            unquoted_required_addons([config]),
        )
        for config in external_configs or []
    ]
    pending = list(required)
    while pending:
        dependency = pending.pop()
        for patches, needs, tokens in providers:
            if dependency in patches:
                unquoted |= tokens
                for need in needs - required:
                    required.add(need)
                    pending.append(need)
    return required, unquoted


def config_defines(config_sources):
    """Every CfgMods defines[] entry: macros a loaded mod turns on."""
    return _config_array_values(config_sources, _DEFINES_RE)


def _guaranteed_lines(text):
    """Per line of a config or script text: True when the preprocessor keeps it.

    A line is kept for certain outside every block, and inside `#ifdef X` (or
    the `#else` of `#ifndef X`) when this same file #defines X, at a line
    kept for certain, before it. Any other condition depends on something
    outside the file.
    """
    local = set()
    stack = []
    guaranteed = []
    for line in text.split("\n"):
        kept = all(
            macro is not None and macro in local and when_defined
            for macro, when_defined in stack
        )
        guaranteed.append(kept)
        opened = _PP_OPEN_RE.match(line)
        if opened:
            stack.append((opened.group("macro"), opened.group("kind") == "ifdef"))
        elif _PP_OPEN_UNSUPPORTED_RE.match(line):
            stack.append((None, True))
        elif _PP_ELIF_RE.match(line):
            if stack:
                stack[-1] = (None, True)
        elif _PP_ELSE_RE.match(line):
            if stack:
                macro, when_defined = stack[-1]
                stack[-1] = (macro, not when_defined)
        elif _PP_ENDIF_RE.match(line):
            if stack:
                stack.pop()
        elif kept:
            defined = _MACRO_DEFINE_RE.match(line)
            if defined:
                local.add(defined.group("name"))
    return guaranteed


def unconditional_config_defines(config_sources):
    """defines[] entries the preprocessor keeps whatever else is defined.

    Only those are on whenever the mod is loaded: an entry under a condition
    that depends on something outside the config.cpp stays a two-way flag.
    Each entry is judged on its own line, so a `#ifdef` inside the array
    counts too.
    """
    values = set()
    for _rel_path, text in config_sources:
        text = _strip_config_comments(text)
        guaranteed = _guaranteed_lines(text)
        for block in _DEFINES_RE.finditer(text):
            body_start = block.start("body")
            for item in _QUOTED_RE.finditer(block.group("body")):
                line = text.count("\n", 0, body_start + item.start())
                value = item.group("value").strip()
                if value and guaranteed[line]:
                    values.add(value)
    return values


def declared_patches(config_sources):
    """Class names directly inside every `class CfgPatches { ... }` block."""
    patches = set()
    for _rel_path, text in config_sources:
        text = _strip_config_comments(text)
        for start in _CFGPATCHES_RE.finditer(text):
            open_brace = text.find("{", start.end())
            if open_brace < 0:
                continue
            depth = 1
            index = open_brace + 1
            while index < len(text) and depth > 0:
                char = text[index]
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                elif depth == 1 and char == "c":
                    match = _CLASS_NAME_RE.match(text, index)
                    if match and (index == 0 or not text[index - 1].isalnum()):
                        patches.add(match.group("name"))
                        index = match.end()
                        continue
                index += 1
    return patches


def _gated(stack, known_macros, always_on):
    """True when the current line may not compile in a build the rule knows.

    Each entry is (macro, branch_when_defined): `#ifdef X` opens (X, True),
    `#ifndef X` opens (X, False) and `#else` flips it. A macro that is always
    on (see unconditional_defines) never compiles its False branch; a build
    flag vanilla tests compiles in both directions.
    """
    for macro, when_defined in stack:
        if macro is None or macro not in known_macros:
            return True
        if macro in always_on and not when_defined:
            return True
    return False


def _update_pp_stack(stack, line):
    """True when `line` is a preprocessor directive (and has been applied)."""
    opened = _PP_OPEN_RE.match(line)
    if opened:
        stack.append((opened.group("macro"), opened.group("kind") == "ifdef"))
        return True
    if _PP_OPEN_UNSUPPORTED_RE.match(line):
        stack.append((None, True))
        return True
    if _PP_ELIF_RE.match(line):
        if stack:
            stack[-1] = (None, True)
        return True
    if _PP_ELSE_RE.match(line):
        if stack:
            macro, when_defined = stack[-1]
            stack[-1] = (macro, not when_defined)
        return True
    if _PP_ENDIF_RE.match(line):
        if stack:
            stack.pop()
        return True
    return line.lstrip().startswith("#")


def _template_args(args):
    if not args:
        return []
    return [
        name for name in _IDENT_RE.findall(args) if _CLASS_LIKE_RE.match(name)
    ]


def unconditional_defines(stripped):
    """Macros `#define`d on a line the preprocessor always keeps.

    Only those are always on: outside every block, or under conditions this
    same file guarantees (_guaranteed_lines). A #define under any other
    condition depends on it (vanilla's 1_core/defines.c lists its build flags
    under `#ifdef DOXYGEN`), so its macro stays a two-way build flag.
    """
    names = set()
    lines = stripped.split("\n")
    for line, kept in zip(lines, _guaranteed_lines(stripped)):
        if kept:
            match = _MACRO_DEFINE_RE.match(line)
            if match:
                names.add(match.group("name"))
    return names


def find_type_references(stripped, known_macros, always_on=frozenset()):
    """Yield (line, name, form) for every class-like name used as a type."""
    stack = []
    for line_number, line in enumerate(stripped.split("\n"), start=1):
        if _update_pp_stack(stack, line):
            continue
        if _gated(stack, known_macros, always_on):
            continue
        seen = set()

        def emit(name, form):
            if name not in seen and _CLASS_LIKE_RE.match(name):
                seen.add(name)
                return [(line_number, name, form)]
            return []

        for match in _STATIC_CALL_RE.finditer(line):
            name = match.group("name")
            if match.group("method") == "Cast":
                form = "%s.Cast" % name
            else:
                form = "static call %s.%s" % (name, match.group("method"))
            yield from emit(name, form)
        for match in _NEW_RE.finditer(line):
            yield from emit(match.group("name"), "new %s" % match.group("name"))
            for arg in _template_args(match.group("args")):
                yield from emit(arg, "template argument of new")
        decl = _DECL_RE.match(line)
        if decl:
            yield from emit(decl.group("name"), "typed declaration")
            for arg in _template_args(decl.group("args")):
                yield from emit(arg, "template argument of a declaration")


def check_es_undefined_class_ref(
    addon_sources,
    addon_configs,
    external_sources,
    external_configs,
    vanilla_root,
    vanilla_skip_reason=None,
    addon_is_vanilla=False,
):
    """Return (errors, skipped).

    addon_sources / external_sources: lists of (rel_path, stripped_source).
    addon_configs / external_configs: lists of (rel_path, raw config.cpp text).
    `addon_is_vanilla`: the addon IS the vanilla tree (the vanilla control). It
    has no mod dependencies, so its empty requiredAddons[] is not "unknown".
    `skipped` lists what the rule could not judge, for the report's info block;
    it never changes the status.
    """
    if not addon_sources:
        return [], []
    if vanilla_root is None:
        return [], [
            {
                "rule_id": ES_UNDEFINED_CLASS_REF_RULE_ID,
                "status": "SKIP",
                "reason": (
                    "%s. Without the vanilla tree every vanilla type would look "
                    "undefined, so the rule does not run."
                    % (vanilla_skip_reason or "vanilla tree not available")
                ),
            }
        ]

    vanilla_key = str(pathlib.Path(vanilla_root).resolve())
    if VANILLA_ANCHOR_CLASS not in vanilla_definitions(vanilla_key).classes:
        return [], [
            {
                "rule_id": ES_UNDEFINED_CLASS_REF_RULE_ID,
                "status": "SKIP",
                "reason": (
                    "the vanilla tree %s declares no class %s, so it is not a "
                    "DayZ scripts tree; judging against it would call every "
                    "vanilla type undefined, so the rule does not run."
                    % (vanilla_root, VANILLA_ANCHOR_CLASS)
                ),
            }
        ]
    definitions = Definitions()
    definitions.merge(vanilla_definitions(vanilla_key))
    always_on = set()
    for _rel_path, stripped in list(addon_sources) + list(external_sources or []):
        definitions.add_source(stripped)
        always_on |= unconditional_defines(stripped)
    all_configs = list(addon_configs) + list(external_configs or [])
    definitions.macros |= config_defines(all_configs)
    always_on |= unconditional_config_defines(all_configs)

    unresolved = []
    for rel_path, stripped in addon_sources:
        for line, name, form in find_type_references(
            stripped, definitions.macros, always_on
        ):
            if definitions.is_type(name):
                continue
            if form.startswith("static call") and (
                name in definitions.variables
                or name in vanilla_variables(vanilla_key)
            ):
                continue
            unresolved.append((rel_path, line, name, form))
    if not unresolved:
        return [], []

    names = sorted({name for _f, _l, name, _form in unresolved})
    shown = "%d type name(s) resolve nowhere (%s)" % (
        len(names), ", ".join(names[:10]) + (", ..." if len(names) > 10 else "")
    )
    direct = required_addons(addon_configs) | unquoted_required_addons(addon_configs)
    required, unquoted = dependency_closure(addon_configs, external_configs)
    provided = declared_patches(all_configs)
    uncovered = sorted(
        dependency
        for dependency in required
        if dependency not in VANILLA_PATCHES and dependency not in provided
    ) + sorted("%s (not a string literal)" % token for token in unquoted)
    reason = None
    if uncovered:
        reason = (
            "config.cpp requires %s, and no scanned root declares %s in "
            "CfgPatches. %s and may come from there; pass the root of each "
            "dependency (the folder with its config.cpp) with --external-scripts "
            "to judge them."
            % (", ".join(uncovered), "it" if len(uncovered) == 1 else "them", shown)
        )
    elif not direct and not addon_is_vanilla:
        # Observed on 2026-09-19 across 161 addon roots under P:\: three mods
        # (six trees) with `requiredAddons[]={};` use CF, Expansion or LBmaster
        # classes outside any #ifdef. They can only compile next to those mods,
        # and the empty list does not say which. Empty is "not declared", not
        # "vanilla only" (vanilla's own scripts/config.cpp is empty too, hence
        # the addon_is_vanilla exception).
        reason = (
            "no config.cpp in the tree lists any requiredAddons[] entry, so the "
            "addon's dependencies are unknown. %s; declare the dependencies in "
            "requiredAddons[] and pass their roots with --external-scripts to "
            "judge them." % shown
        )
    if reason:
        return [], [
            {
                "rule_id": ES_UNDEFINED_CLASS_REF_RULE_ID,
                "status": "SKIP",
                "reason": reason,
                "unresolved": [
                    {"name": name, "file": rel_path, "line": line}
                    for rel_path, line, name, _form in unresolved
                ],
            }
        ]

    errors = []
    for rel_path, line, name, form in unresolved:
        errors.append(
            {
                "check": ES_UNDEFINED_CLASS_REF_RULE_ID,
                "file": rel_path,
                "line": line,
                "message": ES_UNDEFINED_CLASS_REF_MESSAGE.format(
                    rel_path=rel_path, line=line, name=name, form=form,
                    module=_module_label(rel_path),
                ),
                "severity": "FAIL",
                "rule_id": ES_UNDEFINED_CLASS_REF_RULE_ID,
            }
        )
    return errors, []
