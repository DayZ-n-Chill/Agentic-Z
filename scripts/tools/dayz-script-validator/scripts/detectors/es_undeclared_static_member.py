import re

from detectors.es_cast_unrelated_types import _CLASS_RE
from detectors.es_undefined_class_ref import declared_variables
from detectors.es_variable_named_as_type import usable_vanilla_key, vanilla_sources
from shared.dead_branches import dead_lines


ES_UNDECLARED_STATIC_MEMBER_RULE_ID = "ES-UNDECLARED-STATIC-MEMBER"


# claim: CLAIM-ENFORCE-UNDECLARED-STATIC-MEMBER
# `ClassName.Member` naming a member that the class no longer declares stops
# the whole script module from compiling. Pipeline inbox
# fb-20261006-002741-28fa (LFSkateboard): a lane deleted the static consts
# ANIM_SWAP_ENABLED and its siblings from its own class LFSK_Constants while
# seven call sites still read `LFSK_Constants.ANIM_SWAP_ENABLED`, and DayZ
# refused the World module on the first boot. The ticket gives the refusal of
# the module, not the compiler's line for the missing member.
#
# The lookup is complete only for a class the addon owns end to end, so the
# rule judges `ClassName.Member` (and `ClassName.Member(`) only when:
#   - ClassName is a class declared in the addon, not modded and not a
#     template, and not declared at all (modded or not) in the vanilla tree
#     or an --external-scripts root (an enum or a typedef has no class
#     declaration, so it is never judged);
#   - every ancestor is such a class too, through non-modded declarations
#     that agree on one parent; a class without a parent ends the chain (its
#     parent is Class, the implicit root);
#   - neither the class nor an ancestor, across every addon declaration of it
#     (`modded class` included, under any #ifdef), names Member at the top
#     level of its body: a field, a const, a method or anything else;
#   - Member is not a method of Class, which every class inherits (`Cast`,
#     `CastTo`, `StaticType`...; the vanilla tree's `class Class` adds its
#     own names when it is passed);
#   - ClassName is not also declared as a variable anywhere in the addon.
# `Name.M(` is judged too: a call to a method nobody declares is the
# `Undefined function` compile failure of ES-NONEXISTENT-METHOD; on an
# addon-owned class it was not measured on its own. Without a vanilla tree a
# class whose chain reaches a vanilla class is still skipped, because the
# chain does not resolve in the addon. Lines that never compile
# (shared/dead_branches.py) are not judged.

_REFERENCE_RE = re.compile(
    r"(?<![\w.])(?P<cls>[A-Z]\w*)\s*\.\s*(?P<member>[A-Za-z_]\w*)(?P<call>\s*\()?"
)
_IDENT_RE = re.compile(r"[A-Za-z_]\w*")

# Methods of Class, the implicit root: the ten that `class Class` declares at
# 1_core/proto/enscript.c:10-114, the same lines in 1.29.0.163451 and
# 1.30.164078 (read 2026-10-17); it declares no field. A vanilla tree, when
# passed, adds the names of its own `class Class`.
CLASS_ROOT_MEMBERS = frozenset({
    "IsInherited", "ClassName", "GetDebugName", "Type", "StaticType",
    "StaticGetType", "ToString", "Cast", "CastTo", "SafeCastType",
})

ES_UNDECLARED_STATIC_MEMBER_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '{cls}.{member}{call}': no declaration of "
    "'{cls}' in the addon ({where}), nor any of its ancestors ({chain}), names "
    "'{member}', and the class is the addon's own, so nothing outside the "
    "addon can add it. A script module that reads a member its class does not "
    "declare does not compile. Restore the declaration or update the "
    "reference."
)


