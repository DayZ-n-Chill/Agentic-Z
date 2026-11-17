import re

from detectors.es_cast_unrelated_types import (
    UNREAD_PARENT,
    _CLASS_RE,
    FileScopes,
    _argument_type,
    class_parent,
)
from detectors.es_undeclared_static_member import AddonClasses


ES_PROTECTED_METHOD_CROSS_CLASS_RULE_ID = "ES-PROTECTED-METHOD-CROSS-CLASS"


# claim: CLAIM-ENFORCE-PROTECTED-METHOD-CROSS-CLASS
# WARN, not FAIL: the refusal is measured for fields only. Enforce
# `protected` reaches only the declaring class and its descendants, and a
# protected FIELD read from an unrelated class stops the module
# (`Variable 'm_DeviceId' is protected`, enforce-script-reference SKILL.md,
# "Moving a body between modules", and ES-PROTECTED-CROSS-MODULE). No
# compile log in this pack shows the same for a METHOD. Pipeline inbox
# fb-20261006-002741-28fa (LFSkateboard) has the shape: `protected void
# LFSK_OnServerState(...)` declared in LFSK_RideCommand, and
# `PlayerBase.OnRPC` (same module, 4_World, unrelated class) calling
# `cmd.LFSK_OnServerState(...)` on a local `LFSK_RideCommand cmd`; the
# ticket does not isolate a compile line for that call.
#
# Judged only when everything is known:
#   - the receiver is a plain name with one plain declared type, as a local
#     still open at the call or a parameter of the same function, or else as
#     a member of the enclosing class itself (the lookup of
#     ES-CAST-UNRELATED-TYPES), so `this` and `super`, never declared, are
#     not judged;
#   - walking up from that type, every class up to the one that declares the
#     method is declared in the addon (not modded and not a template there,
#     its body readable) and nowhere else, modded or not; the first class
#     that declares the method decides, and it declares it `protected` or
#     `private` in every addon declaration that names it;
#   - the calling class is neither that class nor derived from it. A call
#     outside any class counts as unrelated. The caller's parents are read
#     from the non-modded declarations of the addon and the external roots;
#     a class declared in neither (vanilla) cannot derive from an addon
#     class, which is what makes the ticket's `modded class PlayerBase`
#     unrelated. Two parents for one class, a cycle, or a header that a
#     directive splits (its parent is not read) in the caller or an
#     ancestor, skip the call.
# Lines that never compile (shared/dead_branches.py) are not judged.

_CALL_RE = re.compile(
    r"(?<![\w.])(?P<recv>[A-Za-z_]\w*)\s*\.\s*(?P<method>[A-Za-z_]\w*)\s*\("
)
_IDENT_RE = re.compile(r"[A-Za-z_]\w*")
_HIDDEN = ("protected", "private")

ES_PROTECTED_METHOD_CROSS_CLASS_MESSAGE = (
    "[WARN] {rel_path} line {line}: '{recv}.{method}(': '{recv}' is declared "
    "as {recv_type}, and {method}() is {visibility} in {owner} ({owner_file}); "
    "{caller} is neither {owner} nor derived from it. Enforce refuses a "
    "protected field read from outside its hierarchy (\"Variable '...' is "
    "protected\") and the whole script module does not compile; the same "
    "refusal for a method is not measured yet. Make the method public, or "
    "call it from inside {owner}."
)


def method_visibilities(body):
    """{method name: set of visibilities} at the top level of a class body.

    A top-level statement ends at `;` or at the `}` of a method body; the
    name before its first `(` is the method, and `protected` / `private`
    before that name set the visibility (otherwise "public").
    """
    methods = {}
    head = []
    depth = 0
    in_params = False
    for char in body:
        if char == "{":
            if depth == 0:
                _record(methods, "".join(head))
                head = []
            depth += 1
        elif char == "}":
            depth -= 1
        elif depth > 0:
            continue
        elif char == ";":
            _record(methods, "".join(head))
            head = []
            in_params = False
        elif char == "(":
            if not in_params:
                head.append("(")
            in_params = True
        elif not in_params:
            head.append(char)
        elif char == ")":
            in_params = False
    return methods


def _record(methods, head):
    if "(" not in head:
        return
    before = head.split("(", 1)[0]
    if "=" in before:
        return  # a field initialised by a call: `int m_X = Compute(`
    words = _IDENT_RE.findall(before)
    if not words:
        return
    visibility = next((w for w in words[:-1] if w in _HIDDEN), "public")
    methods.setdefault(words[-1], set()).add(visibility)


