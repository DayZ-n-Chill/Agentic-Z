import re


ES_PROTECTED_CROSS_MODULE_RULE_ID = "ES-PROTECTED-CROSS-MODULE"


# Enforce enforces `protected` ACROSS script modules: a class compiled into
# 5_Mission cannot read a protected member declared by a class compiled into
# 4_World, even though Mission sees World's types. Verified at runtime on
# 2026-09-17 with a disposable probe built into a PBO and booted on a dedicated
# server:
#
#   SCRIPT (E): fx_probeprotectedreader.c,13:
#               Variable 'm_FX_ProbeValue' is protected
#   SCRIPT (E): Can't compile "Mission" script module!
#
# World compiled; Mission did not. The failure is a whole-module compile abort,
# so a single missed access costs the entire mission. Offline detection is worth
# more here than for a per-file rule.
#
# The check resolves the RECEIVER'S TYPE before firing. A first version matched
# on the member name alone and produced 164 false positives on a tree that
# compiles clean: `m_SourcePort` is protected on an entity AND a public field of
# an unrelated wire-data class, so `wd.m_SourcePort` looked like a violation and
# was not. Name matching is not enough; the declared type of the receiver is
# what decides.
#
# It therefore fires only when all of these hold:
#   1. the receiver is a local or parameter whose declared type is known, and
#   2. that type declares the member `protected`/`private`, and
#   3. the declaring file compiles into a different module than the accessor,
#      and
#   4. the member is not declared at any other visibility on that same type.
# A bare `m_Field` or a `this.m_Field` never matches: both are inside the owning
# hierarchy.

_MODULE_RE = re.compile(r"(?:^|[\\/])scripts[\\/](?P<module>[0-9]_[A-Za-z]+)[\\/]")

_PROTECTED_MEMBER_RE = re.compile(
    r"^\s*(?:static\s+)?(?:protected|private)\s+"
    r"(?:(?:static|ref|autoptr|const)\s+)*"
    r"[A-Za-z_]\w*(?:\s*<[^;{}]*>)?"
    r"\s+(?P<name>m_\w+)\s*(?:;|=(?!=))",
    re.M,
)

_ANY_MEMBER_RE = re.compile(
    r"^\s*(?:(?:public|protected|private|static|ref|autoptr|const|proto|native)\s+)*"
    r"[A-Za-z_]\w*(?:\s*<[^;{}]*>)?"
    r"\s+(?P<name>m_\w+)\s*(?:;|=(?!=))",
    re.M,
)

# `receiver.m_Field` — an identifier, a dot, and a member name. `this.m_X` is
# excluded: it is always inside the owning hierarchy.
_QUALIFIED_ACCESS_RE = re.compile(
    r"\b(?P<receiver>[A-Za-z_]\w*)\s*\.\s*(?P<name>m_\w+)\b"
)


ES_PROTECTED_CROSS_MODULE_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '{name}' is declared protected in module "
    "{owner_module} ({owner_file}) and this file compiles into {module}. Enforce "
    "enforces protected across script modules: the whole {module} module fails "
    "to compile with \"Variable '{name}' is protected\". Expose a public accessor "
    "on the declaring class instead of reading the field."
)


def _module_of(rel_path):
    match = _MODULE_RE.search(str(rel_path).replace("\\", "/"))
    if not match:
        return None
    return match.group("module")


_CLASS_HEADER_RE = re.compile(
    r"^\s*(?:modded\s+)?class\s+(?P<name>\w+)"
    r"(?:\s*:\s*(?P<base_colon>\w+)|\s+extends\s+(?P<base_ext>\w+))?"
)


def _index_classes(module_files):
    """class -> (module, file, parent, protected members, public members)."""
    index = {}
    for rel_path, module, stripped in module_files:
        if module is None:
            continue
        current = None
        depth = 0
        entered = False
        for line in stripped.split("\n"):
            header = _CLASS_HEADER_RE.match(line)
            if header and current is None:
                current = header.group("name")
                base = header.group("base_colon") or header.group("base_ext")
                entered = False
                index.setdefault(
                    current,
                    {"module": module, "file": rel_path, "base": base,
                     "protected": set(), "public": set()},
                )
            if current is not None:
                prot = _PROTECTED_MEMBER_RE.match(line)
                if prot:
                    index[current]["protected"].add(prot.group("name"))
                else:
                    any_member = _ANY_MEMBER_RE.match(line)
                    if any_member:
                        index[current]["public"].add(any_member.group("name"))
            depth += line.count("{") - line.count("}")
            if depth > 0:
                # The opening brace usually sits on its OWN line (the Allman
                # style of the vanilla tree): until it is seen, depth stays at 0,
                # and closing the class there would drop all of its members.
                entered = True
            if entered and depth <= 0:
                depth = 0
                current = None
                entered = False
    return index


def _owner_of_protected(cls, member, index):
    """Walk up the addon's chain to find who declares `member` protected."""
    seen = set()
    node = cls
    while node and node not in seen:
        seen.add(node)
        entry = index.get(node)
        if entry is None:
            return None
        if member in entry["public"]:
            return None
        if member in entry["protected"]:
            return entry
        node = entry["base"]
    return None


def check_es_protected_cross_module(module_files):
    """`module_files`: list of (rel_path, module, stripped_source)."""
    index = _index_classes(module_files)

    errors = []
    for rel_path, module, stripped in module_files:
        if module is None:
            continue
        # declared types of locals and parameters inside THIS file
        var_type = {}
        for cls in index:
            for match in re.finditer(
                r"\b" + re.escape(cls) + r"\s+(?P<var>[A-Za-z_]\w*)\b", stripped
            ):
                var_type.setdefault(match.group("var"), cls)

        for line_index, line in enumerate(stripped.split("\n"), start=1):
            for match in _QUALIFIED_ACCESS_RE.finditer(line):
                receiver = match.group("receiver")
                if receiver == "this":
                    continue
                cls = var_type.get(receiver)
                if cls is None:
                    # Without a resolved type nothing is judged: matching by name
                    # produced 164 false positives on a tree that compiles.
                    continue
                name = match.group("name")
                owner = _owner_of_protected(cls, name, index)
                if owner is None:
                    continue
                owner_module, owner_file = owner["module"], owner["file"]
                if owner_module == module:
                    continue
                errors.append(
                    {
                        "check": ES_PROTECTED_CROSS_MODULE_RULE_ID,
                        "file": rel_path,
                        "line": line_index,
                        "message": ES_PROTECTED_CROSS_MODULE_MESSAGE.format(
                            rel_path=rel_path, line=line_index, name=name,
                            module=module, owner_module=owner_module,
                            owner_file=owner_file,
                        ),
                        "severity": "FAIL",
                        "rule_id": ES_PROTECTED_CROSS_MODULE_RULE_ID,
                    }
                )
    return errors