def class_bodies(stripped):
    """Yield (match, body) for every class of the text with a body.

    `body` is the (start, end) offsets of the class's braces, or None when
    the header is not followed by `{` or the braces never close: that class
    cannot be read. A forward `class X;` is not yielded.
    """
    for match in _CLASS_RE.finditer(stripped):
        if match.group("after"):
            continue
        brace = stripped.find("{", match.end())
        if brace < 0 or stripped[match.end():brace].strip(" \t\r\n"):
            yield match, None
            continue
        depth = 0
        for index in range(brace, len(stripped)):
            char = stripped[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    yield match, (brace, index)
                    break
        else:
            yield match, None


def top_level_names(body):
    """Identifiers at the top level of a class body.

    Method bodies and parameter lists are dropped: what is left are the
    declarations of the class (types and modifiers too, which only makes the
    lookup more lenient).
    """
    kept = []
    depth = 0
    for char in body:
        if char in "{(":
            depth += 1
        elif char in "})":
            depth -= 1
        elif depth == 0:
            kept.append(char)
    return set(_IDENT_RE.findall("".join(kept)))


class AddonClasses:
    """Classes the addon owns end to end, with every name their bodies hold."""

    def __init__(self, addon_sources, external_sources, vanilla_root):
        self.declarations = {}
        self.outside = set()
        self.root_members = set(CLASS_ROOT_MEMBERS)
        for rel_path, stripped in addon_sources:
            for match, span in class_bodies(stripped):
                start, end = span or (None, None)
                self.declarations.setdefault(match.group("name"), []).append(
                    {
                        "modded": "modded" in match.group("mods").split(),
                        "parent": match.group("parent"),
                        "templated": bool(match.group("params")),
                        "names": (
                            None if span is None
                            else top_level_names(stripped[start + 1:end])
                        ),
                        "file": rel_path,
                        "start": start,
                        "end": end,
                    }
                )
        for _rel_path, stripped in external_sources or []:
            self._add_outside(stripped)
        vanilla_key = usable_vanilla_key(vanilla_root)
        if vanilla_key is not None:
            for _rel_path, text in vanilla_sources(vanilla_key):
                self._add_outside(text)
                for match, span in class_bodies(text):
                    if match.group("name") == "Class" and span is not None:
                        self.root_members |= top_level_names(
                            text[span[0] + 1:span[1]]
                        )
        self._chains = {}

    def _add_outside(self, text):
        for match in _CLASS_RE.finditer(text):
            self.outside.add(match.group("name"))

    def chain(self, name):
        """[name, parent, ...] when every class of it is the addon's own."""
        if name not in self._chains:
            self._chains[name] = self._resolve(name)
        return self._chains[name]

    def _resolve(self, name):
        chain = []
        while name is not None:
            entries = self.declarations.get(name)
            if (
                not entries
                or name in chain
                or name in self.outside
                or any(
                    entry["templated"] or entry["names"] is None
                    for entry in entries
                )
            ):
                return None
            parents = {e["parent"] for e in entries if not e["modded"]}
            if len(parents) != 1:
                return None
            chain.append(name)
            name = parents.pop()
        return chain

    def names(self, chain):
        names = set(self.root_members)
        for cls in chain:
            for entry in self.declarations[cls]:
                names |= entry["names"]
        return names


def check_es_undeclared_static_member(
    addon_sources, external_sources, vanilla_root
):
    """addon_sources / external_sources: lists of (rel_path, stripped_source)."""
    classes = AddonClasses(addon_sources, external_sources, vanilla_root)
    variables = set()
    for _rel_path, stripped in addon_sources:
        # `class X : Y` reads as a declared name X followed by `:` to
        # declared_variables(); a class header declares no variable.
        variables |= declared_variables(
            _CLASS_RE.sub(lambda m: " " * len(m.group(0)), stripped)
        )

    errors = []
    for rel_path, stripped in addon_sources:
        dead = None
        for match in _REFERENCE_RE.finditer(stripped):
            cls, member = match.group("cls"), match.group("member")
            if cls in variables:
                continue
            chain = classes.chain(cls)
            if chain is None or member in classes.names(chain):
                continue
            line = stripped.count("\n", 0, match.start()) + 1
            if dead is None:
                dead = dead_lines(stripped)
            if line in dead:
                continue
            where = ", ".join(
                sorted({entry["file"] for entry in classes.declarations[cls]})
            )
            errors.append(
                {
                    "check": ES_UNDECLARED_STATIC_MEMBER_RULE_ID,
                    "file": rel_path,
                    "line": line,
                    "message": ES_UNDECLARED_STATIC_MEMBER_MESSAGE.format(
                        rel_path=rel_path, line=line, cls=cls,
                        member=member, call="(" if match.group("call") else "",
                        where=where,
                        chain=" > ".join(chain[1:] + ["Class"]),
                    ),
                    "severity": "FAIL",
                    "rule_id": ES_UNDECLARED_STATIC_MEMBER_RULE_ID,
                }
            )
    return errors
