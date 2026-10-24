"""dayz-layout-preview: Render a DayZ .layout to approximate PNGs at several screen sizes.

Parses the brace property format (not XML), works out every widget's box from
`position`, `size`, the four exact toggles, `halign`/`valign` and `scaled`, lays
out grid and wrap spacer children, and draws boxes, text and image placeholders
with Pillow. It also reports what a person should look at: widgets that leave the
screen, boxes with no area, and widgets missing an exact toggle.

This is a preview, not the game renderer. See SKILL.md for what it approximates.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # reported with an install hint in main(); parsing and layout don't need it
    Image = ImageDraw = ImageFont = None

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "

REQUIREMENTS = Path(__file__).resolve().parent / "requirements.txt"
# This file is <root>\.claude\skills\dayz-layout-preview\layout_preview.py. resolve()
# follows the /sync-skills link, so this is the clone even when run from a home skills folder.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = PROJECT_ROOT / "output" / "layout-preview"
# Vanilla layouts live on the DayZ work drive. A missing file there usually means the drive is not mounted.
P_DRIVE = Path("P:/")
DEFAULT_SIZES = [(1280, 720), (1920, 1080), (2560, 1440), (3440, 1440)]
# `scaled 1` grows exact pixel values with the screen height. 1080 is the
# reference height this preview assumes; the game's own scale may differ.
SCALE_REF_HEIGHT = 1080
EXACT_KEYS = ("hexactpos", "vexactpos", "hexactsize", "vexactsize")
# Keys that take exactly one word value, so a one-line widget such as
# `TextWidgetClass t { halign right_ref text "Hi" }` splits correctly.
ONE_WORD_KEYS = {
    "halign", "valign", "style", "fixaspect", "mode", "font", "text", "image0", "scriptclass",
    "content_halign", "content_valign", '"text halign"', '"text valign"', '"stretch mode"', '"clamp mode"',
}
_TOKEN = re.compile(r'"[^"\n]*"|[{}]|[^\s{}"]+')
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?$")


class LayoutError(ValueError):
    pass


@dataclass
class Widget:
    cls: str
    name: str
    line: int
    props: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    @property
    def is_widget(self) -> bool:
        return self.cls.endswith("WidgetClass")

    def get(self, key: str, default=None):
        return self.props.get(key, default)

    def num(self, key: str, index: int = 0, default: float = 0.0) -> float:
        values = self.props.get(key)
        try:
            return float(values[index])
        except (TypeError, IndexError, ValueError):
            return default

    def word(self, key: str, default: str = "") -> str:
        values = self.props.get(key)
        return values[0].strip('"') if values else default


# ------------------------------------------------------------------ parsing

def parse(text: str) -> Widget:
    """Parse layout text into its root widget. Raises LayoutError on broken structure."""
    if text.lstrip("﻿ \t\r\n").startswith("<"):
        raise LayoutError("this is XML; DayZ .layout files use the brace property format")
    root = Widget("", "", 0)  # top level acts like a children block
    stack: list[tuple[str, Widget]] = [("children", root)]
    for lineno, raw in enumerate(text.splitlines(), 1):
        if raw.strip().startswith("//"):
            continue
        tokens = _TOKEN.findall(raw)
        words: list[str] = []
        for tok in tokens + ["\n"]:
            kind, owner = stack[-1]
            if tok == "{":
                if kind == "widget" and not words:
                    stack.append(("children", owner))
                    continue
                # A header in a property block is a child outside its '{ }' block; the edit
                # hook reports that, the preview still draws it as a child.
                if not words or len(words) > 2:
                    raise LayoutError(f"line {lineno}: a block must open as '<Type>Class <name> {{'")
                child = Widget(words[0], words[1] if len(words) > 1 else "", lineno)
                owner.children.append(child)
                stack.append(("widget", child))
                words = []
            elif tok == "}":
                if kind == "widget":
                    _assign(owner, words)
                words = []
                if len(stack) == 1:
                    raise LayoutError(f"line {lineno}: '}}' with no open block")
                stack.pop()
            elif tok == "\n":
                if kind == "widget":
                    _assign(owner, words)
                words = []  # a widget header always ends its line with '{'
            else:
                words.append(tok)
    if len(stack) > 1:
        raise LayoutError(f"block '{stack[-1][1].name}' opened on line {stack[-1][1].line} is never closed")
    widgets = [w for w in root.children if w.is_widget]
    if not widgets:
        raise LayoutError("no root widget; a .layout starts with '<Type>WidgetClass <name> {'")
    return widgets[0]


def _assign(widget: Widget, words: list[str]) -> None:
    """Split one line's words into properties. Most lines hold one key and its values."""
    key: Optional[str] = None
    for tok in words:
        values = widget.props.get(key) if key else None
        starts_key = key is None or bool(values) and (
            key in ONE_WORD_KEYS or bool(_NUMBER.match(values[-1])) and not _NUMBER.match(tok))
        if starts_key:
            key = tok
            widget.props[key] = []
        else:
            values.append(tok)


