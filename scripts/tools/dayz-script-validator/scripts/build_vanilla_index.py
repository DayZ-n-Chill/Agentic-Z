"""Generate shared/vanilla_index.json from a DayZ scripts tree.

The index is a derived artifact of Bohemia's vanilla tree and is not
committed. Detectors consume it through shared/vanilla_reference.py.

Parser lineage: reference/api_index.py (packctl). This generator reuses its
class/method walk (comment-preserving strip, class stack, brace depth) and
extends the regexes for Enforce cases that file does not cover — see
PARSER_GAPS_VS_API_INDEX.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from stripper import strip_enforce_comments_and_strings  # noqa: E402
from shared.method_recognition import collect_method_signature  # noqa: E402
from shared.vanilla_reference import (  # noqa: E402
    INDEX_SCHEMA_VERSION,
    VANILLA_NONEXISTENT_METHODS,
)


DEFAULT_VANILLA_ROOT = Path(r"P:\scripts")
DEFAULT_OUT_PATH = SCRIPT_DIR / "shared" / "vanilla_index.json"

# Macros a PC+RELEASE retail client does not define, and that the docs
# (vanilla/staticdefinesdoc.c, vanilla/1_core/defines.c) classify as console.
# Everything else is reported, not auto-applied to platform_gated_methods.
CONSOLE_MACROS = frozenset(
    {
        "PLATFORM_CONSOLE",
        "PLATFORM_XBOX",
        "PLATFORM_PS4",
        "PLATFORM_MSSTORE",
    }
)

# Documented as never compiled (staticdefinesdoc.c). Declarations that exist
# only under this macro are not part of any game binary.
NEVER_COMPILED_MACROS = frozenset({"DOXYGEN"})

# api_index.CLASS_PATTERN allows only `(?:modded|inherited)\s+)?class`.
# Vanilla also has `sealed class` (Contact, PhysicsWorld) and proto/native
# prefixes on engine proto classes.
CLASS_HEADER_RE = re.compile(
    r"^\s*(?:(?:modded|inherited|sealed|proto|native)\s+)*"
    r"class\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s*<[^;{]*>)?"
    r"(?:\s*:\s*(?P<base_colon>\w+)|\s+extends\s+(?P<base_ext>\w+))?"
)

# api_index.METHOD_PATTERN misses `external`, `volatile`, `owned`, `ref`.
# Those appear on proto declarations (`proto external`, `proto owned string`).
METHOD_PATTERN = re.compile(
    r"^\s*(?:(?:override|static|proto|native|protected|private|const|"
    r"final|event|external|volatile|owned|ref)\s+)*"
    r"([A-Za-z_][A-Za-z0-9_]*(?:\s*<[^>]+>)?)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)"
)

# Same member regex the detector uses (es_member_redeclare_base._MEMBER_RE).
MEMBER_RE = re.compile(
    r"^\s*"
    r"(?:(?:protected|private|static|ref|autoptr|const|proto|native)\s+)*"
    r"[A-Za-z_]\w*(?:\s*<[^;{}]*>)?"
    r"\s+"
    r"(?P<name>m_\w+)"
    r"\s*(?:;|=(?!=))"
)

PARAM_NAME_RE = re.compile(r"(?P<name>[A-Za-z_]\w*)\s*$")

PP_OPEN_RE = re.compile(r"^\s*#\s*(?P<directive>ifdef|ifndef)\s+(?P<macro>\w+)")
PP_ELSE_RE = re.compile(r"^\s*#\s*else\b")
PP_ENDIF_RE = re.compile(r"^\s*#\s*endif\b")
PP_UNSUPPORTED_OPEN_RE = re.compile(r"^\s*#\s*(?:if|elif)\b")

CONTROL_FLOW_START = (
    "if",
    "else",
    "for",
    "foreach",
    "while",
    "switch",
    "return",
    "new",
    "delete",
    "break",
    "continue",
    "case",
    "default",
)

PARSER_GAPS_VS_API_INDEX = [
    "sealed class (Contact, PhysicsWorld) — api_index CLASS_PATTERN "
    "only allows modded|inherited",
    "proto/native prefixes on class headers",
    "method modifiers external, volatile, owned, ref — api_index "
    "METHOD_PATTERN misses proto external / proto owned string / "
    "proto volatile",
    "destructors (void ~Name) are skipped; they are not override targets",
    "multiline signatures are joined (api_index is single-line only)",
]


def _posix_relative(path, root):
    return path.relative_to(root).as_posix()


def _citation(relative_path, line_number):
    return "%s:%d" % (relative_path, line_number)


def _sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_digest(files, root):
    digest = hashlib.sha256()
    for path in files:
        digest.update(_posix_relative(path, root).encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def update_pp_stack(stack, line):
    opened = PP_OPEN_RE.match(line)
    if opened:
        stack.append(
            {
                "directive": opened.group("directive"),
                "macro": opened.group("macro"),
                "else": False,
            }
        )
        return
    if PP_UNSUPPORTED_OPEN_RE.match(line):
        stack.append(
            {"directive": "unsupported", "macro": None, "else": False}
        )
        return
    if PP_ELSE_RE.match(line):
        if stack:
            stack[-1]["else"] = not stack[-1]["else"]
        return
    if PP_ENDIF_RE.match(line):
        if stack:
            stack.pop()


def classify_stack(stack):
    """Return (required_defined, required_undefined, unknown)."""
    required_defined = set()
    required_undefined = set()
    unknown = False
    for frame in stack:
        if frame["directive"] == "unsupported":
            unknown = True
            continue
        macro = frame["macro"]
        in_true = not frame["else"]
        if frame["directive"] == "ifdef":
            if in_true:
                required_defined.add(macro)
            else:
                required_undefined.add(macro)
        elif frame["directive"] == "ifndef":
            if in_true:
                required_undefined.add(macro)
            else:
                required_defined.add(macro)
    return required_defined, required_undefined, unknown


def primary_console_macro(required_defined):
    console = required_defined & CONSOLE_MACROS
    if not console:
        return None
    if "PLATFORM_CONSOLE" in console:
        return "PLATFORM_CONSOLE"
    if len(console) == 1:
        return next(iter(console))
    return None


def extract_param_names(params_text):
    names = []
    for raw in params_text.split(","):
        part = re.sub(r"=.*$", "", raw).strip()
        part = re.sub(r"\[\d*\]\s*$", "", part).strip()
        if not part:
            continue
        match = PARAM_NAME_RE.search(part)
        if not match:
            return None
        names.append(match.group("name"))
    return tuple(names)


def _is_control_flow(signature):
    stripped = signature.lstrip()
    for keyword in CONTROL_FLOW_START:
        if stripped == keyword or stripped.startswith(keyword + " ") or stripped.startswith(
            keyword + "("
        ):
            return True
    return False


def _is_destructor(signature):
    return bool(re.search(r"\bvoid\s+~", signature))


def collect_c_files(vanilla_root):
    files = sorted(
        path
        for path in vanilla_root.rglob("*.c")
        if path.is_file()
    )
    return files


def scan_file(path, relative_path):
    # Decoded as the detectors read the vanilla tree (_vanilla_texts in
    # detectors/es_undefined_class_ref.py): 1.30's 3_game/global/world.c
    # has a cp1252 0x99 in a comment.
    raw = path.read_text(encoding="utf-8", errors="replace")
    text, _warnings = strip_enforce_comments_and_strings(raw, relative_path)
    lines = text.splitlines()

    classes = []
    methods = []
    members = []
    macros_seen = Counter()
    pp_stack = []
    class_stack = []
    pending_class = None
    brace_depth = 0

    for index, line in enumerate(lines):
        line_number = index + 1
        while class_stack and brace_depth < class_stack[-1]["body_depth"]:
            class_stack.pop()

        required_defined, required_undefined, unknown = classify_stack(pp_stack)
        never_compiled = bool(required_defined & NEVER_COMPILED_MACROS)

        open_match = PP_OPEN_RE.match(line)
        if open_match:
            macros_seen[open_match.group("macro")] += 1

        class_match = CLASS_HEADER_RE.match(line)
        if class_match:
            owner = class_stack[-1]["name"] if class_stack else ""
            is_global = owner == ""
            classes.append(
                {
                    "name": class_match.group("name"),
                    "base": class_match.group("base_colon")
                    or class_match.group("base_ext")
                    or "",
                    "global": is_global,
                    "relative_path": relative_path,
                    "line": line_number,
                    "required_defined": frozenset(required_defined),
                    "required_undefined": frozenset(required_undefined),
                    "unknown_pp": unknown,
                    "never_compiled": never_compiled,
                }
            )
            pending_class = {
                "name": class_match.group("name"),
                "body_depth": None,
            }

        signature, _end_index = collect_method_signature(lines, index)
        method_match = METHOD_PATTERN.match(signature)
        if (
            method_match
            and not _is_control_flow(signature)
            and not _is_destructor(signature)
        ):
            owner = class_stack[-1]["name"] if class_stack else ""
            param_names = extract_param_names(method_match.group(3))
            methods.append(
                {
                    "name": method_match.group(2),
                    "owner": owner,
                    "params": param_names,
                    "relative_path": relative_path,
                    "line": line_number,
                    "required_defined": frozenset(required_defined),
                    "required_undefined": frozenset(required_undefined),
                    "unknown_pp": unknown,
                    "never_compiled": never_compiled,
                    "console_macro": primary_console_macro(required_defined),
                }
            )

        if class_stack and brace_depth == class_stack[-1]["body_depth"]:
            member_match = MEMBER_RE.match(line)
            if member_match:
                members.append(
                    {
                        "name": member_match.group("name"),
                        "owner": class_stack[-1]["name"],
                        "relative_path": relative_path,
                        "line": line_number,
                        "never_compiled": never_compiled,
                    }
                )

        update_pp_stack(pp_stack, line)

        opens = line.count("{")
        closes = line.count("}")
        if pending_class is not None and opens:
            class_stack.append(
                {
                    "name": pending_class["name"],
                    "body_depth": brace_depth + 1,
                }
            )
            pending_class = None
        brace_depth += opens - closes
        while class_stack and brace_depth < class_stack[-1]["body_depth"]:
            class_stack.pop()

    return {
        "classes": classes,
        "methods": methods,
        "members": members,
        "macros": macros_seen,
        "bytes": path.stat().st_size,
    }


def _first_visible_declaration(entries):
    """Pick the first non-DOXYGEN-only declaration for a citation."""
    for entry in entries:
        if not entry.get("never_compiled"):
            return entry
    return entries[0] if entries else None


def build_global_class_names(classes, methods):
    declarations = defaultdict(list)
    for item in classes:
        if item["global"]:
            declarations[item["name"]].append(item)

    # Any vanilla method of this name — including the class's own constructor
    # (`void ClassName()`) — means the linter would flag vanilla itself if we
    # indexed the class. The detector does not distinguish constructors.
    method_names = set()
    for item in methods:
        if item["never_compiled"]:
            continue
        if item["name"]:
            method_names.add(item["name"])

    result = {}
    omitted_as_method = 0
    omitted_doxygen = 0
    for name, entries in declarations.items():
        live = [item for item in entries if not item["never_compiled"]]
        if not live:
            omitted_doxygen += 1
            continue
        if name in method_names:
            omitted_as_method += 1
            continue
        chosen = _first_visible_declaration(live)
        result[name] = _citation(chosen["relative_path"], chosen["line"])
    return result, omitted_as_method, omitted_doxygen


def build_base_members(members):
    by_class = defaultdict(dict)
    for item in members:
        if item["never_compiled"]:
            continue
        class_members = by_class[item["owner"]]
        if item["name"] in class_members:
            continue
        class_members[item["name"]] = _citation(
            item["relative_path"], item["line"]
        )
    return {name: dict(sorted(values.items())) for name, values in sorted(by_class.items())}


def build_override_params(methods):
    by_name = defaultdict(list)
    for item in methods:
        if item["never_compiled"]:
            continue
        by_name[item["name"]].append(item)

    result = {}
    omitted_ambiguous = 0
    omitted_unparseable = 0
    omitted_empty = 0
    omitted_names = []
    unparseable_names = []
    for name, entries in by_name.items():
        signatures = set()
        unparseable = False
        citation = None
        for item in entries:
            if item["params"] is None:
                unparseable = True
                continue
            signatures.add(item["params"])
            if citation is None:
                citation = _citation(item["relative_path"], item["line"])
        if unparseable and not signatures:
            omitted_unparseable += 1
            if len(unparseable_names) < 10:
                unparseable_names.append(name)
            continue
        if unparseable or len(signatures) != 1:
            omitted_ambiguous += 1
            if len(omitted_names) < 40:
                omitted_names.append(name)
            continue
        params = next(iter(signatures))
        if not params:
            omitted_empty += 1
            continue
        result[name] = {
            "params": list(params),
            "citation": citation,
        }
    return result, {
        "ambiguous": omitted_ambiguous,
        "unparseable": omitted_unparseable,
        "empty": omitted_empty,
        "sample_names": omitted_names,
        "unparseable_names": unparseable_names,
    }


def build_platform_gated_methods(methods):
    by_owner_name = defaultdict(list)
    for item in methods:
        if item["never_compiled"]:
            continue
        if not item["owner"]:
            continue
        by_owner_name[(item["owner"], item["name"])].append(item)

    qualified = {}
    for (owner, name), entries in by_owner_name.items():
        macros = set()
        all_gated = True
        citation = None
        for item in entries:
            if item["unknown_pp"] or item["console_macro"] is None:
                all_gated = False
                break
            macros.add(item["console_macro"])
            if citation is None:
                citation = _citation(item["relative_path"], item["line"])
        if not all_gated or len(macros) != 1:
            continue
        qualified.setdefault(name, []).append(
            {
                "owner": owner,
                "macro": next(iter(macros)),
                "citation": citation,
            }
        )

    result = {}
    omitted_multi_owner = 0
    for name, owners in qualified.items():
        unique_pairs = {(item["owner"], item["macro"]) for item in owners}
        if len(unique_pairs) != 1:
            omitted_multi_owner += 1
            continue
        result[name] = {
            "owner": owners[0]["owner"],
            "macro": owners[0]["macro"],
            "citation": owners[0]["citation"],
        }
    return result, omitted_multi_owner


def verify_nonexistent_methods(files, root):
    counts = {name: 0 for name in VANILLA_NONEXISTENT_METHODS}
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(name) for name in VANILLA_NONEXISTENT_METHODS) + r")\b"
    )
    hits = {name: [] for name in VANILLA_NONEXISTENT_METHODS}
    for path in files:
        text, _warnings = strip_enforce_comments_and_strings(
            path.read_text(encoding="utf-8", errors="replace"),
            _posix_relative(path, root),
        )
        for match in pattern.finditer(text):
            name = match.group(1)
            counts[name] += 1
            if len(hits[name]) < 5:
                line = text.count("\n", 0, match.start()) + 1
                hits[name].append(_citation(_posix_relative(path, root), line))
    return {
        name: {"occurrences": counts[name], "sample_hits": hits[name]}
        for name in VANILLA_NONEXISTENT_METHODS
    }


def classify_macro(name):
    if name in CONSOLE_MACROS:
        return "console-undefined-on-pc-release"
    if name in NEVER_COMPILED_MACROS:
        return "never-compiled"
    return "reported-undecided"


def build_index_document(vanilla_root):
    vanilla_root = Path(vanilla_root).resolve()
    if not vanilla_root.is_dir():
        raise FileNotFoundError(
            "vanilla root is not a directory: %s" % vanilla_root
        )

    files = collect_c_files(vanilla_root)
    classes = []
    methods = []
    members = []
    macros = Counter()
    total_bytes = 0
    read_errors = []

    for path in files:
        relative = _posix_relative(path, vanilla_root)
        try:
            scanned = scan_file(path, relative)
        except (OSError, UnicodeError) as error:
            read_errors.append("%s: %s" % (relative, type(error).__name__))
            continue
        classes.extend(scanned["classes"])
        methods.extend(scanned["methods"])
        members.extend(scanned["members"])
        macros.update(scanned["macros"])
        total_bytes += scanned["bytes"]

    global_class_names, omitted_as_method, omitted_doxygen = build_global_class_names(
        classes, methods
    )
    base_members = build_base_members(members)
    override_params, override_omitted = build_override_params(methods)
    platform_gated, omitted_multi_owner = build_platform_gated_methods(methods)
    nonexistent = verify_nonexistent_methods(files, vanilla_root)

    member_count = sum(len(values) for values in base_members.values())
    document = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "vanilla_root": str(vanilla_root),
        "file_count": len(files),
        "parsed_file_count": len(files) - len(read_errors),
        "total_bytes": total_bytes,
        "tree_digest": tree_digest(files, vanilla_root),
        "generated_by": "build_vanilla_index.py",
        "global_class_names": dict(sorted(global_class_names.items())),
        "base_members": base_members,
        "override_params": dict(sorted(override_params.items())),
        "platform_gated_methods": dict(sorted(platform_gated.items())),
        "nonexistent_method_verification": nonexistent,
        "preprocessor_macros": {
            name: {
                "count": count,
                "classification": classify_macro(name),
            }
            for name, count in sorted(macros.items())
        },
        "diagnostics": {
            "class_declaration_count": len(classes),
            "method_declaration_count": len(methods),
            "member_declaration_count": len(members),
            "global_class_name_count": len(global_class_names),
            "base_member_class_count": len(base_members),
            "base_member_count": member_count,
            "override_param_count": len(override_params),
            "platform_gated_count": len(platform_gated),
            "omitted_global_class_used_as_method": omitted_as_method,
            "omitted_global_class_doxygen_only": omitted_doxygen,
            "omitted_override_params": override_omitted,
            "omitted_platform_gated_multi_owner": omitted_multi_owner,
            "read_errors": read_errors,
            "parser_gaps_vs_api_index": PARSER_GAPS_VS_API_INDEX,
            "console_macros": sorted(CONSOLE_MACROS),
        },
    }
    return document


def write_index(document, out_path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True)
    out_path.write_text(payload + "\n", encoding="utf-8")
    return out_path


def format_summary(document, out_path):
    diagnostics = document["diagnostics"]
    omitted = diagnostics["omitted_override_params"]
    lines = [
        "Wrote %s" % out_path,
        "vanilla_root=%s" % document["vanilla_root"],
        "files=%d parsed=%d bytes=%d digest=%s"
        % (
            document["file_count"],
            document["parsed_file_count"],
            document["total_bytes"],
            document["tree_digest"],
        ),
        "global_class_names=%d" % diagnostics["global_class_name_count"],
        "base_members=%d across %d classes"
        % (
            diagnostics["base_member_count"],
            diagnostics["base_member_class_count"],
        ),
        "override_params=%d (omitted ambiguous=%d unparseable=%d empty=%d)"
        % (
            diagnostics["override_param_count"],
            omitted["ambiguous"],
            omitted["unparseable"],
            omitted["empty"],
        ),
        "platform_gated_methods=%d" % diagnostics["platform_gated_count"],
    ]
    for name, payload in document["nonexistent_method_verification"].items():
        lines.append(
            "nonexistent %s occurrences=%d" % (name, payload["occurrences"])
        )
    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Generate vanilla_index.json from a DayZ scripts tree."
    )
    parser.add_argument(
        "--vanilla-root",
        type=Path,
        default=DEFAULT_VANILLA_ROOT,
        help="Root of the vanilla scripts tree (default: P:\\scripts)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_PATH,
        help="Output JSON path (default: scripts/shared/vanilla_index.json)",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    document = build_index_document(args.vanilla_root)
    out_path = write_index(document, args.out)
    print(format_summary(document, out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
