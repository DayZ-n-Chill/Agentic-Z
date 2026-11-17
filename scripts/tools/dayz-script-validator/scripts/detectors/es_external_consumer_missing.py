import re


ES_EXTERNAL_CONSUMER_MISSING_RULE_ID = "ES-EXTERNAL-CONSUMER-MISSING"


# A script that lives OUTSIDE the addon tree -- a mission `init.c`, another
# mod -- can call methods on the addon's classes. Deleting such a method is a
# breaking change that no in-addon check sees, because every in-addon reference
# is gone by construction.
#
# Observed on 2026-09-17 in a mod:
# a refactor removed 62 facade methods from 4_World after proving that no file
# under the addon's own `scripts/` called them. The offline linter was green, the
# implementer's gates were green and an independent review was green. The server
# then refused to compile the mission:
#
#   init.c:812,1367 Undefined function 'FX_ElecGraph.GetOutgoing'
#   init.c:1128     Undefined function 'FX_ElecGraph.GetLastEdgesVisited'
#   Can't compile mission init script!
#
# Nine of the 62 had a consumer in the mission, with 69 call sites. The mission
# source even carried the comment "Verified getter: <addon path>:119" beside the
# call. A facade method reachable from mission script is published API in fact.
#
# The check needs the external roots as input: the caller passes them with
# `--external-scripts`. Nothing is hardcoded, so no machine path is versioned.
#
# It only fires when the method name IS declared somewhere in the addon but is
# not reachable from the receiver's declared class through the addon's own
# inheritance chain. That is the shape of the real failure -- the deleted method
# still existed on the subclass in 5_Mission -- and it keeps vanilla-inherited
# methods (declared nowhere in the addon) from producing noise.

_CLASS_RE = re.compile(
    r"^\s*(?P<modded>modded\s+)?class\s+(?P<name>\w+)"
    r"(?:\s*:\s*(?P<base_colon>\w+)|\s+extends\s+(?P<base_ext>\w+))?",
    re.M,
)

_METHOD_RE = re.compile(
    r"^\s+(?:(?:public|protected|private|static|override|proto|native|ref)\s+)*"
    r"[A-Za-z_]\w*(?:\s*<[^;{}()]*>)?\s+(?P<name>\w+)\s*\(",
    re.M,
)


ES_EXTERNAL_CONSUMER_MISSING_MESSAGE = (
    "[FAIL] {rel_path} line {line}: external script calls '{cls}.{method}', but "
    "'{method}' is not declared on '{cls}' nor anywhere in its addon base chain. "
    "It is declared in the addon on '{elsewhere}', which '{cls}' does not inherit "
    "from. The engine reports \"Undefined function '{cls}.{method}'\" and refuses "
    "to compile the consuming script. Keep the method on '{cls}' or update the "
    "external consumer."
)


def _class_members(addon_files):
    """Return (parent_of, members_of, modded) read from the addon's classes."""
    parent_of = {}
    members_of = {}
    modded = set()
    for _rel_path, stripped in addon_files:
        lines = stripped.split("\n")
        current = None
        depth = 0
        for line in lines:
            header = _CLASS_RE.match(line)
            if header and depth == 0:
                current = header.group("name")
                base = header.group("base_colon") or header.group("base_ext")
                if base:
                    parent_of.setdefault(current, base)
                if header.group("modded"):
                    # `modded class X` inherits from the vanilla X: the chain is
                    # NOT closed inside the addon even when no base is written.
                    modded.add(current)
                members_of.setdefault(current, set())
            if current is not None:
                method = _METHOD_RE.match(line)
                if method:
                    members_of.setdefault(current, set()).add(method.group("name"))
            depth += line.count("{") - line.count("}")
            if depth <= 0:
                depth = 0
                if header is None and current is not None and "}" in line:
                    current = None
    return parent_of, members_of, modded


def _reachable_members(cls, parent_of, members_of):
    seen = set()
    out = set()
    node = cls
    while node and node not in seen:
        seen.add(node)
        out |= members_of.get(node, set())
        node = parent_of.get(node)
    return out


def _chain_is_closed(cls, parent_of, members_of, modded):
    """True when every ancestor of `cls` is declared inside the addon.

    When the chain leaves for a vanilla base -- `FX_AtmBase : Inventory_Base`
    -- the called method may come from there, and offline there is no way to
    know. Without this cut, `GetPosition` produced 13 false positives on a tree
    that compiles clean, only because the addon overrides it in two of its own
    classes.
    """
    seen = set()
    node = cls
    while node and node not in seen:
        seen.add(node)
        if node not in members_of or node in modded:
            return False
        parent = parent_of.get(node)
        if parent is None:
            return True
        node = parent
    return False


def check_es_external_consumer_missing(addon_files, external_files):
    """addon_files / external_files: lists of (rel_path, stripped_source)."""
    if not external_files:
        return []

    parent_of, members_of, modded = _class_members(addon_files)
    if not members_of:
        return []

    declared_anywhere = {}
    for cls, names in members_of.items():
        for name in names:
            declared_anywhere.setdefault(name, set()).add(cls)

    errors = []
    for rel_path, stripped in external_files:
        # variables typed with a class of the addon, parameters included
        var_type = {}
        for cls in members_of:
            for match in re.finditer(
                r"\b" + re.escape(cls) + r"\s+(?P<var>[A-Za-z_]\w*)\b", stripped
            ):
                var_type.setdefault(match.group("var"), cls)

        for line_index, line in enumerate(stripped.split("\n"), start=1):
            for match in re.finditer(
                r"\b(?P<recv>[A-Za-z_]\w*)\s*\.\s*(?P<method>\w+)\s*\(", line
            ):
                recv = match.group("recv")
                method = match.group("method")
                cls = var_type.get(recv)
                if cls is None and recv in members_of:
                    cls = recv
                if cls is None:
                    continue
                if not _chain_is_closed(cls, parent_of, members_of, modded):
                    continue
                if method in _reachable_members(cls, parent_of, members_of):
                    continue
                owners = declared_anywhere.get(method)
                if not owners:
                    # The addon declares that name nowhere: it comes from
                    # vanilla or from another mod. It cannot be judged offline.
                    continue
                errors.append(
                    {
                        "check": ES_EXTERNAL_CONSUMER_MISSING_RULE_ID,
                        "file": rel_path,
                        "line": line_index,
                        "message": ES_EXTERNAL_CONSUMER_MISSING_MESSAGE.format(
                            rel_path=rel_path, line=line_index, cls=cls,
                            method=method, elsewhere=", ".join(sorted(owners)),
                        ),
                        "severity": "FAIL",
                        "rule_id": ES_EXTERNAL_CONSUMER_MISSING_RULE_ID,
                    }
                )
    return errors