# ------------------------------------------------------------------- layout

@dataclass
class Box:
    widget: Widget
    x: float
    y: float
    w: float
    h: float
    depth: int
    hidden: bool = False

    def as_dict(self) -> dict:
        return {"name": self.widget.name, "class": self.widget.cls, "line": self.widget.line,
                "x": round(self.x), "y": round(self.y), "w": round(self.w), "h": round(self.h),
                "depth": self.depth, "hidden": self.hidden}


def _scale(widget: Widget, screen_h: int) -> float:
    return screen_h / SCALE_REF_HEIGHT if widget.word("scaled") == "1" else 1.0


def _flag(widget: Widget, key: str) -> bool:
    return widget.word(key, "0") == "1"


def widget_size(widget: Widget, pw: float, ph: float, screen_h: int) -> tuple[float, float]:
    k = _scale(widget, screen_h)
    sw = widget.num("size", 0, 1.0)
    sh = widget.num("size", 1, 1.0)
    w = sw * k if _flag(widget, "hexactsize") else sw * pw
    h = sh * k if _flag(widget, "vexactsize") else sh * ph
    return w, h


def place(widget: Widget, px: float, py: float, pw: float, ph: float, screen_h: int,
          use_position: bool = True) -> tuple[float, float, float, float]:
    """The widget's box inside a parent box, from position, size, toggles and anchors."""
    w, h = widget_size(widget, pw, ph, screen_h)
    k = _scale(widget, screen_h)
    ox = oy = 0.0
    if use_position:
        ox = widget.num("position", 0) * (k if _flag(widget, "hexactpos") else pw)
        oy = widget.num("position", 1) * (k if _flag(widget, "vexactpos") else ph)
    halign = widget.word("halign", "left")
    valign = widget.word("valign", "top")
    if halign.startswith("right"):
        x = px + pw - w - ox
    elif halign.startswith("center"):
        x = px + (pw - w) / 2 + ox
    else:
        x = px + ox
    if valign.startswith("bottom"):
        y = py + ph - h - oy
    elif valign.startswith("center"):
        y = py + (ph - h) / 2 + oy
    else:
        y = py + oy
    return x, y, w, h


def layout(root: Widget, screen_w: int, screen_h: int, show_hidden: bool = False) -> list[Box]:
    """Every widget's box on a screen of this size, parents before children, children by priority."""
    boxes: list[Box] = []

    def visit(widget: Widget, rect: tuple, depth: int, hidden: bool, *, in_cell: bool = False,
              fixed: Optional[tuple] = None) -> None:
        hidden = hidden or widget.word("visible", "1") == "0"
        if hidden and not show_hidden:
            return
        x, y, w, h = fixed if fixed else place(widget, *rect, screen_h, use_position=not in_cell)
        boxes.append(Box(widget, x, y, w, h, depth, hidden))
        kids = sorted((c for c in widget.children if c.is_widget), key=lambda c: c.num("priority"))
        inner = (x, y, w, h)
        if widget.cls == "GridSpacerWidgetClass":
            for kid, cell in zip(kids, _grid_cells(widget, kids, inner)):
                visit(kid, cell, depth + 1, hidden, in_cell=True)
        elif widget.cls == "WrapSpacerWidgetClass":
            for kid, spot in zip(kids, _wrap_spots(widget, kids, inner, screen_h)):
                visit(kid, inner, depth + 1, hidden, fixed=spot)
        else:
            for kid in kids:
                visit(kid, inner, depth + 1, hidden)

    visit(root, (0.0, 0.0, float(screen_w), float(screen_h)), 0, False)
    return boxes