class _Lookup:
    def __init__(self, addon_sources, external_sources, vanilla_root):
        self.classes = AddonClasses(addon_sources, external_sources, vanilla_root)
        texts = dict(addon_sources)
        for entries in self.classes.declarations.values():
            for entry in entries:
                entry["methods"] = (
                    {} if entry["start"] is None
                    else method_visibilities(
                        texts[entry["file"]][entry["start"] + 1:entry["end"]]
                    )
                )
        self.parents = {}
        for _rel_path, stripped in list(addon_sources) + list(external_sources or []):
            for match in _CLASS_RE.finditer(stripped):
                if match.group("after") or "modded" in match.group("mods").split():
                    continue
                self.parents.setdefault(match.group("name"), set()).add(
                    class_parent(stripped, match)
                )

    def owner(self, cls, method):
        """(owner, visibility, file) of a hidden `method` reached from cls."""
        seen = set()
        while cls is not None and cls not in seen:
            seen.add(cls)
            entries = self.classes.declarations.get(cls)
            if (
                not entries
                or cls in self.classes.outside
                or all(e["modded"] for e in entries)
                or any(e["templated"] or e["names"] is None for e in entries)
            ):
                return None
            found = set()
            files = set()
            for entry in entries:
                if method in entry["methods"]:
                    found |= entry["methods"][method]
                    files.add(entry["file"])
            if found:
                if "public" in found:
                    return None
                visibility = "private" if found == {"private"} else "protected"
                return cls, visibility, ", ".join(sorted(files))
            parents = {e["parent"] for e in entries if not e["modded"]}
            if len(parents) != 1:
                return None
            cls = parents.pop()
        return None

    def unrelated(self, caller, owner):
        """True when `caller` is known not to be `owner` nor derive from it."""
        seen = set()
        while caller is not None:
            if caller == owner or caller in seen:
                return False
            seen.add(caller)
            parents = self.parents.get(caller)
            if not parents:
                return True
            if len(parents) != 1 or UNREAD_PARENT in parents:
                return False
            caller = next(iter(parents))
        return True


def _enclosing_class(declarations, rel_path, at):
    best = None
    for name, entries in declarations.items():
        for entry in entries:
            if (
                entry["file"] == rel_path
                and entry["start"] is not None
                and entry["start"] < at < entry["end"]
                and (best is None or entry["start"] > best[1])
            ):
                best = (name, entry["start"])
    return best[0] if best else None


def check_es_protected_method_cross_class(
    addon_sources, external_sources, vanilla_root
):
    """addon_sources / external_sources: lists of (rel_path, stripped_source)."""
    lookup = None
    warnings = []
    for rel_path, stripped in addon_sources:
        scopes = None
        for match in _CALL_RE.finditer(stripped):
            recv, method = match.group("recv"), match.group("method")
            if lookup is None:
                lookup = _Lookup(addon_sources, external_sources, vanilla_root)
            if scopes is None:
                scopes = FileScopes(stripped)
            line = scopes.line(match.start())
            if line in scopes.dead:
                continue
            recv_type = _argument_type(stripped, scopes, recv, match.start())
            if not recv_type:
                continue
            found = lookup.owner(recv_type, method)
            if found is None:
                continue
            owner, visibility, owner_file = found
            caller = _enclosing_class(
                lookup.classes.declarations, rel_path, match.start()
            )
            if caller is None and scopes.class_body(match.start()) is not None:
                continue  # inside a class whose header is not read
            if not lookup.unrelated(caller, owner):
                continue
            warnings.append(
                {
                    "check": ES_PROTECTED_METHOD_CROSS_CLASS_RULE_ID,
                    "file": rel_path,
                    "line": line,
                    "message": ES_PROTECTED_METHOD_CROSS_CLASS_MESSAGE.format(
                        rel_path=rel_path, line=line, recv=recv, method=method,
                        recv_type=recv_type, visibility=visibility,
                        owner=owner, owner_file=owner_file,
                        caller=(
                            "class %s" % caller if caller
                            else "code outside any class"
                        ),
                    ),
                    "severity": "WARN",
                    "rule_id": ES_PROTECTED_METHOD_CROSS_CLASS_RULE_ID,
                }
            )
    return warnings
