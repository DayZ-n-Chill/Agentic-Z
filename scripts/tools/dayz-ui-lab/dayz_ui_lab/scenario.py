"""Validate and compose versioned DayZ UI scenarios on the parser IR."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


MODULE_DIR = Path(__file__).resolve().parent
TOOL_DIR = MODULE_DIR.parent
REPO_ROOT = TOOL_DIR.parents[1]
SCHEMA_PATH = TOOL_DIR / "schemas" / "dayz-ui-scenario-v1.schema.json"
SCHEMA_VERSION = "dayz-ui-scenario-v1"
DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
SUPPORTED_SCHEMA_KEYS = {
    "$schema",
    "type",
    "required",
    "enum",
    "properties",
    "additionalProperties",
    "items",
    "minimum",
    "pattern",
}
SUPPORTED_TYPES = {"object", "array", "string", "integer", "number", "boolean"}


def _load_parser() -> Any:
    spec = importlib.util.spec_from_file_location(
        "dayz_ui_lab_scenario_parse", MODULE_DIR / "parse.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load parse.py next to scenario.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


parse = _load_parser()


class ScenarioError(Exception):
    """Fail-closed scenario error with a stable machine-readable code."""

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


def finding(error: ScenarioError) -> dict[str, str]:
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


def _schema_failure(source: str, location: str, message: str) -> ScenarioError:
    return ScenarioError(
        "SCENARIO-SCHEMA-INVALID",
        f"{location}: {message}",
        source,
    )

def _check_schema_definition(
    schema: Any,
    source: str,
    location: str = "$",
) -> None:
    if not isinstance(schema, dict):
        raise _schema_failure(source, location, "schema node must be an object")

    unknown = sorted(set(schema) - SUPPORTED_SCHEMA_KEYS)
    if unknown:
        joined = ", ".join(unknown)
        raise _schema_failure(source, location, f"unsupported schema keyword(s): {joined}")

    if "$schema" in schema and schema["$schema"] != DRAFT_2020_12:
        raise _schema_failure(source, f"{location}.$schema", "unsupported JSON Schema draft")

    schema_type = schema.get("type")
    if schema_type is not None:
        if not isinstance(schema_type, str) or schema_type not in SUPPORTED_TYPES:
            raise _schema_failure(source, f"{location}.type", "unsupported schema type")

    if "required" in schema:
        required = schema["required"]
        if schema_type != "object" or not isinstance(required, list):
            raise _schema_failure(source, f"{location}.required", "requires an object schema and an array")
        if any(not isinstance(item, str) for item in required) or len(required) != len(set(required)):
            raise _schema_failure(source, f"{location}.required", "must contain unique strings")

    if "enum" in schema:
        enum = schema["enum"]
        if not isinstance(enum, list) or not enum:
            raise _schema_failure(source, f"{location}.enum", "must be a non-empty array")

    if "properties" in schema:
        properties = schema["properties"]
        if schema_type != "object" or not isinstance(properties, dict):
            raise _schema_failure(source, f"{location}.properties", "requires an object schema and an object")
        for key in sorted(properties):
            if not isinstance(key, str):
                raise _schema_failure(source, f"{location}.properties", "property names must be strings")
            _check_schema_definition(properties[key], source, f"{location}.properties.{key}")

    if "additionalProperties" in schema:
        if schema_type != "object" or not isinstance(schema["additionalProperties"], bool):
            raise _schema_failure(source, f"{location}.additionalProperties", "only boolean object policy is supported")

    if "items" in schema:
        if schema_type != "array":
            raise _schema_failure(source, f"{location}.items", "requires an array schema")
        _check_schema_definition(schema["items"], source, f"{location}.items")

    if "minimum" in schema:
        minimum = schema["minimum"]
        if schema_type not in {"integer", "number"} or isinstance(minimum, bool) or not isinstance(minimum, (int, float)):
            raise _schema_failure(source, f"{location}.minimum", "requires a numeric schema and value")

    if "pattern" in schema:
        pattern = schema["pattern"]
        if schema_type != "string" or not isinstance(pattern, str):
            raise _schema_failure(source, f"{location}.pattern", "requires a string schema and value")
        try:
            re.compile(pattern)
        except re.error as error:
            raise _schema_failure(source, f"{location}.pattern", f"invalid regular expression: {error}") from error


def _instance_matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return False

def _validate_value(
    value: Any,
    schema: dict[str, Any],
    source: str,
    location: str = "$",
) -> None:
    expected = schema.get("type")
    if expected is not None and not _instance_matches_type(value, expected):
        raise _schema_failure(source, location, f"expected {expected}, got {type(value).__name__}")
    if expected in {"integer", "number"} and isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise _schema_failure(source, location, "number must be finite")

    if "enum" in schema and value not in schema["enum"]:
        raise _schema_failure(source, location, f"value {value!r} is not in the declared enum")

    if "minimum" in schema and value < schema["minimum"]:
        raise _schema_failure(source, location, f"value {value!r} is below minimum {schema['minimum']!r}")

    if "pattern" in schema and re.search(schema["pattern"], value) is None:
        raise _schema_failure(source, location, f"value {value!r} does not match pattern {schema['pattern']!r}")

    if expected == "object":
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise _schema_failure(source, location, f"missing required property {key!r}")

        properties = schema.get("properties", {})
        unexpected = sorted(set(value) - set(properties))
        if unexpected and schema.get("additionalProperties", True) is False:
            joined = ", ".join(unexpected)
            raise _schema_failure(source, location, f"unexpected property(s): {joined}")
        for key in sorted(set(value) & set(properties)):
            _validate_value(value[key], properties[key], source, f"{location}.{key}")

    if expected == "array" and "items" in schema:
        for index, item in enumerate(value):
            _validate_value(item, schema["items"], source, f"{location}[{index}]")


def validate_against_schema(
    instance: Any,
    schema: dict[str, Any],
    source_path: str,
) -> None:
    """Validate an instance with the supported fail-closed JSON Schema subset."""
    _check_schema_definition(schema, source_path)
    _validate_value(instance, schema, source_path)


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard numeric constant {value!r}")


def _read_json(path: Path, source: str) -> Any:
    try:
        with path.open("r", encoding="utf-8-sig") as stream:
            return json.load(stream, parse_constant=_reject_json_constant)
    except json.JSONDecodeError as error:
        raise _schema_failure(
            source,
            "$",
            f"invalid JSON at line {error.lineno}, column {error.colno}",
        ) from error
    except OSError as error:
        raise _schema_failure(source, "$", "cannot read JSON document") from error
    except ValueError as error:
        raise _schema_failure(source, "$", f"invalid JSON value: {error}") from error


def _require_unique(values: list[str], label: str, source: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise _schema_failure(source, "$", f"duplicate {label} {value!r}")
        seen.add(value)


def _validate_semantics(document: dict[str, Any], source: str) -> None:
    subviews = document["subviews"]
    collections = document["collections"]
    states = document["states"]
    _require_unique([item["id"] for item in subviews], "subview id", source)
    _require_unique([item["id"] for item in collections], "collection id", source)
    _require_unique([item["name"] for item in states], "state name", source)

    subview_ids = {item["id"] for item in subviews}
    for ref in document["entrypoint"]["subviews"]:
        if ref not in subview_ids:
            raise _schema_failure(source, "$.entrypoint.subviews", f"unknown subview {ref!r}")
    for index, subview in enumerate(subviews):
        for ref in subview["subviews"]:
            if ref not in subview_ids:
                raise _schema_failure(source, f"$.subviews[{index}].subviews", f"unknown subview {ref!r}")

    collection_items: dict[str, set[str]] = {}
    for index, collection in enumerate(collections):
        keys = [item["key"] for item in collection["items"]]
        _require_unique(keys, f"item key in collection {collection['id']!r}", source)
        collection_items[collection["id"]] = set(keys)

    for state_index, state in enumerate(states):
        selected_collections: list[str] = []
        for selection in state.get("collections", []):
            collection_id = selection["collection"]
            selected_collections.append(collection_id)
            if collection_id not in collection_items:
                raise _schema_failure(source, f"$.states[{state_index}].collections", f"unknown collection {collection_id!r}")
            _require_unique(selection["items"], f"selected item in collection {collection_id!r}", source)
            for key in selection["items"]:
                if key not in collection_items[collection_id]:
                    raise _schema_failure(source, f"$.states[{state_index}].collections", f"unknown item {key!r} in collection {collection_id!r}")
        _require_unique(selected_collections, "state collection selection", source)

        for color_index, color in enumerate(state.get("colors", [])):
            values = color["color"]
            if len(values) != 4 or any(value > 1 for value in values):
                raise _schema_failure(source, f"$.states[{state_index}].colors[{color_index}].color", "must contain four numbers in the range 0..1")
            if color["alpha"] > 1:
                raise _schema_failure(source, f"$.states[{state_index}].colors[{color_index}].alpha", "must be in the range 0..1")


def load_scenario(path: Path | str) -> dict[str, Any]:
    """Load and validate a scenario document without composing layouts."""
    scenario_path = Path(path).resolve()
    scenario_source = _display_path(scenario_path)
    document = _read_json(scenario_path, scenario_source)
    schema_source = _display_path(SCHEMA_PATH)
    schema = _read_json(SCHEMA_PATH, schema_source)
    scenario_id = document.get("scenario_id", "") if isinstance(document, dict) else ""
    try:
        validate_against_schema(document, schema, scenario_source)
        _validate_semantics(document, scenario_source)
    except ScenarioError as error:
        if not error.scenario_id and isinstance(scenario_id, str):
            error.scenario_id = scenario_id
        raise
    return document


@dataclass
class ComposedNode:
    node: Any
    source_path: str
    children: list["ComposedNode"] = field(default_factory=list)
    runtime_state: dict[str, Any] = field(default_factory=dict)
    collection_id: str = ""
    item_key: str = ""


def _wrap_widget(node: Any, source_path: str) -> ComposedNode | None:
    if not parse.is_widget_node(node):
        return None
    wrapped = ComposedNode(
        node=node,
        source_path=source_path,
    )
    wrapped.children = [
        child
        for child in (
            _wrap_widget(candidate, source_path) for candidate in node.children
        )
        if child is not None
    ]
    return wrapped


def _resolve_layout(layout_ref: str, scenario_dir: Path) -> Path:
    candidate = scenario_dir / Path(layout_ref)
    try:
        return parse.resolve_layout_path(str(candidate), [])
    except FileNotFoundError as error:
        raise ScenarioError(
            "SCENARIO-LAYOUT-MISSING",
            f"layout does not resolve: {layout_ref}",
            _display_path(candidate),
        ) from error


def _parse_layout(
    layout_ref: str,
    scenario_dir: Path,
    viewport: tuple[int, int],
) -> tuple[Path, list[ComposedNode]]:
    path = _resolve_layout(layout_ref, scenario_dir)
    source = _display_path(path)
    try:
        document = parse.parse_file(
            path,
            canvas_width=viewport[0],
            canvas_height=viewport[1],
            source_path_override=source,
        )
    except FileNotFoundError as error:
        raise ScenarioError(
            "SCENARIO-LAYOUT-MISSING",
            f"layout does not resolve: {layout_ref}",
            source,
        ) from error
    except parse.LayoutSyntaxError as error:
        raise ScenarioError(
            "SCENARIO-SCHEMA-INVALID",
            f"layout syntax is invalid: {error}",
            source,
        ) from error

    roots = [
        wrapped
        for wrapped in (_wrap_widget(root, source) for root in document.roots)
        if wrapped is not None
    ]
    if not roots:
        raise ScenarioError(
            "SCENARIO-SCHEMA-INVALID",
            "layout contains no widget roots",
            source,
        )
    return path, roots


def _walk(nodes: list[ComposedNode]):
    for node in nodes:
        yield node
        yield from _walk(node.children)


def _find_named(nodes: list[ComposedNode], name: str) -> list[ComposedNode]:
    return [node for node in _walk(nodes) if node.node.name == name]


def _find_mount(
    nodes: list[ComposedNode],
    name: str,
    scenario_source: str,
) -> ComposedNode:
    matches = _find_named(nodes, name)
    if len(matches) != 1:
        raise ScenarioError(
            "SCENARIO-MOUNT-MISSING",
            f"mount {name!r} must resolve to exactly one widget; found {len(matches)}",
            scenario_source,
        )
    return matches[0]


def _find_binding_target(
    nodes: list[ComposedNode],
    name: str,
    scenario_source: str,
) -> ComposedNode:
    matches = _find_named(nodes, name)
    if len(matches) != 1:
        raise ScenarioError(
            "SCENARIO-BINDING-MISSING",
            f"widget {name!r} must resolve to exactly one binding target; found {len(matches)}",
            scenario_source,
        )
    return matches[0]


def _compose_subview(
    subview_id: str,
    mount_scope: list[ComposedNode],
    subviews: dict[str, dict[str, Any]],
    scenario_dir: Path,
    scenario_source: str,
    viewport: tuple[int, int],
    active_ids: tuple[str, ...],
    active_layouts: tuple[Path, ...],
) -> None:
    if subview_id in active_ids:
        chain = " -> ".join((*active_ids, subview_id))
        raise ScenarioError(
            "SCENARIO-CYCLE",
            f"subview cycle detected: {chain}",
            scenario_source,
        )

    subview = subviews[subview_id]
    mount = _find_mount(mount_scope, subview["mount"], scenario_source)
    layout_path, child_roots = _parse_layout(
        subview["layout"], scenario_dir, viewport
    )
    if layout_path in active_layouts:
        chain = " -> ".join(_display_path(path) for path in (*active_layouts, layout_path))
        raise ScenarioError(
            "SCENARIO-CYCLE",
            f"layout cycle detected: {chain}",
            _display_path(layout_path),
        )

    mount.children.extend(child_roots)
    next_ids = (*active_ids, subview_id)
    next_layouts = (*active_layouts, layout_path)
    for child_id in subview["subviews"]:
        _compose_subview(
            child_id,
            child_roots,
            subviews,
            scenario_dir,
            scenario_source,
            viewport,
            next_ids,
            next_layouts,
        )


def _set_binding(target: ComposedNode, binding: dict[str, Any]) -> None:
    property_name = binding["property"]
    value = binding["value"]
    target.node.attrs[property_name] = [value]
    target.runtime_state.setdefault("bindings", {})[property_name] = value


def _compose_collections(
    roots: list[ComposedNode],
    state: dict[str, Any],
    collections: dict[str, dict[str, Any]],
    scenario_dir: Path,
    scenario_source: str,
    viewport: tuple[int, int],
) -> None:
    for selection in state.get("collections", []):
        collection = collections[selection["collection"]]
        mount = _find_mount(roots, collection["mount"], scenario_source)
        items = {item["key"]: item for item in collection["items"]}
        for item_key in selection["items"]:
            item = items[item_key]
            _, item_roots = _parse_layout(item["layout"], scenario_dir, viewport)
            if len(item_roots) != 1:
                raise ScenarioError(
                    "SCENARIO-SCHEMA-INVALID",
                    f"collection item {item_key!r} must contain exactly one widget root",
                    _display_path(scenario_dir / item["layout"]),
                )
            item_root = item_roots[0]
            position = item["position"]
            item_root.node.attrs["position"] = [position["x"], position["y"]]
            item_root.node.attrs["size"] = [position["width"], position["height"]]
            item_root.runtime_state["position"] = dict(position)
            item_root.collection_id = collection["id"]
            item_root.item_key = item_key
            for binding in item["bindings"]:
                target = _find_binding_target(
                    [item_root], binding["widget"], scenario_source
                )
                _set_binding(target, binding)
            mount.children.append(item_root)


def _apply_state(
    roots: list[ComposedNode],
    state: dict[str, Any],
    scenario_source: str,
) -> None:
    for binding in state.get("bindings", []):
        target = _find_binding_target(roots, binding["widget"], scenario_source)
        _set_binding(target, binding)

    for rule in state.get("visibility", []):
        target = _find_binding_target(roots, rule["widget"], scenario_source)
        target.node.attrs["visible"] = [1 if rule["visible"] else 0]
        target.runtime_state["visible"] = rule["visible"]

    for rule in state.get("colors", []):
        target = _find_binding_target(roots, rule["widget"], scenario_source)
        target.node.attrs["color"] = list(rule["color"])
        target.node.attrs["alpha"] = [rule["alpha"]]
        target.runtime_state["color"] = list(rule["color"])
        target.runtime_state["alpha"] = rule["alpha"]

    for rule in state.get("positions", []):
        target = _find_binding_target(roots, rule["widget"], scenario_source)
        target.node.attrs["position"] = [rule["x"], rule["y"]]
        target.node.attrs["size"] = [rule["width"], rule["height"]]
        target.runtime_state["position"] = {
            "x": rule["x"],
            "y": rule["y"],
            "width": rule["width"],
            "height": rule["height"],
        }

    for rule in state.get("tabs", []):
        target = _find_binding_target(roots, rule["widget"], scenario_source)
        target.runtime_state["tab_active"] = rule["active"]

    for rule in state.get("controls", []):
        target = _find_binding_target(roots, rule["widget"], scenario_source)
        target.runtime_state["enabled"] = rule["enabled"]

    for rule in state.get("modal", []):
        target = _find_binding_target(roots, rule["widget"], scenario_source)
        target.node.attrs["visible"] = [1 if rule["visible"] else 0]
        target.runtime_state["modal_visible"] = rule["visible"]

    for rule in state.get("pointer", []):
        target = _find_binding_target(roots, rule["widget"], scenario_source)
        target.runtime_state["pointer"] = rule["state"]


def _stable_widget_id(ancestry: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        ancestry,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "widget-" + hashlib.sha256(payload).hexdigest()


def _serialize_nodes(
    nodes: list[ComposedNode],
    parent_id: str | None,
    parent_width: float,
    parent_height: float,
    ancestry: list[dict[str, Any]],
    seen_ids: set[str],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for sibling_index, composed in enumerate(nodes):
        descriptor = {
            "sibling_index": sibling_index,
            "name": composed.node.name,
            "type": composed.node.cls,
        }
        node_ancestry = [*ancestry, descriptor]
        widget_id = _stable_widget_id(node_ancestry)
        if widget_id in seen_ids:
            raise ScenarioError(
                "SCENARIO-DUPLICATE-WIDGET-ID",
                f"widget id {widget_id!r} is duplicated",
                composed.source_path,
            )
        seen_ids.add(widget_id)

        geometry = parse.resolve_geometry(
            composed.node,
            parent_width,
            parent_height,
        )
        child_width = parent_width
        child_height = parent_height
        if geometry is not None:
            child_width = geometry["size"]["width"]
            child_height = geometry["size"]["height"]

        serialized: dict[str, Any] = {
            "attrs": composed.node.attrs,
            "children": _serialize_nodes(
                composed.children,
                widget_id,
                child_width,
                child_height,
                node_ancestry,
                seen_ids,
            ),
            "geometry": geometry,
            "id": widget_id,
            "name": composed.node.name,
            "parent_id": parent_id,
            "runtime_state": composed.runtime_state,
            "sibling_index": sibling_index,
            "source": {
                "column": composed.node.column,
                "line": composed.node.line,
                "path": composed.source_path,
            },
            "type": composed.node.cls,
        }
        if composed.collection_id:
            serialized["collection_id"] = composed.collection_id
            serialized["item_key"] = composed.item_key
        result.append(serialized)
    return result


def _count_nodes(nodes: list[dict[str, Any]]) -> int:
    return sum(1 + _count_nodes(node["children"]) for node in nodes)


def _count_collection_items(nodes: list[dict[str, Any]]) -> int:
    return sum(
        (1 if node.get("collection_id") and node.get("item_key") else 0)
        + _count_collection_items(node["children"])
        for node in nodes
    )


def compose_scenario(
    path: Path | str,
    state_name: str | None = None,
    viewport: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Compose one named scenario state into a deterministic widget tree."""
    scenario_path = Path(path).resolve()
    scenario_source = _display_path(scenario_path)
    document = load_scenario(scenario_path)
    scenario_id = document["scenario_id"]
    try:
        selected_state = state_name or document["default_state"]
        state = next(
            (item for item in document["states"] if item["name"] == selected_state),
            None,
        )
        if state is None:
            raise ScenarioError(
                "SCENARIO-STATE-MISSING",
                f"state {selected_state!r} is not declared",
                scenario_source,
                scenario_id,
            )

        if viewport is None:
            viewport = (
                document["viewport"]["width"],
                document["viewport"]["height"],
            )
        if (
            len(viewport) != 2
            or any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in viewport)
        ):
            raise ScenarioError(
                "SCENARIO-SCHEMA-INVALID",
                "viewport must contain two positive integers",
                scenario_source,
                scenario_id,
            )

        scenario_dir = scenario_path.parent
        entry_path, roots = _parse_layout(
            document["entrypoint"]["layout"], scenario_dir, viewport
        )
        subviews = {item["id"]: item for item in document["subviews"]}
        for subview_id in document["entrypoint"]["subviews"]:
            _compose_subview(
                subview_id,
                roots,
                subviews,
                scenario_dir,
                scenario_source,
                viewport,
                (),
                (entry_path,),
            )

        collections = {item["id"]: item for item in document["collections"]}
        _compose_collections(
            roots,
            state,
            collections,
            scenario_dir,
            scenario_source,
            viewport,
        )
        _apply_state(roots, state, scenario_source)

        serialized_roots = _serialize_nodes(
            roots,
            None,
            viewport[0],
            viewport[1],
            [],
            set(),
        )
        return {
            "entrypoint": _display_path(entry_path),
            "roots": serialized_roots,
            "scenario": scenario_source,
            "scenario_id": scenario_id,
            "schema_version": SCHEMA_VERSION,
            "state": selected_state,
            "stats": {
                "collection_item_count": _count_collection_items(serialized_roots),
                "widget_count": _count_nodes(serialized_roots),
            },
            "viewport": {
                "height": viewport[1],
                "width": viewport[0],
            },
        }
    except ScenarioError as error:
        if not error.scenario_id:
            error.scenario_id = scenario_id
        raise


