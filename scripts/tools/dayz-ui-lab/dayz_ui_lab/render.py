"""Emit deterministic semantic renders from versioned DayZ UI scenarios."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


MODULE_DIR = Path(__file__).resolve().parent
TOOL_DIR = MODULE_DIR.parent
REPO_ROOT = TOOL_DIR.parents[1]
SCHEMA_PATH = TOOL_DIR / "schemas" / "dayz-ui-render-v1.schema.json"
SCHEMA_VERSION = "dayz-ui-render-v1"
FLOAT_DECIMAL_PLACES = 6


def _load_scenario() -> Any:
    spec = importlib.util.spec_from_file_location(
        "dayz_ui_lab_render_scenario", MODULE_DIR / "scenario.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load scenario.py next to render.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


scenario = _load_scenario()


class RenderError(Exception):
    """Fail-closed render error with a stable machine-readable code."""

    def __init__(
        self,
        code: str,
        message: str,
        source: str = "",
        scenario_id: str = "",
    ):
        self.code = code
        self.message = message
        self.source = source
        self.scenario_id = scenario_id
        rendered = f"{source}: {message}" if source else message
        super().__init__(rendered)


def finding(error: Any) -> dict[str, str]:
    return {
        "code": error.code,
        "scenario_id": error.scenario_id,
        "message": error.message,
        "source": error.source,
    }


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard numeric constant {value!r}")


def _read_schema() -> dict[str, Any]:
    source = _display_path(SCHEMA_PATH)
    try:
        with SCHEMA_PATH.open("r", encoding="utf-8-sig") as stream:
            document = json.load(stream, parse_constant=_reject_json_constant)
    except json.JSONDecodeError as error:
        raise RenderError(
            "RENDER-SCHEMA-INVALID",
            f"invalid JSON at line {error.lineno}, column {error.colno}",
            source,
        ) from error
    except (OSError, ValueError) as error:
        raise RenderError(
            "RENDER-SCHEMA-INVALID",
            "cannot read render schema",
            source,
        ) from error
    if not isinstance(document, dict):
        raise RenderError(
            "RENDER-SCHEMA-INVALID",
            "render schema root must be an object",
            source,
        )
    return document


def _round_float(value: float) -> float:
    if not math.isfinite(value):
        raise RenderError(
            "RENDER-NORMALIZATION-INVALID",
            "render values must not contain non-finite floats",
        )
    rounded = round(value, FLOAT_DECIMAL_PLACES)
    return 0.0 if rounded == 0 else rounded


def _normalize_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        return _round_float(value)
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise RenderError(
                "RENDER-NORMALIZATION-INVALID",
                "render object keys must be strings",
            )
        return {key: _normalize_value(value[key]) for key in sorted(value)}
    raise RenderError(
        "RENDER-NORMALIZATION-INVALID",
        f"unsupported render value type {type(value).__name__!r}",
    )


def _normalize_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    if (
        normalized.startswith("/")
        or re.match(r"^[A-Za-z]:", normalized) is not None
        or ".." in normalized.split("/")
    ):
        raise RenderError(
            "RENDER-NORMALIZATION-INVALID",
            "render paths must be repository-relative",
        )
    return normalized


def _normalize_attributes(attributes: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "values": _normalize_value(attributes[name]),
        }
        for name in sorted(attributes)
    ]


def _normalize_state(runtime_state: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "value": _normalize_value(runtime_state[name]),
        }
        for name in sorted(runtime_state)
    ]


def _normalize_geometry(geometry: dict[str, Any]) -> dict[str, Any]:
    raw_position = geometry["raw"]["position"]
    raw_size = geometry["raw"]["size"]
    normalized = {
        "anchor": _normalize_value(geometry["anchor"]),
        "clip_children": geometry["clipChildren"],
        "flags": _normalize_value(geometry["flags"]),
        "ignore_pointer": geometry["ignorePointer"],
        "notes": _normalize_value(geometry["notes"]),
        "offset": _normalize_value(geometry["offset"]),
        "position": _normalize_value(geometry["position"]),
        "raw": {
            "position": {
                "x": _normalize_value(raw_position[0]),
                "y": _normalize_value(raw_position[1]),
            },
            "size": {
                "height": _normalize_value(raw_size[1]),
                "width": _normalize_value(raw_size[0]),
            },
        },
        "size": _normalize_value(geometry["size"]),
        "status": geometry["status"],
        "visible": geometry["visible"],
    }
    if geometry["alpha"] is not None:
        normalized["alpha"] = _normalize_value(geometry["alpha"])
    return normalized


def _append_widgets(
    nodes: list[dict[str, Any]],
    widgets: list[dict[str, Any]],
) -> None:
    for node in nodes:
        widget = {
            "attributes": _normalize_attributes(node["attrs"]),
            "children": [child["id"] for child in node["children"]],
            "geometry": _normalize_geometry(node["geometry"]),
            "id": node["id"],
            "name": node["name"],
            "sibling_index": node["sibling_index"],
            "source": {
                "column": node["source"]["column"],
                "line": node["source"]["line"],
                "path": _normalize_path(node["source"]["path"]),
            },
            "state": _normalize_state(node["runtime_state"]),
            "type": node["type"],
        }
        if node["parent_id"] is not None:
            widget["parent_id"] = node["parent_id"]
        if node.get("collection_id") and node.get("item_key"):
            widget["collection"] = {
                "id": node["collection_id"],
                "item_key": node["item_key"],
            }
        widgets.append(widget)
        _append_widgets(node["children"], widgets)


def normalize_composition(composition: dict[str, Any]) -> dict[str, Any]:
    """Project a composed widget tree into the canonical semantic render form."""
    widgets: list[dict[str, Any]] = []
    _append_widgets(composition["roots"], widgets)
    document = {
        "canonical": {
            "raster": False,
            "semantic": True,
        },
        "entrypoint": _normalize_path(composition["entrypoint"]),
        "normalization": {
            "float_decimal_places": FLOAT_DECIMAL_PLACES,
            "path_format": "repo-relative-posix",
            "widget_order": "depth-first-preorder",
        },
        "scenario": _normalize_path(composition["scenario"]),
        "scenario_id": composition["scenario_id"],
        "schema_version": SCHEMA_VERSION,
        "state": composition["state"],
        "stats": {
            "widget_count": len(widgets),
        },
        "viewport": {
            "height": composition["viewport"]["height"],
            "width": composition["viewport"]["width"],
        },
        "widgets": widgets,
    }
    validate_render_document(document)
    return document


def _iter_values(value: Any):
    yield value
    if isinstance(value, dict):
        for key in sorted(value):
            yield from _iter_values(value[key])
    elif isinstance(value, list):
        for item in value:
            yield from _iter_values(item)


def validate_render_document(document: dict[str, Any]) -> None:
    """Validate a dayz-ui-render-v1 document with the shared stdlib validator."""
    source = _display_path(SCHEMA_PATH)
    try:
        scenario.validate_against_schema(document, _read_schema(), source)
    except scenario.ScenarioError as error:
        raise RenderError(
            "RENDER-SCHEMA-INVALID",
            error.message,
            error.source,
        ) from error

    for value in _iter_values(document):
        if not isinstance(value, float):
            continue
        if not math.isfinite(value) or value != round(value, FLOAT_DECIMAL_PLACES):
            raise RenderError(
                "RENDER-SCHEMA-INVALID",
                f"float {value!r} exceeds the declared precision",
                source,
            )
        if value == 0 and math.copysign(1.0, value) < 0:
            raise RenderError(
                "RENDER-SCHEMA-INVALID",
                "negative zero is not canonical",
                source,
            )


def render_document(
    path: Path | str,
    state_name: str | None = None,
    viewport: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Compose and normalize one deterministic semantic render document."""
    composition = scenario.compose_scenario(
        path,
        state_name=state_name,
        viewport=viewport,
    )
    return normalize_composition(composition)


