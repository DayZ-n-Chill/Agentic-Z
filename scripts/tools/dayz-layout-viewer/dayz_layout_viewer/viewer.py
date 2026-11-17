"""DayZ .layout -> self-contained HTML preview at four viewports.

Consumes the pack format parser in tools/dayz-ui-lab/dayz_ui_lab/parse.py
(LayoutDoc + phase-1 geometry) and embeds the resolved tree at 1080p, 1440p,
21:9 and 720p into one *.preview.html.

This is a structural approximation, not the engine's widget rasterizer.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from .html_template import TEMPLATE

VIEWPORTS = [
    {"label": "1080p (16:9)", "width": 1920, "height": 1080},
    {"label": "1440p (16:9)", "width": 2560, "height": 1440},
    {"label": "Ultrawide (21:9)", "width": 3440, "height": 1440},
    {"label": "720p (16:9)", "width": 1280, "height": 720},
]

_PARSE: ModuleType | None = None


def load_layout_parser() -> ModuleType:
    """Load tools/dayz-ui-lab/dayz_ui_lab/parse.py, the pack format parser."""
    global _PARSE
    if _PARSE is not None:
        return _PARSE

    try:
        import dayz_ui_lab.parse as layout_parse  # type: ignore[import-not-found]
    except ImportError:
        layout_parse = None

    if layout_parse is None:
        parse_path = (
            Path(__file__).resolve().parents[2]
            / "dayz-ui-lab"
            / "dayz_ui_lab"
            / "parse.py"
        )
        if not parse_path.is_file():
            raise ImportError(
                "dayz_ui_lab.parse is required. Keep this tool next to "
                "tools/dayz-ui-lab in the pack tree, or put that directory "
                "on PYTHONPATH."
            )
        spec = importlib.util.spec_from_file_location("dayz_ui_lab.parse", parse_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"could not load layout parser from {parse_path.as_posix()}")
        layout_parse = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = layout_parse
        spec.loader.exec_module(layout_parse)

    _PARSE = layout_parse
    return layout_parse


def build_docs(layout_path: Path) -> list[dict[str, Any]]:
    parse = load_layout_parser()
    out: list[dict[str, Any]] = []
    for viewport in VIEWPORTS:
        doc = parse.parse_file(
            layout_path,
            canvas_width=viewport["width"],
            canvas_height=viewport["height"],
            source_path_override=layout_path.name,
        )
        out.append(
            {
                "label": viewport["label"],
                "width": viewport["width"],
                "height": viewport["height"],
                "doc": doc.to_dict(),
            }
        )
    return out


def build_preview_html(layout_path: Path) -> str:
    docs = build_docs(layout_path)
    return TEMPLATE.replace("__TITLE__", layout_path.name).replace(
        "/*__VIEWPORTS_JSON__*/",
        json.dumps(docs, ensure_ascii=False),
    )


def write_preview(layout_path: Path, out_path: Path) -> Path:
    html = build_preview_html(layout_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dayz-layout-viewer",
        description=(
            "Emit a self-contained HTML preview of a DayZ .layout at four "
            "viewports. Structural approximation; not the engine."
        ),
    )
    parser.add_argument("layout", help="layout path, or a name under --layout-root")
    parser.add_argument("-o", "--out", help="output HTML path; default: <layout>.preview.html")
    parser.add_argument(
        "--layout-root",
        action="append",
        default=[],
        help="directory used to resolve a relative layout name; can be repeated",
    )
    args = parser.parse_args(argv)

    parse = load_layout_parser()
    roots = [Path(value) for value in args.layout_root]
    try:
        layout_path = parse.resolve_layout_path(args.layout, roots)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        html = build_preview_html(layout_path)
    except parse.LayoutSyntaxError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    out_path = Path(args.out) if args.out else layout_path.with_suffix(".preview.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(
        "WROTE "
        + str(out_path)
        + "  ("
        + str(out_path.stat().st_size)
        + " bytes, "
        + str(len(VIEWPORTS))
        + " viewports)"
    )
    return 0
