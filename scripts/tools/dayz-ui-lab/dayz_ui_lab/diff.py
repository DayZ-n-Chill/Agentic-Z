"""Compare semantic renders and report deterministic offline UI defects.

The supported iteration cycle is: render a named scenario state, run this diff,
edit the reported layout source, render again, and repeat until the verdict is
PASS. This module emits data only; it does not produce raster or engine evidence.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


MODULE_DIR = Path(__file__).resolve().parent
TOOL_DIR = MODULE_DIR.parent
REPO_ROOT = TOOL_DIR.parents[1]
SCHEMA_VERSION = "dayz-ui-diff-v1"
VIEWPORT_MISMATCH_CODE = "DIFF-VIEWPORT-MISMATCH"
MISSING_VALUE = {"missing": True}
STRUCTURAL_CODES = {
    "DIFF-PROPERTY-CHANGED",
    "DIFF-WIDGET-ADDED",
    "DIFF-WIDGET-REMOVED",
}
FINDING_CODE_ORDER = (
    "DIFF-WIDGET-ADDED",
    "DIFF-WIDGET-REMOVED",
    "DIFF-PROPERTY-CHANGED",
    "DIFF-REFERENCE-MISSING",
    "DIFF-CLIPPING",
    "DIFF-OVERLAP",
    "DIFF-OVERFLOW",
    "DIFF-STATE-MISSING",
)
FINDING_SORT_KEYS = (
    "code_precedence",
    "scenario",
    "widget_id",
    "property",
    "source",
    "expected_json",
    "observed_json",
)


def _load_render() -> Any:
    spec = importlib.util.spec_from_file_location(
        "dayz_ui_lab_diff_render", MODULE_DIR / "render.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load render.py next to diff.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


render = _load_render()


class DiffError(Exception):
    """Fail-closed CLI input error with a stable code."""

    def __init__(
        self,
        message: str,
        source: str = "",
        code: str = "DIFF-INPUT-INVALID",
    ):
        self.code = code
        self.message = message
        self.source = source
        rendered = f"{source}: {message}" if source else message
        super().__init__(rendered)


class DiffArgumentParser(argparse.ArgumentParser):
    """Convert argument errors to the diff CLI's binary exit contract."""

    def error(self, message: str) -> None:
        raise DiffError(message)


def _display_path(value: Path | str) -> str:
    path = Path(value)
    candidate = path if path.is_absolute() else REPO_ROOT / path
    try:
        return candidate.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return path.name


def _source(widget: dict[str, Any]) -> str:
    location = widget["source"]
    return (
        f"{_display_path(location['path'])}:"
        f"{location['line']}:{location['column']}"
    )


def _source_key(widget: dict[str, Any]) -> tuple[str, int, int, str]:
    location = widget["source"]
    return (
        _display_path(location["path"]),
        location["line"],
        location["column"],
        widget["id"],
    )


