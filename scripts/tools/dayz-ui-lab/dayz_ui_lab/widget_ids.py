"""Derive and audit DayZ widget IDs from .layout files."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


MODULE_DIR = Path(__file__).resolve().parent
SCHEMA = "dayz-ui-widget-ids-v1"
ID_LITERAL_RE = re.compile(r"^\{([0-9A-Fa-f]{16})\}$")
TSV_HEADER = "line\tclass\tname\tstored_id\tderived_id\tmatch\tnote"


def _load_parse() -> Any:
    spec = importlib.util.spec_from_file_location(
        "dayz_ui_lab_widget_ids_parse", MODULE_DIR / "parse.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load parse.py next to widget_ids.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


parse = _load_parse()


def widget_crc(data: bytes) -> int:
    """CRC-32 with polynomial 0x04C11DB7, MSB first, not augmented."""
    reg = 0xFFFFFFFF
    for byte in data:
        for shift in range(7, -1, -1):
            bit = (byte >> shift) & 1
            top = (reg >> 31) & 1
            reg = ((reg << 1) | bit) & 0xFFFFFFFF
            if top:
                reg ^= 0x04C11DB7
    return reg ^ 0xFFFFFFFF


def chain_id(names: list[str]) -> str:
    return "00000000%08X" % widget_crc("".join(names).encode("utf-8"))


def _id_literal(value: str) -> str | None:
    match = ID_LITERAL_RE.match(value)
    if match is None:
        return None
    return match.group(1).upper()


def _first_attr(node: Any, key: str) -> Any:
    values = node.attrs.get(key)
    if not values:
        return None
    return values[0]


def _widget_name(node: Any) -> str:
    name_value = _first_attr(node, "Name")
    if name_value is not None:
        return str(name_value)
    if _id_literal(node.name) is not None:
        return ""
    return node.name


def _build_rows(roots: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def visit(node: Any, depth: int, ancestor_names: list[str]) -> None:
        if not parse.is_widget_node(node):
            return

        name = _widget_name(node)
        if depth == 0:
            chain = [name]
            child_ancestors: list[str] = []
        else:
            chain = [name] + ancestor_names
            child_ancestors = chain

        stored_id = _id_literal(node.name)
        prefab_value = _first_attr(node, "Prefab")
        prefab = _id_literal(str(prefab_value)) if prefab_value is not None else None

        if name == "":
            derived_id: str | None = None
            note: str | None = "unnamed"
        elif any(part == "" for part in chain[1:]):
            derived_id = None
            note = "unnamed-ancestor"
        else:
            derived_id = chain_id(chain)
            note = None

        if stored_id is not None and derived_id is not None:
            match: bool | None = stored_id == derived_id
        else:
            match = None

        effective_id = stored_id if stored_id is not None else derived_id

        rows.append(
            {
                "line": node.line,
                "class": node.cls,
                "name": name,
                "chain": chain,
                "stored_id": stored_id,
                "derived_id": derived_id,
                "prefab": prefab,
                "match": match,
                "note": note,
                "effective_id": effective_id,
            }
        )

        for child in node.children:
            visit(child, depth + 1, child_ancestors)

    for root in roots:
        visit(root, 0, [])
    return rows


def _load_layout(path: Path, source_path: str) -> Any:
    data = path.read_bytes()
    text = data.decode("utf-8-sig", errors="replace")
    return parse.parse_text(text, source_path)


def _json_widget(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "line": row["line"],
        "class": row["class"],
        "name": row["name"],
        "chain": row["chain"],
        "stored_id": row["stored_id"],
        "derived_id": row["derived_id"],
        "prefab": row["prefab"],
        "match": row["match"],
        "note": row["note"],
    }


def _derive_tsv(rows: list[dict[str, Any]]) -> str:
    lines = [TSV_HEADER]
    for row in rows:
        if row["match"] is None:
            match = ""
        elif row["match"]:
            match = "yes"
        else:
            match = "no"
        lines.append(
            "\t".join(
                [
                    str(row["line"]),
                    row["class"],
                    row["name"],
                    row["stored_id"] or "",
                    row["derived_id"] or "",
                    match,
                    row["note"] or "",
                ]
            )
        )
    return "\n".join(lines)


def _collisions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for order, row in enumerate(rows):
        effective_id = row["effective_id"]
        if effective_id is None:
            continue
        groups.setdefault(effective_id, []).append((order, row))

    collisions: list[dict[str, Any]] = []
    for effective_id, members in groups.items():
        if len(members) < 2:
            continue
        members.sort(key=lambda item: item[0])
        collisions.append(
            {
                "id": effective_id,
                "widgets": [
                    {"line": row["line"], "name": row["name"]}
                    for _, row in members
                ],
                "order": members[0][0],
            }
        )
    collisions.sort(key=lambda item: item["order"])
    return collisions


def _scan_paths(root: Path) -> list[Path]:
    paths = list(root.rglob("*.layout"))
    return sorted(paths, key=lambda path: path.relative_to(root).as_posix())


def _cmd_derive(args: argparse.Namespace) -> int:
    source = args.layout
    try:
        doc = _load_layout(Path(source), source)
    except parse.LayoutSyntaxError as error:
        print(str(error), file=sys.stderr)
        return 2
    except OSError as error:
        print(f"{source}: {error}", file=sys.stderr)
        return 2

    rows = _build_rows(doc.roots)
    if args.json:
        document = {
            "schema": SCHEMA,
            "command": "derive",
            "source": source,
            "widgets": [_json_widget(row) for row in rows],
        }
        print(json.dumps(document, ensure_ascii=False))
    else:
        print(_derive_tsv(rows))
    return 0


def _cmd_scan(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    if not root.is_dir():
        print(f"{args.dir}: not a directory", file=sys.stderr)
        return 2

    files: list[dict[str, Any]] = []
    parse_errors: list[dict[str, Any]] = []
    lines: list[str] = []
    total_stored = 0
    total_derived_match = 0
    total_upper32_nonzero = 0

    for path in _scan_paths(root):
        relative = path.relative_to(root).as_posix()
        try:
            doc = _load_layout(path, str(path))
        except parse.LayoutSyntaxError as error:
            message = str(error).replace("\n", " ")
            parse_errors.append({"path": relative, "message": message})
            lines.append(f"{relative}\tPARSE-ERROR\t{message}")
            continue
        except OSError as error:
            message = str(error).replace("\n", " ")
            parse_errors.append({"path": relative, "message": message})
            lines.append(f"{relative}\tPARSE-ERROR\t{message}")
            continue

        rows = _build_rows(doc.roots)
        stored = sum(1 for row in rows if row["stored_id"] is not None)
        derived_match = sum(1 for row in rows if row["match"] is True)
        upper32_nonzero = sum(
            1
            for row in rows
            if row["stored_id"] is not None and row["stored_id"][:8] != "00000000"
        )
        files.append(
            {
                "path": relative,
                "stored": stored,
                "derived_match": derived_match,
                "upper32_nonzero": upper32_nonzero,
            }
        )
        total_stored += stored
        total_derived_match += derived_match
        total_upper32_nonzero += upper32_nonzero
        lines.append(
            f"{relative}\tstored={stored}\tderived_match={derived_match}"
            f"\tupper32_nonzero={upper32_nonzero}"
        )

    total = {
        "files": len(files),
        "stored": total_stored,
        "derived_match": total_derived_match,
        "upper32_nonzero": total_upper32_nonzero,
        "parse_errors": len(parse_errors),
    }
    lines.append(
        f"TOTAL\tfiles={total['files']}\tstored={total['stored']}"
        f"\tderived_match={total['derived_match']}"
        f"\tupper32_nonzero={total['upper32_nonzero']}"
        f"\tparse_errors={total['parse_errors']}"
    )

    if args.json:
        document = {
            "schema": SCHEMA,
            "command": "scan",
            "root": args.dir,
            "files": files,
            "parse_errors": parse_errors,
            "total": total,
        }
        print(json.dumps(document, ensure_ascii=False))
    else:
        print("\n".join(lines))
    return 1 if parse_errors else 0


def _cmd_collide(args: argparse.Namespace) -> int:
    source = args.layout
    try:
        doc = _load_layout(Path(source), source)
    except parse.LayoutSyntaxError as error:
        print(str(error), file=sys.stderr)
        return 2
    except OSError as error:
        print(f"{source}: {error}", file=sys.stderr)
        return 2

    rows = _build_rows(doc.roots)
    collisions = _collisions(rows)
    if args.json:
        document = {
            "schema": SCHEMA,
            "command": "collide",
            "source": source,
            "collisions": [
                {"id": item["id"], "widgets": item["widgets"]}
                for item in collisions
            ],
        }
        print(json.dumps(document, ensure_ascii=False))
    else:
        for item in collisions:
            members = "; ".join(
                f"{widget['line']}:{widget['name']}" for widget in item["widgets"]
            )
            print(f"{item['id']}\t{members}")
    return 1 if collisions else 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Derive and audit DayZ widget IDs from .layout files.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    derive = subparsers.add_parser("derive", help="derive widget IDs for one layout")
    derive.add_argument("layout", help="layout path")
    derive.add_argument("--json", action="store_true", help="emit JSON")
    derive.set_defaults(func=_cmd_derive)

    scan = subparsers.add_parser("scan", help="scan a directory of layouts")
    scan.add_argument("dir", help="layout directory")
    scan.add_argument("--json", action="store_true", help="emit JSON")
    scan.set_defaults(func=_cmd_scan)

    collide = subparsers.add_parser("collide", help="report shared effective IDs")
    collide.add_argument("layout", help="layout path")
    collide.add_argument("--json", action="store_true", help="emit JSON")
    collide.set_defaults(func=_cmd_collide)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