def _grid_cells(spacer: Widget, kids: list, rect: tuple) -> list[tuple]:
    """Grid spacer: shown children fill Columns x Rows cells in order. A hidden child gets
    the next cell too but does not use it up."""
    x, y, w, h = rect
    pad = spacer.num("Padding")
    gap = spacer.num("Margin")
    shown = sum(1 for k in kids if k.word("visible", "1") != "0")
    cols = max(1, int(spacer.num("Columns", 0, 1)))
    rows = max(1, int(spacer.num("Rows", 0, 1)), math.ceil(shown / cols))
    cw = (w - 2 * pad - gap * (cols - 1)) / cols
    ch = (h - 2 * pad - gap * (rows - 1)) / rows
    cells, i = [], 0
    for kid in kids:
        col, row = i % cols, i // cols
        cells.append((x + pad + col * (cw + gap), y + pad + row * (ch + gap), cw, ch))
        if kid.word("visible", "1") != "0":
            i += 1
    return cells


def _wrap_spots(spacer: Widget, kids: list, rect: tuple, screen_h: int) -> list[tuple]:
    """Wrap spacer: shown children flow left to right and wrap at the spacer's width."""
    x, y, w, h = rect
    pad = spacer.num("Padding")
    gap = spacer.num("Margin")
    cx, cy, line_h = x + pad, y + pad, 0.0
    spots = []
    for kid in kids:
        kw, kh = widget_size(kid, w - 2 * pad, h - 2 * pad, screen_h)
        if kid.word("visible", "1") == "0":
            spots.append((cx, cy, kw, kh))
            continue
        if cx > x + pad and cx + kw > x + w - pad:
            cx, cy, line_h = x + pad, cy + line_h + gap, 0.0
        spots.append((cx, cy, kw, kh))
        cx += kw + gap
        line_h = max(line_h, kh)
    return spots


# ------------------------------------------------------------------- checks

def findings(root: Widget, boxes_by_size: dict) -> list[dict]:
    """What a person should look at, from the boxes at every size."""
    out: list[dict] = []

    def walk(widget: Widget) -> None:
        missing = [k for k in EXACT_KEYS if k not in widget.props]
        if widget.is_widget and missing and ("size" in widget.props or "position" in widget.props):
            out.append({"severity": "warning", "rule": "missing-toggle", "widget": widget.name, "line": widget.line,
                        "message": f"{widget.name} has no {', '.join(missing)}; the preview reads it as 0 (relative)"})
        for child in widget.children:
            walk(child)

    walk(root)
    # One finding per widget and rule, naming every screen size it happens at.
    seen: dict = {}
    for (sw, sh), boxes in boxes_by_size.items():
        for b in boxes:
            if b.hidden:
                continue
            if b.w <= 0.5 or b.h <= 0.5:
                rule, what = "no-area", "has no area"
            elif b.x < -0.5 or b.y < -0.5 or b.x + b.w > sw + 0.5 or b.y + b.h > sh + 0.5:
                rule, what = "off-screen", "leaves the screen"
            else:
                continue
            key = (rule, b.widget.line, b.widget.name)
            if key not in seen:
                seen[key] = {"severity": "warning", "rule": rule, "widget": b.widget.name,
                             "line": b.widget.line, "sizes": [], "what": what}
                out.append(seen[key])
            seen[key]["sizes"].append(f"{sw}x{sh}")
    for f in seen.values():
        f["message"] = f"{f['widget']} {f.pop('what')} at {', '.join(f['sizes'])}"
    return out


# ------------------------------------------------------------------ drawing

OUTLINE = {
    "FrameWidgetClass": (120, 120, 120),
    "PanelWidgetClass": (90, 160, 220),
    "WindowWidgetClass": (90, 160, 220),
    "ImageWidgetClass": (220, 170, 60),
    "ButtonWidgetClass": (110, 200, 120),
    "GridSpacerWidgetClass": (170, 110, 210),
    "WrapSpacerWidgetClass": (170, 110, 210),
}
TEXT_CLASSES = {"TextWidgetClass", "RichTextWidgetClass", "MultilineTextWidgetClass", "ButtonWidgetClass",
                "EditBoxWidgetClass", "MultilineEditBoxWidgetClass"}


def _rgba(widget: Widget, key: str) -> Optional[tuple]:
    values = widget.props.get(key)
    if not values or len(values) < 3:
        return None
    try:
        parts = [float(v) for v in values[:4]] + [1.0]
    except ValueError:
        return None
    return tuple(max(0, min(255, round(p * 255))) for p in parts[:4])