def _json_key(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _finding_sort_key(finding: dict[str, Any]) -> tuple[Any, ...]:
    try:
        code_rank = FINDING_CODE_ORDER.index(finding["code"])
    except ValueError:
        code_rank = len(FINDING_CODE_ORDER)
    return (
        code_rank,
        finding["scenario"],
        finding["widget_id"],
        finding["property"],
        finding["source"],
        _json_key(finding["expected"]),
        _json_key(finding["observed"]),
    )


def _finding(
    code: str,
    scenario: str,
    widget: dict[str, Any],
    property_name: str,
    expected: Any,
    observed: Any,
) -> dict[str, Any]:
    return {
        "code": code,
        "evidence": "offline",
        "expected": expected,
        "observed": observed,
        "property": property_name,
        "scenario": scenario,
        "source": _source(widget),
        "widget_id": widget["id"],
    }


def _validate_document(document: dict[str, Any], label: str) -> None:
    try:
        render.validate_render_document(document)
    except Exception as error:
        raise DiffError(f"{label} render is invalid: {error}") from error


def _widget_map(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {widget["id"]: widget for widget in document["widgets"]}


def _comparable_widget(widget: dict[str, Any]) -> dict[str, Any]:
    comparable = {
        key: value
        for key, value in widget.items()
        if key not in {"id", "source"}
    }
    comparable["attributes"] = {
        item["name"]: item["values"] for item in widget["attributes"]
    }
    comparable["state"] = {
        item["name"]: item["value"] for item in widget["state"]
    }
    return comparable


def _property_changes(
    expected: Any,
    observed: Any,
    prefix: str = "",
) -> list[tuple[str, Any, Any]]:
    if isinstance(expected, dict) and isinstance(observed, dict):
        changes: list[tuple[str, Any, Any]] = []
        for key in sorted(set(expected) | set(observed)):
            property_name = f"{prefix}.{key}" if prefix else key
            if key not in expected:
                changes.append((property_name, MISSING_VALUE, observed[key]))
            elif key not in observed:
                changes.append((property_name, expected[key], MISSING_VALUE))
            else:
                changes.extend(
                    _property_changes(expected[key], observed[key], property_name)
                )
        return changes
    if expected != observed:
        return [(prefix, expected, observed)]
    return []


def compare_documents(
    expected: dict[str, Any],
    observed: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare widgets by stable id and report semantic property deltas."""
    _validate_document(expected, "expected")
    _validate_document(observed, "observed")
    # Geometry is resolved against the viewport, so comparing two renders taken
    # at different ones reports every size, offset and position as changed. Those
    # deltas are resolution arithmetic, not defects, and they bury the findings
    # that are real: 1920x1080 against 3440x1440 on the three-card fixture yields
    # 86 property changes. Refuse the comparison instead of emitting them.
    #
    # Only the pairwise comparison is guarded. Analysing a single render at a
    # viewport the scenario does not declare stays valid, because the overlay
    # detectors read that render's own geometry and SC-005 requires composing one
    # scenario at two resolutions.
    if expected["viewport"] != observed["viewport"]:
        raise DiffError(
            "expected and observed renders declare different viewports: "
            f"{expected['viewport']['width']}x{expected['viewport']['height']} "
            f"and {observed['viewport']['width']}x{observed['viewport']['height']}",
            code=VIEWPORT_MISMATCH_CODE,
        )
    expected_widgets = _widget_map(expected)
    observed_widgets = _widget_map(observed)
    scenario = observed["scenario_id"]
    findings: list[dict[str, Any]] = []

    for widget_id in sorted(set(observed_widgets) - set(expected_widgets)):
        widget = observed_widgets[widget_id]
        findings.append(
            _finding(
                "DIFF-WIDGET-ADDED",
                scenario,
                widget,
                "widget",
                {"present": False},
                {"name": widget["name"], "present": True},
            )
        )

    for widget_id in sorted(set(expected_widgets) - set(observed_widgets)):
        widget = expected_widgets[widget_id]
        findings.append(
            _finding(
                "DIFF-WIDGET-REMOVED",
                scenario,
                widget,
                "widget",
                {"name": widget["name"], "present": True},
                {"present": False},
            )
        )

    for widget_id in sorted(set(expected_widgets) & set(observed_widgets)):
        expected_widget = expected_widgets[widget_id]
        observed_widget = observed_widgets[widget_id]
        for property_name, expected_value, observed_value in _property_changes(
            _comparable_widget(expected_widget),
            _comparable_widget(observed_widget),
        ):
            findings.append(
                _finding(
                    "DIFF-PROPERTY-CHANGED",
                    scenario,
                    observed_widget,
                    property_name,
                    expected_value,
                    observed_value,
                )
            )

    return sorted(findings, key=_finding_sort_key)


def _reference_findings(
    document: dict[str, Any],
    widgets: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    scenario = document["scenario_id"]
    findings: list[dict[str, Any]] = []
    for widget in sorted(widgets.values(), key=_source_key):
        parent_id = widget.get("parent_id")
        if parent_id is not None and parent_id not in widgets:
            findings.append(
                _finding(
                    "DIFF-REFERENCE-MISSING",
                    scenario,
                    widget,
                    "parent_id",
                    {"resolves": True},
                    {"reference": parent_id, "resolves": False},
                )
            )
        for child_id in widget["children"]:
            if child_id not in widgets:
                findings.append(
                    _finding(
                        "DIFF-REFERENCE-MISSING",
                        scenario,
                        widget,
                        "children",
                        {"resolves": True},
                        {"reference": child_id, "resolves": False},
                    )
                )
    return findings


def _effective_visibility(
    widget: dict[str, Any],
    widgets: dict[str, dict[str, Any]],
    memo: dict[str, bool],
    active: set[str] | None = None,
) -> bool:
    widget_id = widget["id"]
    if widget_id in memo:
        return memo[widget_id]
    if not widget["geometry"]["visible"]:
        memo[widget_id] = False
        return False
    if active is None:
        active = set()
    if widget_id in active:
        memo[widget_id] = False
        return False
    parent_id = widget.get("parent_id")
    if parent_id is None:
        memo[widget_id] = True
        return True
    parent = widgets.get(parent_id)
    if parent is None:
        memo[widget_id] = False
        return False
    visible = _effective_visibility(parent, widgets, memo, active | {widget_id})
    memo[widget_id] = visible
    return visible


def _bounds(widget: dict[str, Any]) -> dict[str, float]:
    geometry = widget["geometry"]
    position = geometry["position"]
    size = geometry["size"]
    return {
        "height": size["height"],
        "width": size["width"],
        "x": position["x"],
        "y": position["y"],
    }


def _outside_parent(
    child: dict[str, Any],
    parent: dict[str, Any],
) -> bool:
    child_bounds = _bounds(child)
    parent_size = parent["geometry"]["size"]
    return (
        child_bounds["x"] < 0
        or child_bounds["y"] < 0
        or child_bounds["x"] + child_bounds["width"] > parent_size["width"]
        or child_bounds["y"] + child_bounds["height"] > parent_size["height"]
    )


def _containment_findings(
    document: dict[str, Any],
    widgets: dict[str, dict[str, Any]],
    visibility: dict[str, bool],
) -> list[dict[str, Any]]:
    scenario = document["scenario_id"]
    findings: list[dict[str, Any]] = []
    for child in sorted(widgets.values(), key=_source_key):
        parent_id = child.get("parent_id")
        parent = widgets.get(parent_id) if parent_id is not None else None
        if parent is None:
            continue
        if not _effective_visibility(child, widgets, visibility):
            continue
        if child["geometry"]["status"] != "resolved":
            continue
        if parent["geometry"]["status"] != "resolved":
            continue
        if not _outside_parent(child, parent):
            continue
        code = (
            "DIFF-CLIPPING"
            if parent["geometry"]["clip_children"]
            else "DIFF-OVERFLOW"
        )
        findings.append(
            _finding(
                code,
                scenario,
                child,
                "geometry.bounds",
                {
                    "height": parent["geometry"]["size"]["height"],
                    "width": parent["geometry"]["size"]["width"],
                    "x": 0.0,
                    "y": 0.0,
                },
                _bounds(child),
            )
        )
    return findings


def _intersection(
    first: dict[str, Any],
    second: dict[str, Any],
) -> dict[str, float] | None:
    first_bounds = _bounds(first)
    second_bounds = _bounds(second)
    left = max(first_bounds["x"], second_bounds["x"])
    top = max(first_bounds["y"], second_bounds["y"])
    right = min(
        first_bounds["x"] + first_bounds["width"],
        second_bounds["x"] + second_bounds["width"],
    )
    bottom = min(
        first_bounds["y"] + first_bounds["height"],
        second_bounds["y"] + second_bounds["height"],
    )
    if right <= left or bottom <= top:
        return None
    return {
        "height": bottom - top,
        "width": right - left,
        "x": left,
        "y": top,
    }


def _overlap_findings(
    document: dict[str, Any],
    widgets: dict[str, dict[str, Any]],
    visibility: dict[str, bool],
) -> list[dict[str, Any]]:
    scenario = document["scenario_id"]
    siblings: dict[str | None, list[dict[str, Any]]] = {}
    for widget in widgets.values():
        if widget["geometry"]["status"] != "resolved":
            continue
        if not _effective_visibility(widget, widgets, visibility):
            continue
        size = widget["geometry"]["size"]
        if size["width"] <= 0 or size["height"] <= 0:
            continue
        siblings.setdefault(widget.get("parent_id"), []).append(widget)

    findings: list[dict[str, Any]] = []
    for parent_id in sorted(siblings, key=lambda value: value or ""):
        ordered = sorted(siblings[parent_id], key=_source_key)
        for first_index, first in enumerate(ordered):
            for second in ordered[first_index + 1 :]:
                intersection = _intersection(first, second)
                if intersection is None:
                    continue
                findings.append(
                    _finding(
                        "DIFF-OVERLAP",
                        scenario,
                        second,
                        "geometry.bounds",
                        {"sibling_overlaps": []},
                        {
                            "intersection": intersection,
                            "sibling_widget_id": first["id"],
                        },
                    )
                )
    return findings


def _scenario_path(
    document: dict[str, Any],
    scenario_path: Path | str | None,
) -> Path:
    value = scenario_path if scenario_path is not None else document["scenario"]
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _load_scenario_document(path: Path) -> dict[str, Any]:
    try:
        return render.scenario.load_scenario(path)
    except Exception as error:
        raise DiffError(
            f"scenario cannot be loaded: {error}",
            _display_path(path),
        ) from error


def _fallback_widget(widgets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    roots = [widget for widget in widgets.values() if widget.get("parent_id") is None]
    candidates = roots or list(widgets.values())
    return sorted(candidates, key=_source_key)[0]


def _state_value(widget: dict[str, Any], name: str) -> Any:
    state = {item["name"]: item["value"] for item in widget["state"]}
    return state.get(name, MISSING_VALUE)


def _nested_state_value(
    widget: dict[str, Any],
    name: str,
    nested_name: str,
) -> Any:
    value = _state_value(widget, name)
    if not isinstance(value, dict):
        return MISSING_VALUE
    return value.get(nested_name, MISSING_VALUE)


def _state_findings(
    document: dict[str, Any],
    widgets: dict[str, dict[str, Any]],
    scenario_document: dict[str, Any],
) -> list[dict[str, Any]]:
    scenario = document["scenario_id"]
    state_name = document["state"]
    selected = next(
        (state for state in scenario_document["states"] if state["name"] == state_name),
        None,
    )
    if selected is None:
        widget = _fallback_widget(widgets)
        return [
            _finding(
                "DIFF-STATE-MISSING",
                scenario,
                widget,
                "state",
                {"declared": sorted(state["name"] for state in scenario_document["states"])},
                state_name,
            )
        ]

    by_name: dict[str, list[dict[str, Any]]] = {}
    for widget in widgets.values():
        by_name.setdefault(widget["name"], []).append(widget)
    for matches in by_name.values():
        matches.sort(key=_source_key)

    findings: list[dict[str, Any]] = []

    def check(
        widget_name: str,
        property_name: str,
        state_key: str,
        expected: Any,
        nested_key: str | None = None,
    ) -> None:
        widget = by_name.get(widget_name, [_fallback_widget(widgets)])[0]
        observed = (
            _nested_state_value(widget, state_key, nested_key)
            if nested_key is not None
            else _state_value(widget, state_key)
        )
        if widget_name not in by_name:
            observed = {"missing_widget": widget_name}
        if observed != expected:
            findings.append(
                _finding(
                    "DIFF-STATE-MISSING",
                    scenario,
                    widget,
                    property_name,
                    expected,
                    observed,
                )
            )

    for rule in selected.get("bindings", []):
        check(
            rule["widget"],
            f"state.bindings.{rule['property']}",
            "bindings",
            rule["value"],
            rule["property"],
        )
    for rule in selected.get("visibility", []):
        check(rule["widget"], "state.visible", "visible", rule["visible"])
    for rule in selected.get("colors", []):
        check(rule["widget"], "state.color", "color", rule["color"])
        check(rule["widget"], "state.alpha", "alpha", rule["alpha"])
    for rule in selected.get("positions", []):
        expected_position = {
            "height": rule["height"],
            "width": rule["width"],
            "x": rule["x"],
            "y": rule["y"],
        }
        check(rule["widget"], "state.position", "position", expected_position)
    for rule in selected.get("tabs", []):
        check(rule["widget"], "state.tab_active", "tab_active", rule["active"])
    for rule in selected.get("controls", []):
        check(rule["widget"], "state.enabled", "enabled", rule["enabled"])
    for rule in selected.get("modal", []):
        check(
            rule["widget"],
            "state.modal_visible",
            "modal_visible",
            rule["visible"],
        )
    for rule in selected.get("pointer", []):
        check(rule["widget"], "state.pointer", "pointer", rule["state"])

    collection_definitions = {
        collection["id"]: collection for collection in scenario_document["collections"]
    }
    for selection in selected.get("collections", []):
        collection_id = selection["collection"]
        observed_items = [
            widget["collection"]["item_key"]
            for widget in document["widgets"]
            if widget.get("collection", {}).get("id") == collection_id
        ]
        expected_items = selection["items"]
        if observed_items == expected_items:
            continue
        mount_name = collection_definitions[collection_id]["mount"]
        widget = by_name.get(mount_name, [_fallback_widget(widgets)])[0]
        findings.append(
            _finding(
                "DIFF-STATE-MISSING",
                scenario,
                widget,
                f"state.collections.{collection_id}",
                expected_items,
                observed_items,
            )
        )

    return findings


def analyze_document(
    document: dict[str, Any],
    scenario_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Detect reference, containment, overlap, and state defects."""
    _validate_document(document, "observed")
    widgets = _widget_map(document)
    if not widgets:
        raise DiffError("observed render has no widgets")
    scenario_document = _load_scenario_document(
        _scenario_path(document, scenario_path)
    )
    if scenario_document["scenario_id"] != document["scenario_id"]:
        raise DiffError("scenario id does not match the observed render")

    visibility: dict[str, bool] = {}
    findings = _reference_findings(document, widgets)
    findings.extend(_containment_findings(document, widgets, visibility))
    findings.extend(_overlap_findings(document, widgets, visibility))
    findings.extend(_state_findings(document, widgets, scenario_document))
    return sorted(findings, key=_finding_sort_key)


def _input_summary(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "scenario_id": document["scenario_id"],
        "state": document["state"],
        "viewport": document["viewport"],
    }


def build_report(
    observed: dict[str, Any],
    expected: dict[str, Any] | None = None,
    scenario_path: Path | str | None = None,
) -> dict[str, Any]:
    """Build the canonical dayz-ui-diff-v1 contract document."""
    structural = compare_documents(expected, observed) if expected is not None else []
    overlays = analyze_document(observed, scenario_path)
    findings = sorted([*structural, *overlays], key=_finding_sort_key)
    return {
        "canonical": observed["canonical"],
        "finding_order": {
            "code_precedence": list(FINDING_CODE_ORDER),
            "keys": list(FINDING_SORT_KEYS),
        },
        "findings": findings,
        "inputs": {
            "expected": _input_summary(expected) if expected is not None else None,
            "observed": _input_summary(observed),
        },
        "scenario_id": observed["scenario_id"],
        "schema_version": SCHEMA_VERSION,
        "state": observed["state"],
        "stats": {
            "finding_count": len(findings),
            "overlay_count": len(findings) - sum(
                finding["code"] in STRUCTURAL_CODES for finding in findings
            ),
            "structural_count": sum(
                finding["code"] in STRUCTURAL_CODES for finding in findings
            ),
        },
        "verdict": "FAIL" if findings else "PASS",
        "viewport": observed["viewport"],
    }


def canonical_bytes(report: dict[str, Any]) -> bytes:
    """Serialize a diff report with the contract's canonical JSON profile."""
    return (
        json.dumps(
            report,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard numeric constant {value!r}")


def _read_render(path: Path, label: str) -> dict[str, Any]:
    source = _display_path(path)
    try:
        with open(path, "r", encoding="utf-8-sig") as stream:
            document = json.load(stream, parse_constant=_reject_json_constant)
    except (OSError, UnicodeError, ValueError) as error:
        raise DiffError(f"cannot read {label} render: {error}", source) from error
    if not isinstance(document, dict):
        raise DiffError(f"{label} render root must be an object", source)
    _validate_document(document, label)
    return document


def _write_report(path: Path, report: dict[str, Any]) -> None:
    try:
        with open(path, "wb") as stream:
            stream.write(canonical_bytes(report))
    except OSError as error:
        raise DiffError(f"cannot write report: {error}", _display_path(path)) from error


def _error_report(error: DiffError) -> dict[str, Any]:
    return {
        "canonical": {"raster": False, "semantic": False},
        "errors": [
            {
                "code": error.code,
                "message": error.message,
                "source": error.source,
            }
        ],
        "finding_order": {
            "code_precedence": list(FINDING_CODE_ORDER),
            "keys": list(FINDING_SORT_KEYS),
        },
        "findings": [],
        "inputs": {"expected": None, "observed": None},
        "scenario_id": "",
        "schema_version": SCHEMA_VERSION,
        "state": "",
        "stats": {
            "finding_count": 0,
            "overlay_count": 0,
            "structural_count": 0,
        },
        "verdict": "FAIL",
        "viewport": None,
    }


def _parser() -> DiffArgumentParser:
    parser = DiffArgumentParser(
        description="Compare semantic DayZ UI renders and detect offline defects.",
        epilog=(
            "Cycle: render the scenario, run diff, edit each reported layout "
            "source, render again, and repeat until verdict=PASS."
        ),
    )
    parser.add_argument("--observed", required=True, type=Path)
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--scenario", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser


def _print_report(report: dict[str, Any]) -> None:
    for finding in report["findings"]:
        print(
            f"{finding['code']} scenario={finding['scenario']} "
            f"widget={finding['widget_id']} property={finding['property']} "
            f"expected={_json_key(finding['expected'])} "
            f"observed={_json_key(finding['observed'])} "
            f"source={finding['source']} evidence={finding['evidence']}"
        )
    print(
        f"findings={report['stats']['finding_count']} "
        f"verdict={report['verdict']}"
    )


def main(argv: list[str] | None = None) -> int:
    report_path: Path | None = None
    try:
        arguments = _parser().parse_args(argv)
        report_path = arguments.report
        observed = _read_render(arguments.observed, "observed")
        expected = (
            _read_render(arguments.expected, "expected")
            if arguments.expected is not None
            else None
        )
        report = build_report(observed, expected, arguments.scenario)
        _write_report(arguments.report, report)
        _print_report(report)
        return 0 if report["verdict"] == "PASS" else 1
    except DiffError as error:
        report = _error_report(error)
        if report_path is not None:
            try:
                _write_report(report_path, report)
            except DiffError:
                pass
        prefix = f"{error.source}: " if error.source else ""
        print(f"{error.code} {prefix}{error.message}")
        print("findings=0 verdict=FAIL")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