def composition_bytes(
    path: Path | str,
    state_name: str | None = None,
    viewport: tuple[int, int] | None = None,
) -> bytes:
    composition = compose_scenario(path, state_name=state_name, viewport=viewport)
    return (json.dumps(composition, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _parse_viewport(value: str, source: str) -> tuple[int, int]:
    match = re.fullmatch(r"([1-9][0-9]*)x([1-9][0-9]*)", value)
    if match is None:
        raise ScenarioError(
            "SCENARIO-SCHEMA-INVALID",
            f"viewport {value!r} must use WIDTHxHEIGHT with positive integers",
            source,
        )
    return int(match.group(1)), int(match.group(2))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and compose a dayz-ui-scenario-v1 document.",
    )
    parser.add_argument("--scenario", required=True, help="scenario JSON path")
    parser.add_argument("--viewport", required=True, help="composition viewport WIDTHxHEIGHT")
    parser.add_argument("--state", default=None, help="named state; defaults to document default_state")
    parser.add_argument("--report", default=None, help="write the JSON report here")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    scenario_path = Path(args.scenario)
    scenario_source = _display_path(scenario_path)
    composition: dict[str, Any] | None = None
    findings: list[dict[str, str]] = []
    viewport: tuple[int, int] | None = None

    try:
        viewport = _parse_viewport(args.viewport, scenario_source)
        composition = compose_scenario(
            scenario_path,
            state_name=args.state,
            viewport=viewport,
        )
    except ScenarioError as error:
        findings.append(finding(error))

    report: dict[str, Any] = {
        "command": "dayz-ui-lab scenario",
        "composition": composition,
        "findings": findings,
        "scenario": scenario_source,
        "schema_version": SCHEMA_VERSION,
        "state": composition["state"] if composition is not None else (args.state or ""),
        "verdict": "PASS" if not findings else "FAIL",
        "viewport": (
            {"height": viewport[1], "width": viewport[0]}
            if viewport is not None
            else args.viewport
        ),
    }

    if composition is not None:
        stats = composition["stats"]
        size = composition["viewport"]
        print(
            f"scenario: {composition['scenario_id']} state={composition['state']} "
            f"viewport={size['width']}x{size['height']} widgets={stats['widget_count']}"
        )
        print(json.dumps(composition, indent=2, sort_keys=True))
    else:
        for item in findings:
            print(f"  {item['code']} | {item['source'] or '-'} | {item['message']}")

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_bytes(
            (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
        )

    print(f"verdict={report['verdict']}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
