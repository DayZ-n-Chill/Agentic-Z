"""Reproducible corpus gate for `dayz-ui-lab` (C1) plus the C5 provenance audit.

The corpora are licence-restricted and none of them is redistributed here. This
module carries identity only -- URL, pin, hashes, licence -- and reads the actual
bytes from wherever `sources/local-roots.json` points, which is machine-local and
untracked. A corpus whose root is missing is reported as such and fails the gate;
it is never silently skipped, because "not measured" and "passed" must not look
alike.

Exit codes: 0 when every configured corpus meets its expectations and the
provenance audit is clean, 1 otherwise. Findings carry stable codes so a caller
can tell a missing root from a parse regression.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

MODULE_DIR = Path(__file__).resolve().parent
TOOL_DIR = MODULE_DIR.parent
DEFAULT_MANIFEST = TOOL_DIR / "corpora" / "manifest.json"

# These named fixture directories are the only places where this repository may
# track .layout files. Everything else may be a leaked third-party layout.
FIRST_PARTY_LAYOUT_DIR = "tools/dayz-ui-lab/probe/LF_UIProbe/gui/layouts"
FIRST_PARTY_LAYOUT_DIRS = (
    FIRST_PARTY_LAYOUT_DIR,
    "tools/dayz-ui-lab/fixtures/scenarios",
)


def _load_parser() -> Any:
    spec = importlib.util.spec_from_file_location(
        "dayz_ui_lab_corpus_parse", MODULE_DIR / "parse.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load parse.py next to corpus.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def finding(code: str, corpus_id: str, message: str, evidence: str = "") -> dict[str, str]:
    return {
        "code": code,
        "corpus_id": corpus_id,
        "message": message,
        "evidence": evidence,
    }


def resolve_roots(
    pack_root: Path, required: set[str] | None = None
) -> tuple[dict[str, Path], list[dict[str, str]]]:
    """Read the untracked local-roots file; absence is a finding, not a crash.

    `required` limits the reporting to the roots this manifest actually uses. The
    file is shared with the API-index resolver and lists roots unrelated to the
    corpora, and reporting those as findings would bury the ones that matter.
    """
    path = pack_root / "sources" / "local-roots.json"
    if not path.is_file():
        return {}, [
            finding(
                "CORPUS-LOCAL-ROOTS-MISSING",
                "",
                "sources/local-roots.json is absent; copy local-roots.example.json "
                "and point it at your corpora.",
                str(path),
            )
        ]

    document = json.loads(path.read_text(encoding="utf-8"))
    roots: dict[str, Path] = {}
    findings: list[dict[str, str]] = []
    for root_id, config in document.get("roots", {}).items():
        if "path" in config:
            roots[root_id] = Path(str(config["path"]))
            continue
        name = config.get("path_env")
        value = os.environ.get(str(name)) if name else None
        if value:
            roots[root_id] = Path(value)
        elif required is None or root_id in required:
            findings.append(
                finding(
                    "CORPUS-ROOT-ENV-UNSET",
                    "",
                    f"root {root_id!r} resolves through {name!r} and that variable is unset.",
                    root_id,
                )
            )
    return roots, findings


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_identity(
    entry: dict[str, Any], roots: dict[str, Path]
) -> list[dict[str, str]]:
    """Verify the pinned artifact hashes, when the corpus declares any."""
    corpus_id = str(entry["corpus_id"])
    identity_root_id = entry.get("identity_root_id")
    expected_files = entry.get("identity_files") or []
    if not identity_root_id or not expected_files:
        return []

    root = roots.get(str(identity_root_id))
    if root is None or not root.is_dir():
        return [
            finding(
                "CORPUS-IDENTITY-ROOT-MISSING",
                corpus_id,
                f"identity root {identity_root_id!r} is not configured or not a directory.",
                str(root) if root else str(identity_root_id),
            )
        ]

    findings: list[dict[str, str]] = []
    present = {path.name: path for path in root.rglob("*") if path.is_file()}
    for expected in expected_files:
        name = str(expected["name"])
        actual = present.get(name)
        if actual is None:
            findings.append(
                finding("CORPUS-IDENTITY-FILE-MISSING", corpus_id, f"{name} not found under the identity root.", str(root))
            )
            continue
        size = actual.stat().st_size
        if size != int(expected["bytes"]):
            findings.append(
                finding(
                    "CORPUS-IDENTITY-MISMATCH",
                    corpus_id,
                    f"{name} size differs from the pinned manifest.",
                    f"expected={expected['bytes']} actual={size}",
                )
            )
            continue
        digest = sha256_of(actual)
        if digest != str(expected["sha256"]):
            findings.append(
                finding(
                    "CORPUS-IDENTITY-MISMATCH",
                    corpus_id,
                    f"{name} sha256 differs from the pinned manifest.",
                    f"expected={expected['sha256']} actual={digest}",
                )
            )
    return findings


def measure_corpus(
    entry: dict[str, Any], roots: dict[str, Path], parse: Any
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    corpus_id = str(entry["corpus_id"])
    root_id = str(entry["local_root_id"])
    root = roots.get(root_id)

    result: dict[str, Any] = {
        "corpus_id": corpus_id,
        "root_id": root_id,
        "root": str(root) if root else None,
        "layouts_found": 0,
        "parse_ok": 0,
        "parse_failed": 0,
        "failures": [],
        "diagnostics": 0,
        "diagnostic_codes": {},
        "expected_layout_count": int(entry["expected_layout_count"]),
        "expected_parse_ok": int(entry["expected_parse_ok"]),
        "measured": False,
    }

    if root is None or not root.is_dir():
        return result, [
            finding(
                "CORPUS-ROOT-MISSING",
                corpus_id,
                f"root {root_id!r} is not configured or not a directory; corpus not measured.",
                str(root) if root else root_id,
            )
        ]

    findings = check_identity(entry, roots)

    layouts = sorted(root.rglob("*.layout"))
    result["layouts_found"] = len(layouts)
    result["measured"] = True

    for path in layouts:
        try:
            document = parse.parse_file(path)
            result["parse_ok"] += 1
            # C1 also demands zero false missing-child-block. B19 removed the
            # branch that emitted it, but "the code cannot emit it" is an
            # argument; counting what the parser actually emitted is a
            # measurement, and it stays honest if a later change reintroduces
            # a diagnostic.
            for diagnostic in getattr(document, "diagnostics", []) or []:
                result["diagnostics"] += 1
                code = str(diagnostic.get("code", diagnostic))
                result["diagnostic_codes"][code] = (
                    result["diagnostic_codes"].get(code, 0) + 1
                )
        except Exception as error:  # noqa: BLE001 - any parse failure is a finding
            result["parse_failed"] += 1
            result["failures"].append(
                {"layout": path.name, "error": f"{type(error).__name__}: {error}"}
            )

    if result["layouts_found"] != result["expected_layout_count"]:
        findings.append(
            finding(
                "CORPUS-COUNT-MISMATCH",
                corpus_id,
                "layout count differs from the pinned manifest; the checkout may not be at the pin.",
                f"expected={result['expected_layout_count']} actual={result['layouts_found']}",
            )
        )
    if result["parse_ok"] != result["expected_parse_ok"]:
        findings.append(
            finding(
                "CORPUS-PARSE-REGRESSION",
                corpus_id,
                "parse count differs from the pinned expectation.",
                f"expected={result['expected_parse_ok']} actual={result['parse_ok']}",
            )
        )
    if result["diagnostics"]:
        findings.append(
            finding(
                "CORPUS-DIAGNOSTICS-EMITTED",
                corpus_id,
                "a valid layout produced parser diagnostics; B19 requires zero.",
                json.dumps(result["diagnostic_codes"], sort_keys=True),
            )
        )
    return result, findings


def audit_redistribution(
    pack_root: Path, entries: list[dict[str, Any]], roots: dict[str, Path]
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """C5: no third-party layout may live inside the pack.

    Compared by content hash rather than by path, so moving or renaming a leaked
    file does not hide it.
    """
    # Exclude on the path RELATIVE to the pack root. Filtering on absolute parts
    # silently matched everything when the pack itself lives under .worktrees,
    # which made this audit measure zero files while reporting success.
    excluded_top = {"reports", "dist", "build", ".git"}
    tracked = []
    for path in sorted(pack_root.rglob("*.layout")):
        relative = path.relative_to(pack_root)
        if relative.parts and relative.parts[0] in excluded_top:
            continue
        tracked.append(path)

    first_party_dirs = [
        (pack_root / directory).resolve() for directory in FIRST_PARTY_LAYOUT_DIRS
    ]
    outside = [
        str(p.relative_to(pack_root).as_posix())
        for p in tracked
        if not any(directory in p.resolve().parents for directory in first_party_dirs)
    ]

    third_party_digests: dict[str, str] = {}
    for entry in entries:
        if entry.get("role") == "first-party-regression":
            continue
        root = roots.get(str(entry["local_root_id"]))
        if root is None or not root.is_dir():
            continue
        for path in root.rglob("*.layout"):
            third_party_digests[sha256_of(path)] = str(entry["corpus_id"])

    leaked = []
    for path in tracked:
        digest = sha256_of(path)
        if digest in third_party_digests:
            leaked.append(
                {
                    "path": str(path.relative_to(pack_root).as_posix()),
                    "corpus_id": third_party_digests[digest],
                }
            )

    findings: list[dict[str, str]] = []
    for item in outside:
        findings.append(
            finding(
                "CORPUS-LAYOUT-OUTSIDE-FIRST-PARTY",
                "",
                "a tracked .layout lives outside the first-party probe fixtures.",
                item,
            )
        )
    for item in leaked:
        findings.append(
            finding(
                "CORPUS-THIRD-PARTY-REDISTRIBUTED",
                str(item["corpus_id"]),
                "a tracked file is byte-identical to a third-party corpus layout.",
                str(item["path"]),
            )
        )

    return (
        {
            "tracked_layouts": len(tracked),
            "outside_first_party": outside,
            "third_party_layouts_compared": len(third_party_digests),
            "leaked": leaked,
        },
        findings,
    )


def run(pack_root: Path, manifest_path: Path) -> dict[str, Any]:
    parse = _load_parser()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = list(manifest["corpora"])

    required: set[str] = set()
    for entry in entries:
        required.add(str(entry["local_root_id"]))
        if entry.get("identity_root_id"):
            required.add(str(entry["identity_root_id"]))

    roots, findings = resolve_roots(pack_root, required)

    results = []
    for entry in entries:
        result, entry_findings = measure_corpus(entry, roots, parse)
        results.append(result)
        findings.extend(entry_findings)

    audit, audit_findings = audit_redistribution(pack_root, entries, roots)
    findings.extend(audit_findings)

    measured = [r for r in results if r["measured"]]
    report = {
        "schema_version": 1,
        "command": "dayz-ui-lab corpus",
        "manifest": str(manifest_path.as_posix()),
        "corpora": results,
        "totals": {
            "corpora_declared": len(entries),
            "corpora_measured": len(measured),
            "layouts_found": sum(r["layouts_found"] for r in measured),
            "parse_ok": sum(r["parse_ok"] for r in measured),
            "parse_failed": sum(r["parse_failed"] for r in measured),
            "diagnostics": sum(r["diagnostics"] for r in measured),
        },
        "provenance_audit": audit,
        "findings": findings,
        "verdict": "PASS" if not findings else "FAIL",
    }
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure the dayz-ui-lab layout corpora against their pinned manifest.",
    )
    parser.add_argument("--root", default=".", help="pack repository root")
    parser.add_argument("--manifest", default=None, help="corpus manifest path")
    parser.add_argument("--report", default=None, help="write the JSON report here")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    pack_root = Path(args.root).resolve()
    manifest_path = Path(args.manifest) if args.manifest else DEFAULT_MANIFEST

    report = run(pack_root, manifest_path)

    for result in report["corpora"]:
        if not result["measured"]:
            print(f"  {result['corpus_id']:24} NOT MEASURED (root {result['root_id']!r})")
            continue
        print(
            f"  {result['corpus_id']:24} {result['parse_ok']}/{result['layouts_found']} parse"
            f"  (expected {result['expected_parse_ok']}/{result['expected_layout_count']})"
        )
        for failure in result["failures"]:
            print(f"      FAIL {failure['layout']}: {failure['error']}")

    totals = report["totals"]
    print(
        f"totals: {totals['parse_ok']}/{totals['layouts_found']} layouts parse across "
        f"{totals['corpora_measured']}/{totals['corpora_declared']} corpora, "
        f"{totals['diagnostics']} diagnostics emitted"
    )
    audit = report["provenance_audit"]
    print(
        f"provenance: {audit['tracked_layouts']} tracked .layout, "
        f"{len(audit['leaked'])} redistributed, "
        f"{audit['third_party_layouts_compared']} third-party layouts compared"
    )

    for item in report["findings"]:
        print(f"  {item['code']} | {item['corpus_id'] or '-'} | {item['message']} | {item['evidence']}")

    if args.report:
        Path(args.report).write_bytes(
            (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
        )

    print(f"verdict={report['verdict']}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