def _font(px: float):
    return ImageFont.load_default(size=max(8, round(px)))


def render(screen_w: int, screen_h: int, boxes: list[Box], labels: bool = True):
    """An RGBA image of the boxes. Panels fill with their color; images get a crossed placeholder."""
    img = Image.new("RGBA", (screen_w, screen_h), (28, 30, 34, 255))
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    label_font = _font(11)
    for b in boxes:
        w = b.widget
        x0, y0 = round(b.x), round(b.y)
        x1, y1 = round(b.x + b.w) - 1, round(b.y + b.h) - 1
        if x1 < x0 or y1 < y0:
            continue
        outline = OUTLINE.get(w.cls, (200, 200, 200)) + ((90,) if b.hidden else (255,))
        fill = _rgba(w, "color")
        if w.cls in ("PanelWidgetClass", "WindowWidgetClass") and fill:
            draw.rectangle((x0, y0, x1, y1), fill=fill)
        if w.cls == "ImageWidgetClass":
            tint = fill or (255, 255, 255, 255)
            draw.rectangle((x0, y0, x1, y1), fill=tint[:3] + (min(tint[3], 60),))
            draw.line((x0, y0, x1, y1), fill=outline, width=1)
            draw.line((x0, y1, x1, y0), fill=outline, width=1)
        draw.rectangle((x0, y0, x1, y1), outline=outline, width=1)
        text = w.word("text")
        if w.cls in TEXT_CLASSES and text.strip():
            if w.word('"exact text"') == "1" and '"exact text size"' in w.props:
                px = w.num('"exact text size"', 0, 16) * _scale(w, screen_h)
            else:
                px = min(b.h * 0.7, 32)
            color = _rgba(w, '"text color"') or (235, 235, 235, 255)
            font = _font(px)
            tw = draw.textlength(text, font=font)
            button = w.cls == "ButtonWidgetClass"
            halign = w.word('"text halign"', "center" if button else "left")
            valign = w.word('"text valign"', "center" if button else "top")
            bw, bh = x1 - x0 + 1, y1 - y0 + 1
            tx = (bw - tw) / 2 if halign == "center" else bw - tw if halign == "right" else 2
            ty = (bh - px) / 2 if valign == "center" else bh - px if valign == "bottom" else 0
            # Draw on a layer the size of the box so text is clipped to it, as in game.
            layer = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            ImageDraw.Draw(layer).text((tx, ty), text, fill=color, font=font)
            overlay.alpha_composite(layer, dest=(max(x0, 0), max(y0, 0)), source=(max(-x0, 0), max(-y0, 0)))
        elif labels and w.cls == "ImageWidgetClass" and w.word("image0") and b.w >= 60:
            draw.text((x0 + 3, y0 + 3), w.word("image0"), fill=outline, font=label_font)
        if labels and b.w >= 40 and b.h >= 14:
            draw.text((x0 + 3, y1 - 13), w.name, fill=outline[:3] + (170,), font=label_font)
    return Image.alpha_composite(img, overlay)


# ---------------------------------------------------------------------- CLI

def parse_sizes(value: str) -> list[tuple[int, int]]:
    sizes = []
    for part in value.split(","):
        m = re.fullmatch(r"\s*(\d{2,5})[xX](\d{2,5})\s*", part)
        if not m:
            raise argparse.ArgumentTypeError(f"'{part}' is not WIDTHxHEIGHT, for example 1920x1080")
        sizes.append((int(m.group(1)), int(m.group(2))))
    return sizes


def png_names(paths: list) -> dict:
    """A unique PNG base name per layout path: the file stem, with parent folder names
    prefixed (`parent_stem`, then `grand_parent_stem`) only where two different
    layouts in the same run would otherwise share a name."""
    resolved = {p: p.resolve() for p in paths}
    depth = dict.fromkeys(paths, 0)

    def name(p: Path) -> str:
        folders = resolved[p].parent.parts
        return "_".join(folders[len(folders) - depth[p]:] + (resolved[p].stem,)) if depth[p] else resolved[p].stem

    while True:
        owners: dict = {}
        for p in paths:
            owners.setdefault(name(p), set()).add(resolved[p])
        clashing = [p for p in paths
                    if len(owners[name(p)]) > 1 and depth[p] < len(resolved[p].parent.parts)]
        if not clashing:
            return {p: name(p) for p in paths}
        for p in clashing:
            depth[p] += 1


