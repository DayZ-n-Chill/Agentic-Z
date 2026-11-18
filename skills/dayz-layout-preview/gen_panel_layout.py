#!/usr/bin/env python3
"""Parameterized DayZ .layout generator for UI-on-demand panels.

Grammar and attribute set are those of a panel layout that was loaded in
game from $profile: and, for HUD panel chrome only,
skills/_shared/ui/templates/hud_overlay.layout.
All TextWidget `text` values are empty literals; content is injected at
runtime with FindAnyWidget and SetText. No #STR_ keys.

Pure offline: it reads nothing from the P: work drive or DayZ Tools and starts no process,
so it does not call the /dayz-preflight gate. The widget names it writes are
a contract, documented in skills/_shared/ui/templates/panel-contract.md.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Output encoding matches the ladder layout: UTF-8, no BOM, LF.
ENCODING = "utf-8"
NEWLINE = "\n"

KIND_FEED = "feed"
KIND_INFO = "info"
KIND_HUD = "hud"
KINDS = (KIND_FEED, KIND_INFO, KIND_HUD)

# Inner fractions of the ladder layout (header + data rows).
PAD_X = 0.025
PAD_Y = 0.035
TITLE_H = 0.075
GAP_AFTER_TITLE = 0.027
LADDER_ROW_H = 0.075
LADDER_STEP = 0.102
LABEL_W = 0.245
VALUE_X = 0.285
VALUE_W = 0.690

FONT = "gui/fonts/sdf_MetronBook24"
COLOR_TITLE = "0.75 0.82 0.95 1"
COLOR_LABEL = "0.75 0.82 0.95 1"
COLOR_BODY = "1 1 1 1"
STYLE_PANEL = "rover_sim_colorable"

# Panel defaults: feed/info color from LadderPanel; HUD color/size/pos from HudBadge.
DEFAULTS = {
    KIND_FEED: {
        "width": 0.32,
        "height": 0.45,
        "x": 0.02,
        "y": 0.50,
        "priority": 2000,
        "color": "0.025 0.025 0.035 0.985",
        "root": "FeedRoot",
        "panel": "FeedPanel",
    },
    KIND_INFO: {
        "width": 0.28,
        "height": 0.40,
        "x": 0.02,
        "y": 0.04,
        "priority": 2000,
        "color": "0.025 0.025 0.035 0.985",
        "root": "InfoRoot",
        "panel": "InfoPanel",
    },
    KIND_HUD: {
        "width": 0.22,
        "height": 0.10,
        "x": 0.76,
        "y": 0.04,
        "priority": 100,
        "color": "0.12 0.12 0.12 0.90",
        "root": "HudRoot",
        "panel": "HudPanel",
    },
}

SELFTEST_SPECS = (
    (KIND_FEED, 10, "CHAT", "chat_feed.layout"),
    (KIND_INFO, 6, "STATUS", "info_panel.layout"),
    (KIND_HUD, 2, None, "mini_hud.layout"),
)

NAME_RE = re.compile(r'(?m)^\s*name\s+"([^"]*)"\s*$')
TEXT_RE = re.compile(r'(?m)^\s*text\s+"([^"]*)"\s*$')
CLASS_RE = re.compile(r"(?m)^\s*(\w+Class)\s+(\w+)\s*\{")


def fmt_num(value):
    """Format a layout number like the ladder file (0, 1, 0.025, 0.075)."""
    value = round(float(value), 3)
    if value == int(value):
        return str(int(value))
    text = f"{value:.3f}".rstrip("0")
    if text.endswith("."):
        text += "0"
    return text


def fmt_tp(value):
    return f"{round(float(value), 2):.2f}"


def sanitize_comment(text):
    return " ".join(str(text).split())


def has_title_widget(kind, title):
    if kind in (KIND_FEED, KIND_INFO):
        return True
    return title is not None


def row_band(n_rows, titled):
    """Return (title_rect | None, list of (x, y, w, h) row rects) in panel space."""
    inner_w = 1.0 - 2.0 * PAD_X
    y = PAD_Y
    title_rect = None
    if titled:
        title_rect = (PAD_X, y, inner_w, TITLE_H)
        y = y + TITLE_H + GAP_AFTER_TITLE
    available = 1.0 - PAD_Y - y
    if n_rows < 1:
        return title_rect, []
    fill = LADDER_ROW_H / LADDER_STEP
    step = available / float(n_rows)
    row_h = step * fill
    rows = []
    for i in range(n_rows):
        rows.append((PAD_X, y + i * step, inner_w, row_h))
    return title_rect, rows


def text_proportion_for(row_h, panel_height):
    """Keep on-screen glyph near the ladder band (~18 px at 1080p).

    Ladder uses text_proportion 0.30 in a 0.075-of-screen cell. A sub-panel
    shrinks that cell; scale the attribute so the product stays in band.
    """
    on_screen = float(row_h) * float(panel_height)
    if on_screen <= 1e-9:
        return 0.30
    scaled = 0.30 * LADDER_ROW_H / on_screen
    if scaled < 0.20:
        return 0.20
    if scaled > 0.85:
        return 0.85
    return scaled


def emit_text_widget(name, x, y, w, h, color, proportion):
    return [
        f"            TextWidgetClass {name} {{",
        f'                name "{name}"',
        "                ignorepointer 1",
        f"                position {fmt_num(x)} {fmt_num(y)}",
        f"                size {fmt_num(w)} {fmt_num(h)}",
        "                hexactpos 0",
        "                vexactpos 0",
        "                hexactsize 0",
        "                vexactsize 0",
        '                text ""',
        f'                font "{FONT}"',
        f'                "text color" {color}',
        '                "text halign" left',
        '                "text valign" center',
        f"                text_proportion {fmt_tp(proportion)}",
        "            }",
    ]


def generate_layout(kind, rows, title=None, width=None, height=None, x=None, y=None):
    if kind not in DEFAULTS:
        raise ValueError(f"unknown kind: {kind}")
    if int(rows) < 1:
        raise ValueError("--rows must be >= 1")
    rows = int(rows)
    cfg = DEFAULTS[kind]
    width = cfg["width"] if width is None else float(width)
    height = cfg["height"] if height is None else float(height)
    x = cfg["x"] if x is None else float(x)
    y = cfg["y"] if y is None else float(y)
    titled = has_title_widget(kind, title)
    title_rect, row_rects = row_band(rows, titled)

    title_bit = ""
    if title is not None:
        title_bit = f" title={sanitize_comment(title)}"
    lines = [
        f"// Generated by gen_panel_layout.py. kind={kind} rows={rows}{title_bit}.",
        "// Texts start empty; fill at runtime with FindAnyWidget and SetText.",
        f"FrameWidgetClass {cfg['root']} {{",
        f'    name "{cfg["root"]}"',
        "    ignorepointer 1",
        "    position 0 0",
        "    size 1 1",
        "    hexactpos 0",
        "    vexactpos 0",
        "    hexactsize 0",
        "    vexactsize 0",
        f"    priority {cfg['priority']}",
        "    {",
        f"        PanelWidgetClass {cfg['panel']} {{",
        f'            name "{cfg["panel"]}"',
    ]
    if kind == KIND_HUD:
        lines.append("            ignorepointer 1")
    lines.extend(
        [
            f"            color {cfg['color']}",
            f"            position {fmt_num(x)} {fmt_num(y)}",
            f"            size {fmt_num(width)} {fmt_num(height)}",
        ]
    )
    if kind == KIND_HUD:
        # HudBadge in hud_overlay.layout: left/top + fractional position.
        lines.extend(
            [
                "            halign left",
                "            valign top",
            ]
        )
    lines.extend(
        [
            "            hexactpos 0",
            "            vexactpos 0",
            "            hexactsize 0",
            "            vexactsize 0",
            f"            style {STYLE_PANEL}",
            "            {",
        ]
    )

    if title_rect is not None:
        tx, ty, tw, th = title_rect
        tp = text_proportion_for(th, height)
        lines.extend(emit_text_widget("TitleText", tx, ty, tw, th, COLOR_TITLE, tp))

    for i, (rx, ry, rw, rh) in enumerate(row_rects):
        tp = text_proportion_for(rh, height)
        if kind == KIND_INFO:
            lines.extend(
                emit_text_widget(
                    f"Label{i}", rx, ry, LABEL_W, rh, COLOR_LABEL, tp
                )
            )
            lines.extend(
                emit_text_widget(
                    f"Value{i}", VALUE_X, ry, VALUE_W, rh, COLOR_BODY, tp
                )
            )
        else:
            lines.extend(
                emit_text_widget(
                    f"FeedLine{i}", rx, ry, rw, rh, COLOR_BODY, tp
                )
            )

    lines.extend(
        [
            "            }",
            "        }",
            "    }",
            "}",
        ]
    )
    return NEWLINE.join(lines) + NEWLINE


def write_layout(path, text):
    path = Path(path)
    if "\r" in text:
        raise ValueError("layout text contains CR")
    if text.startswith("\ufeff"):
        raise ValueError("layout text contains BOM")
    data = text.encode(ENCODING)
    path.write_bytes(data)
    return len(data)


def declared_row_names(kind, rows, titled):
    names = []
    if titled:
        names.append("TitleText")
    for i in range(rows):
        if kind == KIND_INFO:
            names.append(f"Label{i}")
            names.append(f"Value{i}")
        else:
            names.append(f"FeedLine{i}")
    return names


def verify_layout_text(text, kind, rows, titled):
    errors = []
    if text.startswith("\ufeff") or (len(text) >= 1 and text[0] == "\ufeff"):
        errors.append("UTF-8 BOM present")
    if "\r" in text:
        errors.append("CR present (expected LF-only)")
    if "#STR_" in text:
        errors.append("#STR_ key present (forbidden for $profile: dynamic text)")

    opens = text.count("{")
    closes = text.count("}")
    if opens != closes:
        errors.append(f"brace imbalance: {{={opens} }}={closes}")

    names = NAME_RE.findall(text)
    if len(names) != len(set(names)):
        dupes = sorted({n for n in names if names.count(n) > 1})
        errors.append("duplicate name: " + ", ".join(dupes))

    class_names = [m[1] for m in CLASS_RE.findall(text)]
    for widget_name in names:
        if names.count(widget_name) != 1:
            errors.append(f'name "{widget_name}" count={names.count(widget_name)}')
        if widget_name not in class_names:
            errors.append(f'name "{widget_name}" has no matching Class identifier')

    expected = declared_row_names(kind, rows, titled)
    for widget_name in expected:
        count = names.count(widget_name)
        if count != 1:
            errors.append(f'declared {widget_name} appears {count} time(s)')

    if kind in (KIND_FEED, KIND_HUD):
        extra_feed = [
            n for n in names if re.fullmatch(r"FeedLine\d+", n) and n not in expected
        ]
        if extra_feed:
            errors.append("unexpected FeedLine: " + ", ".join(extra_feed))
    if kind == KIND_INFO:
        extra_val = [
            n for n in names if re.fullmatch(r"Value\d+", n) and n not in expected
        ]
        extra_lab = [
            n for n in names if re.fullmatch(r"Label\d+", n) and n not in expected
        ]
        if extra_val:
            errors.append("unexpected Value: " + ", ".join(extra_val))
        if extra_lab:
            errors.append("unexpected Label: " + ", ".join(extra_lab))

    texts = TEXT_RE.findall(text)
    if not texts:
        errors.append("no text attributes")
    for value in texts:
        if value != "":
            errors.append(f'non-empty text "{value}"')

    cfg = DEFAULTS[kind]
    if cfg["root"] not in names:
        errors.append(f'missing root name {cfg["root"]}')
    if cfg["panel"] not in names:
        errors.append(f'missing panel name {cfg["panel"]}')
    return errors


def run_selftest(out_dir):
    out_dir = Path(out_dir)
    failures = []
    for kind, rows, title, filename in SELFTEST_SPECS:
        path = out_dir / filename
        titled = has_title_widget(kind, title)
        text = generate_layout(kind, rows, title=title)
        write_layout(path, text)
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            failures.append(f"{filename}: BOM on disk")
        if b"\r" in raw:
            failures.append(f"{filename}: CR on disk")
        decoded = raw.decode(ENCODING)
        for err in verify_layout_text(decoded, kind, rows, titled):
            failures.append(f"{filename}: {err}")
        expected = declared_row_names(kind, rows, titled)
        names = NAME_RE.findall(decoded)
        for widget_name in expected:
            if widget_name.startswith("FeedLine") or widget_name.startswith("Value"):
                if names.count(widget_name) != 1:
                    failures.append(
                        f"{filename}: {widget_name} count={names.count(widget_name)}"
                    )
    if failures:
        sys.stdout.write("SELFTEST FAIL" + NEWLINE)
        for item in failures:
            sys.stdout.write(item + NEWLINE)
        return 1
    sys.stdout.write("SELFTEST PASS" + NEWLINE)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Generate a DayZ .layout panel loaded from $profile: and filled with SetText.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            '  python gen_panel_layout.py feed --rows 10 --title "CHAT" --out chat_feed.layout\n'
            '  python gen_panel_layout.py info --rows 6 --title "STATUS" --out info_panel.layout\n'
            "  python gen_panel_layout.py hud --rows 2 --out mini_hud.layout\n"
            "  python gen_panel_layout.py --self-test\n"
        ),
    )
    parser.add_argument("kind", nargs="?", choices=KINDS, help="panel kind")
    parser.add_argument("--rows", type=int, help="number of data rows")
    parser.add_argument("--title", default=None, help="documentary title (widget stays empty)")
    parser.add_argument("--out", help="output .layout path")
    parser.add_argument("--width", type=float, help="panel width (fraction of screen)")
    parser.add_argument("--height", type=float, help="panel height (fraction of screen)")
    parser.add_argument("--x", type=float, help="panel left (fraction of screen)")
    parser.add_argument("--y", type=float, help="panel top (fraction of screen)")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="write the three example layouts and verify them",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    here = Path(__file__).resolve().parent
    if args.self_test:
        return run_selftest(here)
    if args.kind is None:
        parser.error("kind is required unless --self-test")
    if args.rows is None:
        parser.error("--rows is required")
    if not args.out:
        parser.error("--out is required")
    text = generate_layout(
        args.kind,
        args.rows,
        title=args.title,
        width=args.width,
        height=args.height,
        x=args.x,
        y=args.y,
    )
    write_layout(args.out, text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
