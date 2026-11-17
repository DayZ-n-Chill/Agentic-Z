"""dayz-pbo-reverse-engineering: classify PBOs from their headers, without extracting them.

Step 1 of the skill (the inventory pass): for each .pbo it prints the header prefix,
the entry count, the entry types, and whether the PBO is a deployable mod, a
config-only PBO, a source asset distribution or a data-only PBO. It also names entries an extractor
should not be trusted with (path traversal, device names, control characters).

Pure offline reader: it opens only the .pbo files it is given, so it does not gate
on /dayz-preflight. See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

pbo_entries = h.load_module(
    "dayz_pbo_reverse_entries", Path(__file__).resolve().parents[1] / "dayz-build-pbo" / "pbo_entries.py"
)

OK, WARN, FAIL = h.OK, h.WARN, h.FAIL

CONFIG_NAMES = {"config.bin", "config.cpp"}
# Entry types that make a PBO something the game loads as a mod.
MOD_SUFFIXES = {".c", ".p3d", ".layout"}
# Entry types that mark a PBO used to hand out source assets, not to be loaded.
SOURCE_SUFFIXES = {".rar", ".zip", ".7z", ".fbx", ".blend", ".max", ".obj", ".psd", ".spp", ".tga"}
_DEVICE_NAMES = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
_GUID_RE = re.compile(r"\{?[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}\}?", re.I)

MOD, CONFIG_ONLY, SOURCE, DATA = "mod", "config-only", "source-distribution", "data-only"


def unsafe_reason(name: str) -> str | None:
    """Why an extractor should not write this entry name to disk, or None when it is safe."""
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in name):
        return "control character"
    if name.startswith(("/", "\\")):
        return "absolute path"
    if re.match(r"^[A-Za-z]:", name):
        return "drive letter"
    segments = re.split(r"[\\/]", name)
    if ".." in segments:
        return "'..' segment"
    if any(seg.split(".")[0].lower() in _DEVICE_NAMES for seg in segments if seg):
        return "Windows device name"
    return None


def inventory(path: Path, check_trailer: bool = True) -> dict:
    """The header facts and the verdict for one PBO. Raises PboError or OSError when it cannot be read."""
    pbo = pbo_entries.read_pbo(path, check_trailer=check_trailer)
    suffixes = Counter(Path(e.name.replace("\\", "/")).suffix.lower() or "(none)" for e in pbo.entries)
    configs = [e for e in pbo.entries if e.key.rsplit("\\", 1)[-1] in CONFIG_NAMES]
    has_config = any(e.data_size > 0 for e in configs)
    mod_files = sum(suffixes[s] for s in MOD_SUFFIXES)
    source_files = sum(suffixes[s] for s in SOURCE_SUFFIXES)
    if has_config and mod_files:
        kind = MOD
    elif has_config:
        kind = CONFIG_ONLY
    elif source_files:
        kind = SOURCE
    else:
        kind = DATA
    unsafe = [(e.name, reason) for e in pbo.entries for reason in [unsafe_reason(e.name)] if reason]
    return {
        "path": str(path),
        "prefix": pbo.prefix,
        "properties": dict(pbo.properties),
        "entries": len(pbo.entries),
        "bytes": sum(e.data_size for e in pbo.entries),
        "kind": kind,
        "config": sorted(e.name for e in configs if e.data_size > 0),
        "empty_config": sorted(e.name for e in configs if e.data_size == 0),
        "suffixes": dict(sorted(suffixes.items(), key=lambda kv: (-kv[1], kv[0]))),
        "compressed": sum(1 for e in pbo.entries if e.compressed),
        "guid_names": sum(1 for e in pbo.entries if _GUID_RE.search(e.name)),
        "unsafe": [{"name": name, "reason": reason} for name, reason in unsafe],
        "trailer_ok": pbo.trailer_ok,
    }


KIND_TEXT = {
    MOD: "deployable mod (config plus scripts, models or layouts)",
    CONFIG_ONLY: "config-only PBO (mounts, but ships no script, model or layout)",
    SOURCE: "source asset distribution (archives or source art, no config to load)",
    DATA: "data only (no config; loaded only if another PBO refers to its files)",
}


def print_report(info: dict) -> None:
    print(f"{OK} {info['path']}")
    print(f"       prefix: {info['prefix'] or '(none)'}   entries: {info['entries']}   payload: {info['bytes']:,} bytes")
    print(f"       kind:   {KIND_TEXT[info['kind']]}")
    types = ", ".join(f"{suffix} {count}" for suffix, count in list(info["suffixes"].items())[:12])
    print(f"       types:  {types or '(no entries)'}")
    if info["empty_config"]:
        print(f"{WARN} empty config entr{'y' if len(info['empty_config']) == 1 else 'ies'}: {', '.join(info['empty_config'])}")
    if info["compressed"]:
        print(
            f"{WARN} {info['compressed']} compressed entr{'y' if info['compressed'] == 1 else 'ies'}:"
            " prove the extractor decoded them before reading the output (references/pitfalls.md)."
        )
    if info["guid_names"] or info["unsafe"]:
        names = ", ".join(f"{u['name']!r} ({u['reason']})" for u in info["unsafe"][:5])
        print(
            f"{WARN} {info['guid_names']} GUID-like and {len(info['unsafe'])} unsafe entry name(s)"
            + (f": {names}" if names else "")
            + "\n       This looks obfuscated or hostile. Do not extract it over existing files, and do not sweep"
            " obfuscated output."
        )
    if info["trailer_ok"] is False:
        print(f"{WARN} no valid checksum trailer: the file may be cut short or packed by a hand-made tool.")


def find_pbos(targets: list[str]) -> list[Path]:
    found: list[Path] = []
    for target in targets:
        path = Path(target)
        if path.is_dir():
            found += sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() == ".pbo")
        else:
            found.append(path)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify DayZ PBOs from their headers, without extracting them.")
    parser.add_argument("targets", nargs="+", help="A .pbo file, or a folder searched for .pbo files at any depth.")
    parser.add_argument("--json", action="store_true", help="Print one JSON list instead of the text report.")
    parser.add_argument("--no-trailer", action="store_true", help="Skip the checksum trailer (it hashes the whole file).")
    args = parser.parse_args(argv)

    pbos = find_pbos(args.targets)
    if not pbos:
        print(f"{FAIL} No .pbo file found in: {', '.join(args.targets)}")
        return 1
    results, failed = [], 0
    for path in pbos:
        try:
            info = inventory(path, check_trailer=not args.no_trailer)
        except (pbo_entries.PboError, OSError) as e:
            failed += 1
            info = {"path": str(path), "error": str(e)}
            if not args.json:
                print(f"{FAIL} {path}: not a readable PBO ({e})")
        else:
            if not args.json:
                print_report(info)
        results.append(info)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        kinds = Counter(r["kind"] for r in results if "kind" in r)
        summary = ", ".join(f"{count} {kind}" for kind, count in sorted(kinds.items())) or "none readable"
        print(f"\n{len(pbos)} PBO(s): {summary}" + (f"; {failed} unreadable" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