def inside_mod_workspace(out_dir: Path) -> bool:
    """True when out_dir is workspace\\<Mod>\\ or below it, where PNGs would be packed into the PBO.
    resolve() follows the P:\\<ModName>\\ junction, so that route is caught too."""
    try:
        rel = out_dir.resolve().relative_to((PROJECT_ROOT / "workspace").resolve())
    except ValueError:
        return False
    return len(rel.parts) >= 1


def on_unmounted_p(path: Path) -> bool:
    """True when path is on P:\\ and P:\\ is not mounted, so the fix is /dayz-workdrive, not the path."""
    return path.drive.upper() == P_DRIVE.drive.upper() and not P_DRIVE.exists()


def preview(path: Path, sizes: list, out_dir: Optional[Path], show_hidden: bool = False,
            labels: bool = True, name: Optional[str] = None) -> dict:
    """Lay out (and draw, when out_dir is given) one layout at every size. Returns the report.

    PNGs are named <name>_<W>x<H>.png; name defaults to the layout's file stem."""
    root = parse(path.read_text(encoding="utf-8", errors="replace"))
    boxes_by_size = {size: layout(root, *size, show_hidden=show_hidden) for size in sizes}
    report = {"layout": str(path), "root": root.name, "sizes": [], "findings": findings(root, boxes_by_size)}
    for (sw, sh), boxes in boxes_by_size.items():
        entry = {"size": f"{sw}x{sh}", "widgets": [b.as_dict() for b in boxes]}
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            png = out_dir / f"{name or path.stem}_{sw}x{sh}.png"
            render(sw, sh, boxes, labels).convert("RGB").save(png)
            entry["png"] = str(png)
        report["sizes"].append(entry)
    return report


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Render a DayZ .layout to approximate PNGs at several screen sizes.")
    ap.add_argument("layouts", nargs="+", type=Path, help=".layout file(s) to preview")
    ap.add_argument("--sizes", type=parse_sizes, default=DEFAULT_SIZES,
                    help="Comma separated WIDTHxHEIGHT list (default 1280x720,1920x1080,2560x1440,3440x1440)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help="Folder for the PNGs (default output/layout-preview under the project root)")
    ap.add_argument("--show-hidden", action="store_true", help="Also draw widgets with visible 0, faded")
    ap.add_argument("--no-labels", action="store_true", help="Do not print widget names on the boxes")
    ap.add_argument("--json", action="store_true",
                    help="Print the full report (every widget box) as JSON on stdout; text lines go to stderr")
    args = ap.parse_args(argv)
    # With --json, stdout carries only the JSON so it can be piped straight into a parser.
    log = sys.stderr if args.json else sys.stdout

    if Image is None:
        print(f"{FAIL}Pillow is not installed.\n       Install it: python -m pip install -r \"{REQUIREMENTS}\"",
              file=log)
        return 2
    if inside_mod_workspace(args.out):
        print(f"{FAIL}{args.out}: is inside a mod under workspace\\, so the PNGs would be packed into its PBO.\n"
              f"       Leave --out off to use {DEFAULT_OUT}, or pick a folder outside workspace\\.", file=log)
        return 1
    reports, failed = [], 0
    names = png_names(args.layouts)
    for path in args.layouts:
        if not path.is_file():
            if on_unmounted_p(path):
                print(f"{FAIL}{path}: P:\\ is not mounted, so vanilla files can't be read. Run /dayz-workdrive.",
                      file=log)
            else:
                print(f"{FAIL}{path}: no such file", file=log)
            failed += 1
            continue
        try:
            report = preview(path, args.sizes, args.out, args.show_hidden, not args.no_labels, names[path])
        except LayoutError as e:
            print(f"{FAIL}{path}: {e}", file=log)
            failed += 1
            continue
        reports.append(report)
        for entry in report["sizes"]:
            print(f"{OK}{entry['png']}  ({len(entry['widgets'])} widgets)", file=log)
        for f in report["findings"]:
            print(f"{WARN}{path.name}:{f['line']} {f['rule']}: {f['message']}", file=log)
    if args.json:
        print(json.dumps(reports, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