def canonical_bytes(document: dict[str, Any]) -> bytes:
    """Serialize a validated render document to canonical UTF-8 JSON bytes."""
    validate_render_document(document)
    return (
        json.dumps(
            document,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def render_bytes(
    path: Path | str,
    state_name: str | None = None,
    viewport: tuple[int, int] | None = None,
) -> bytes:
    return canonical_bytes(
        render_document(path, state_name=state_name, viewport=viewport)
    )


def _write_bytes(path: Path, payload: bytes, code: str, label: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    except OSError as error:
        raise RenderError(
            code,
            f"cannot write {label}",
            _display_path(path),
        ) from error


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Emit a deterministic dayz-ui-render-v1 document.",
    )
    parser.add_argument("--scenario", required=True, help="scenario JSON path")
    parser.add_argument("--state", default=None, help="named scenario state")
    parser.add_argument("--viewport", required=True, help="render viewport WIDTHxHEIGHT")
    parser.add_argument("--out", required=True, help="write render JSON here")
    parser.add_argument("--report", default=None, help="write the JSON report here")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    scenario_path = Path(args.scenario)
    scenario_source = _display_path(scenario_path)
    document: dict[str, Any] | None = None
    artifact: dict[str, Any] | None = None
    findings: list[dict[str, str]] = []
    viewport: tuple[int, int] | None = None

    try:
        viewport = scenario._parse_viewport(args.viewport, scenario_source)
        document = render_document(
            scenario_path,
            state_name=args.state,
            viewport=viewport,
        )
        payload = canonical_bytes(document)
        _write_bytes(
            Path(args.out),
            payload,
            "RENDER-OUTPUT-WRITE-FAILED",
            "render document",
        )
        artifact = {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    except scenario.ScenarioError as error:
        findings.append(finding(error))
    except RenderError as error:
        findings.append(finding(error))

    report: dict[str, Any] = {
        "artifact": artifact,
        "canonical": {
            "raster": False,
            "semantic": True,
        },
        "command": "dayz-ui-lab render",
        "findings": findings,
        "scenario": scenario_source,
        "schema_version": SCHEMA_VERSION,
        "state": document["state"] if document is not None else (args.state or ""),
        "verdict": "PASS" if not findings else "FAIL",
        "viewport": (
            {"height": viewport[1], "width": viewport[0]}
            if viewport is not None
            else args.viewport
        ),
    }

    if args.report:
        try:
            report_payload = (
                json.dumps(
                    report,
                    allow_nan=False,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8")
            _write_bytes(
                Path(args.report),
                report_payload,
                "RENDER-REPORT-WRITE-FAILED",
                "render report",
            )
        except RenderError as error:
            findings.append(finding(error))
            report["findings"] = findings
            report["verdict"] = "FAIL"

    if report["verdict"] == "PASS" and document is not None:
        size = document["viewport"]
        print(
            f"render: {document['scenario_id']} state={document['state']} "
            f"viewport={size['width']}x{size['height']} "
            f"widgets={document['stats']['widget_count']}"
        )
    else:
        for item in findings:
            print(f"  {item['code']} | {item['source'] or '-'} | {item['message']}")

    print(f"verdict={report['verdict']}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
