from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


TOOL_DIR = Path(__file__).resolve().parents[1]
UI_LAB_DIR = Path(__file__).resolve().parents[2] / "dayz-ui-lab"
for path in (TOOL_DIR, UI_LAB_DIR):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from dayz_layout_viewer import viewer  # noqa: E402


FIXTURE = TOOL_DIR / "tests" / "fixtures" / "visible-zero.layout"

EXPECTED_VIEWPORTS = [
    ("1080p (16:9)", 1920, 1080),
    ("1440p (16:9)", 2560, 1440),
    ("Ultrawide (21:9)", 3440, 1440),
    ("720p (16:9)", 1280, 720),
]


def viewports_from_html(html: str) -> list[dict[str, Any]]:
    marker = "var VIEWPORTS = "
    start = html.index(marker) + len(marker)
    docs, _consumed = json.JSONDecoder().raw_decode(html[start:])
    return docs


def flatten(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for node in nodes:
        result.append(node)
        result.extend(flatten(node.get("children") or []))
    return result


def widget_named(docs: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for entry in docs:
        for node in flatten(entry["doc"]["roots"]):
            if node.get("name") == name:
                found.append(node)
    return found


class LayoutViewerTests(unittest.TestCase):
    def test_emits_html_for_fixture(self) -> None:
        html = viewer.build_preview_html(FIXTURE)
        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertIn("DayZ layout preview", html)
        self.assertIn(FIXTURE.name, html)
        self.assertNotIn("\\Users\\", html)
        docs = viewports_from_html(html)
        hidden = widget_named(docs, "HiddenLabel")
        self.assertEqual(len(hidden), len(EXPECTED_VIEWPORTS))
        self.assertEqual(hidden[0]["attrs"]["text"], ["hidden-by-flag"])
        self.assertEqual(hidden[0]["attrs"]["color"], [1, 0, 0, 1])
        icon = widget_named(docs, "Icon")
        self.assertTrue(icon[0]["attrs"]["image0"][0].startswith("#(argb"))

    def test_four_viewports(self) -> None:
        html = viewer.build_preview_html(FIXTURE)
        docs = viewports_from_html(html)
        self.assertEqual(len(docs), 4)
        self.assertEqual(len(viewer.VIEWPORTS), 4)
        actual = [(entry["label"], entry["width"], entry["height"]) for entry in docs]
        self.assertEqual(actual, EXPECTED_VIEWPORTS)
        for label, width, height in EXPECTED_VIEWPORTS:
            self.assertIn(label, html)
            canvas = next(entry["doc"]["canvas"] for entry in docs if entry["label"] == label)
            self.assertEqual(canvas, {"width": width, "height": height})

    def test_visible_zero_is_not_shown(self) -> None:
        """v1 used `int(attr or 1)`, which turns authored 0 into 1."""
        html = viewer.build_preview_html(FIXTURE)
        self.assertIn(".hidden-w{display:none}", html)
        self.assertIn("g.visible?'':' hidden-w'", html)
        self.assertNotIn("or 1", viewer.build_preview_html.__code__.co_consts or ())
        source = (TOOL_DIR / "dayz_layout_viewer" / "viewer.py").read_text(encoding="utf-8")
        template = (TOOL_DIR / "dayz_layout_viewer" / "html_template.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("attr or 1", source)
        self.assertNotIn("or 1", source)
        self.assertNotIn("|| 1", template)
        self.assertNotIn("||1", template)

        docs = viewports_from_html(html)
        hidden_nodes = widget_named(docs, "HiddenLabel")
        shown_nodes = widget_named(docs, "ShownLabel")
        self.assertEqual(len(hidden_nodes), 4)
        self.assertEqual(len(shown_nodes), 4)
        for node in hidden_nodes:
            visible = node["geometry"]["visible"]
            self.assertIs(visible, False)
            self.assertNotEqual(visible, 1)
            self.assertEqual(node["attrs"]["visible"], [0])
        for node in shown_nodes:
            self.assertIs(node["geometry"]["visible"], True)

    def test_cli_writes_preview_html(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "out.preview.html"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = viewer.main([str(FIXTURE), "-o", str(out_path)])
            self.assertEqual(code, 0)
            self.assertTrue(out_path.is_file())
            html = out_path.read_text(encoding="utf-8")
            self.assertIn("var VIEWPORTS = ", html)
            self.assertIn("WROTE ", stdout.getvalue())
            self.assertIn("4 viewports", stdout.getvalue())
            self.assertNotIn(str(FIXTURE.resolve()), html)
