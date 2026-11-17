from __future__ import annotations

import importlib.util
import inspect
import json
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "dayz_ui_lab" / "parse.py"
SPEC = importlib.util.spec_from_file_location("dayz_layout_phase1_parse", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
parse = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = parse
SPEC.loader.exec_module(parse)


class Phase1ParserTests(unittest.TestCase):
    def test_multiroot_bom_block_comments_and_float_edges(self) -> None:
        text = """\ufeff/* block comment */
FrameWidgetClass Root {
    position .5 1.
    size 1 .25
    visible 0
    {
        TextWidgetClass Label {
            scriptclass "ViewBinding"
            "text halign" center
            text "Hello"
            {
                ScriptParamsClass {
                    Binding_Name "HeaderTitle"
                }
            }
        }
    }
}
FrameWidgetClass Other {
    {
    }
}
"""
        doc = parse.parse_text(text, source_path="fixture.layout", canvas_width=200, canvas_height=100)
        data = doc.to_dict()

        self.assertEqual(data["stats"]["rootCount"], 2)
        self.assertEqual(data["stats"]["widgetCount"], 3)
        self.assertEqual(data["stats"]["geometryWidgetCount"], 3)
        self.assertEqual(data["stats"]["renderedWidgetCount"], 1)
        self.assertEqual(data["stats"]["visualWidgetCount"], 1)
        self.assertEqual(data["stats"]["metadataCount"], 1)
        self.assertEqual(data["roots"][0]["geometry"]["raw"]["position"], [0.5, 1.0])
        self.assertFalse(data["roots"][0]["geometry"]["visible"])
        label = data["roots"][0]["children"][0]
        self.assertEqual(label["bindingName"], "HeaderTitle")
        self.assertEqual(label["attrs"]["text halign"], ["center"])

    def test_layout_json_snapshot_shape(self) -> None:
        text = """FrameWidgetClass Root {
    position 0 0
    size 100 50
    hexactpos 1
    vexactpos 1
    hexactsize 1
    vexactsize 1
    {
    }
}
"""
        doc = parse.parse_text(text, source_path="snapshot.layout", canvas_width=200, canvas_height=100)
        actual = json.loads(doc.to_json())
        expected = {
            "schemaVersion": 1,
            "generator": "renderer/parse.py phase1",
            "source": {"path": "snapshot.layout"},
            "canvas": {"width": 200, "height": 100},
            "renderState": {"mode": "raw-layout"},
            "stats": {
                "rootCount": 1,
                "nodeCount": 1,
                "widgetCount": 1,
                "geometryWidgetCount": 1,
                "renderedWidgetCount": 0,
                "visualWidgetCount": 0,
                "metadataCount": 0,
            },
            "roots": [
                {
                    "class": "FrameWidgetClass",
                    "name": "Root",
                    "source": {"line": 1, "column": 1},
                    "isMetadata": False,
                    "attrs": {
                        "position": [0, 0],
                        "size": [100, 50],
                        "hexactpos": [1],
                        "vexactpos": [1],
                        "hexactsize": [1],
                        "vexactsize": [1],
                    },
                    "children": [],
                    "geometry": {
                        "status": "resolved",
                        "notes": [],
                        "anchor": {"horizontal": "left_ref", "vertical": "top_ref"},
                        "flags": {
                            "hexactpos": 1,
                            "vexactpos": 1,
                            "hexactsize": 1,
                            "vexactsize": 1,
                        },
                        "position": {"x": 0.0, "y": 0.0},
                        "offset": {"x": 0.0, "y": 0.0},
                        "size": {"width": 100.0, "height": 50.0},
                        "raw": {"position": [0.0, 0.0], "size": [100.0, 50.0]},
                        "visible": True,
                        "ignorePointer": False,
                        "clipChildren": False,
                        "alpha": None,
                    },
                }
            ],
        }
        self.assertEqual(actual, expected)

    def test_error_reports_line_and_column(self) -> None:
        text = """FrameWidgetClass Root {
    position 0 0
"""
        with self.assertRaises(parse.LayoutSyntaxError) as raised:
            parse.parse_text(text, source_path="broken.layout")
        self.assertIn("broken.layout:3:1", str(raised.exception))

    def test_widgetclass_leaf_without_child_block_is_valid(self) -> None:
        text = """FrameWidgetClass Root {
    {
        TextWidgetClass Label {
            text "No child block"
        }
    }
}
"""
        doc = parse.parse_text(text, source_path="missing-child-block.layout")
        data = doc.to_dict()
        self.assertNotIn("diagnostics", data)
        self.assertFalse(doc.roots[0].children[0].has_child_block)

    def test_false_strict_child_block_contract_is_not_exposed(self) -> None:
        self.assertNotIn("strict_child_blocks", inspect.signature(parse.Parser).parameters)
        self.assertNotIn("strict_child_blocks", inspect.signature(parse.parse_text).parameters)
        self.assertNotIn("strict_child_blocks", inspect.signature(parse.parse_file).parameters)
        self.assertNotIn(
            "--strict-child-blocks",
            parse.build_arg_parser()._option_string_actions,
        )

class ContinuationTests(unittest.TestCase):
    # Measured in DayZDiag 1.29.163451 through the LF_UIProbe fixture:
    # ButtonWidget.GetText returned Length()==10 for both the LF and the CRLF
    # source, and the RPT rendered the join as CRLF in a file whose 49768 bytes
    # contain zero bare LF and zero lone CR. Ten characters is "Alpha" + one +
    # "Beta", and only a newline is written as CRLF, so the engine inserts
    # exactly one newline. It is not a bare concatenation, which would be nine.
    ENGINE_VALUE = "Alpha\nBeta"

    LF_SOURCE = (
        'FrameWidgetClass ProbeRoot {\n'
        '    {\n'
        '        ButtonWidgetClass ProbeButton {\n'
        '            text "Alpha"\\\n'
        '                "Beta"\n'
        '        }\n'
        '    }\n'
        '}\n'
    )

    def _text_of(self, source: str) -> str:
        doc = parse.parse_text(source, source_path="continuation.layout")
        return str(doc.roots[0].children[0].attrs["text"][0])

    def test_lf_and_crlf_sources_agree_with_the_engine_value(self) -> None:
        crlf_source = self.LF_SOURCE.replace("\n", "\r\n")
        self.assertNotEqual(crlf_source, self.LF_SOURCE)

        # parse_file reads with universal newlines, so a CRLF layout reaches the
        # tokenizer as LF; parse_text callers can still hand over raw CRLF.
        self.assertEqual(self._text_of(self.LF_SOURCE), self.ENGINE_VALUE)
        self.assertEqual(self._text_of(crlf_source), self.ENGINE_VALUE)
        self.assertEqual(len(self.ENGINE_VALUE), 10)

    def test_continuation_chains_across_more_than_two_fragments(self) -> None:
        source = (
            'FrameWidgetClass Root {\n'
            '    text "one"\\\n'
            '        "two"\\\n'
            '        "three"\n'
            '}\n'
        )
        doc = parse.parse_text(source, source_path="chain.layout")
        self.assertEqual(doc.roots[0].attrs["text"][0], "one\ntwo\nthree")

    def test_attributes_after_a_continuation_keep_parsing(self) -> None:
        source = (
            'FrameWidgetClass Root {\n'
            '    text "a"\\\n'
            '        "b"\n'
            '    size 10 20\n'
            '}\n'
        )
        doc = parse.parse_text(source, source_path="after.layout")
        self.assertEqual(doc.roots[0].attrs["text"][0], "a\nb")
        self.assertEqual(doc.roots[0].attrs["size"], [10, 20])

    def test_unobserved_continuation_shapes_fail_with_line_and_column(self) -> None:
        # A backslash is not universal whitespace: only the observed shape joins.
        cases = {
            "orphan": 'FrameWidgetClass R {\n    text \\ "x"\n}\n',
            "bare token after": 'FrameWidgetClass R {\n    text "a"\\\n    12\n}\n',
            "space before newline": 'FrameWidgetClass R {\n    text "a"\\ \n    "b"\n}\n',
            "end of file": 'FrameWidgetClass R {\n    text "a"\\\n',
            "blank line between": 'FrameWidgetClass R {\n    text "a"\\\n\n    "b"\n}\n',
        }
        for label, source in cases.items():
            with self.subTest(shape=label):
                with self.assertRaises(parse.LayoutSyntaxError) as raised:
                    parse.parse_text(source, source_path="negative.layout")
                message = str(raised.exception)
                self.assertIn("negative.layout:2:", message)
                self.assertRegex(
                    message,
                    r"Orphan line continuation|Line continuation must join",
                )

    def test_observed_in_string_escapes_still_decode(self) -> None:
        doc = parse.parse_text(
            'FrameWidgetClass R {\n'
            '    a "x\\ny"\n'
            '    b "q\\"q"\n'
            '    c "back\\\\slash"\n'
            '    d "tab\\there"\n'
            '    e "carriage\\rreturn"\n'
            '}\n',
            source_path="escapes.layout",
        )
        attrs = doc.roots[0].attrs
        self.assertEqual(attrs["a"][0], "x\ny")
        self.assertEqual(attrs["b"][0], 'q"q')
        self.assertEqual(attrs["c"][0], "back\\slash")
        self.assertEqual(attrs["d"][0], "tab\there")
        self.assertEqual(attrs["e"][0], "carriage\rreturn")

    def test_unknown_in_string_escape_fails_closed(self) -> None:
        # This used to be a silent substitution that dropped the backslash, so
        # "gui\layouts\f.edds" parsed as "guilayoutsf.edds" with no diagnostic.
        # The five pinned corpora carry zero in-string backslashes across their
        # 376 layouts, so tightening it cannot break an observed layout; the
        # corpus gate is what keeps that measured rather than assumed.
        cases = {
            "path separator": 'FrameWidgetClass R {\n    c "gui\\layouts\\f.edds"\n}\n',
            "unknown letter": 'FrameWidgetClass R {\n    c "a\\qb"\n}\n',
            "escaped newline": 'FrameWidgetClass R {\n    c "a\\\nb"\n}\n',
            "escaped space": 'FrameWidgetClass R {\n    c "a\\ b"\n}\n',
        }
        for label, source in cases.items():
            with self.subTest(shape=label):
                with self.assertRaises(parse.LayoutSyntaxError) as raised:
                    parse.parse_text(source, source_path="escapes.layout")
                message = str(raised.exception)
                self.assertIn("escapes.layout:2:", message)
                self.assertIn("Unknown string escape", message)


class InlineAttributeTests(unittest.TestCase):
    # TOOLS.md and layout-format.md F1: grouping values by physical line
    # collapsed this one-line widget into a single `position` attribute.

    def test_inline_attributes_are_split_by_arity_not_by_physical_line(self) -> None:
        text = (
            "ImageWidgetClass Bg { position 0 0 size 1 1 stretch 1 ignorepointer 1 { } }"
        )
        doc = parse.parse_text(text, source_path="inline.layout")
        attrs = doc.roots[0].attrs
        self.assertEqual(list(attrs.keys()), ["position", "size", "stretch", "ignorepointer"])
        self.assertEqual(attrs["position"], [0, 0])
        self.assertEqual(attrs["size"], [1, 1])
        self.assertEqual(attrs["stretch"], [1])
        self.assertEqual(attrs["ignorepointer"], [1])

    def test_inline_float_edges_stay_on_their_own_keys(self) -> None:
        text = "ImageWidgetClass Inline { position 0 0 size .5 -0.5 { } }"
        doc = parse.parse_text(text, source_path="ok_inline_widget.layout")
        attrs = doc.roots[0].attrs
        self.assertEqual(attrs["position"], [0, 0])
        self.assertEqual(attrs["size"], [0.5, -0.5])
        self.assertNotIn("size", attrs["position"])

    def test_quoted_keys_on_one_line_stay_separate(self) -> None:
        text = 'TextWidgetClass T { "text halign" center "text valign" center { } }\n'
        doc = parse.parse_text(text, source_path="quoted-inline.layout")
        attrs = doc.roots[0].attrs
        self.assertEqual(attrs["text halign"], ["center"])
        self.assertEqual(attrs["text valign"], ["center"])

    def test_unary_value_that_collides_with_another_key_stays_a_value(self) -> None:
        text = 'ImageWidgetClass Bg { "clamp mode" wrap wrap 1 { } }\n'
        doc = parse.parse_text(text, source_path="clamp-inline.layout")
        attrs = doc.roots[0].attrs
        self.assertEqual(attrs["clamp mode"], ["wrap"])
        self.assertEqual(attrs["wrap"], [1])

    def test_unknown_keys_inline_still_collapse_which_is_the_documented_bound(self) -> None:
        # Not an aspiration: the arity split covers ATTRIBUTE_ARITY and nothing
        # else. A key the table does not list falls back to physical-line
        # grouping, so two unknown keys on one line still merge. Pinned here so
        # the bound stated in TOOLS.md cannot drift away from the code.
        text = "ImageWidgetClass Bg { zzz_custom 0 0 yyy_other 1 1 { } }"
        doc = parse.parse_text(text, source_path="unknown-inline.layout")
        attrs = doc.roots[0].attrs
        self.assertEqual(list(attrs.keys()), ["zzz_custom"])
        self.assertEqual(attrs["zzz_custom"], [0, 0, "yyy_other", 1, 1])

    def test_known_key_arity_ends_the_run_before_an_unknown_key(self) -> None:
        text = "ImageWidgetClass Bg { position 0 0 zzz_custom 7 { } }"
        doc = parse.parse_text(text, source_path="mixed-inline.layout")
        attrs = doc.roots[0].attrs
        self.assertEqual(attrs["position"], [0, 0])
        self.assertEqual(attrs["zzz_custom"], [7])


class Phase1ParserPathTests(unittest.TestCase):
    def test_out_dir_preserves_layout_root_relative_path(self) -> None:
        root = Path("C:/layouts")
        out_dir = Path("C:/out")
        medium = Path("C:/layouts/inventory_new/medium/cargo_container.layout")
        narrow = Path("C:/layouts/inventory_new/narrow/cargo_container.layout")

        medium_out = out_dir / parse.layout_json_relative_path(medium, [root])
        narrow_out = out_dir / parse.layout_json_relative_path(narrow, [root])

        self.assertEqual(
            medium_out,
            Path("C:/out/inventory_new/medium/cargo_container.layout.json"),
        )
        self.assertEqual(
            narrow_out,
            Path("C:/out/inventory_new/narrow/cargo_container.layout.json"),
        )
        self.assertNotEqual(medium_out, narrow_out)

    def test_source_display_path_can_be_relative(self) -> None:
        root = Path("C:/layouts")
        layout = Path("C:/layouts/gui/day_z_hud.layout")
        self.assertEqual(parse.source_display_path(layout, root), "gui/day_z_hud.layout")


if __name__ == "__main__":
    unittest.main()
