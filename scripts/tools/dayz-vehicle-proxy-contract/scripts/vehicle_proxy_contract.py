from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
from typing import Sequence
import uuid

import numpy as np

from vehicle_proxy import audit as audit_module
from vehicle_proxy.audit import AuditInputError, AuditResult
from vehicle_proxy.engine import find_animation_overlaps, find_property_findings
from vehicle_proxy.geometry import apply_matrix, classify_fit, fit_surface
from vehicle_proxy.manifest import ManifestError, VehicleManifest, load_manifest
from vehicle_proxy.preview import write_previews
from vehicle_proxy.pbo import verify_paths_against_pbo
from vehicle_proxy.repair import RepairRefused, plan_repairs, stage_repairs
from vehicle_proxy.reporting import atomic_json, write_reports


class UsageError(ValueError):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UsageError(message)


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="vehicle_proxy_contract.py")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("audit", "preview"):
        command = commands.add_parser(name)
        command.add_argument("--manifest", required=True)
        command.add_argument("--out", required=True)
    repair = commands.add_parser("repair")
    repair.add_argument("--manifest", required=True)
    repair.add_argument("--staging", required=True)
    repair.add_argument(
        "--operation",
        required=True,
        choices=("set-autocenter-zero", "yaw180", "affine-fit"),
    )
    commands.add_parser("self-test")
    return parser


def _load(path: str) -> VehicleManifest:
    try:
        return load_manifest(Path(path))
    except ManifestError as error:
        raise AuditInputError(str(error)) from error
    except OSError as error:
        raise AuditInputError(f"cannot read manifest {path}: {error}") from error


def _status(result: AuditResult) -> int:
    return 0 if result.overall_status == "PASS" else 1


def _audit_command(manifest: VehicleManifest, out: Path) -> int:
    result = audit_module.audit(manifest)
    write_reports(result, out)
    return _status(result)


def _preview_command(manifest: VehicleManifest, out: Path) -> int:
    result = audit_module.audit(manifest)
    write_previews(result, out)
    return _status(result)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _validate_staging(manifest: VehicleManifest, raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        raise AuditInputError(f"staging root must be absolute: {path}")
    requested = Path(os.path.abspath(os.fspath(path)))
    if os.path.lexists(requested):
        raise AuditInputError(f"staging root already exists: {requested}")
    try:
        addon_root = manifest.addon_root.resolve(strict=True)
        staging = requested.resolve(strict=False)
    except (OSError, RuntimeError) as error:
        raise AuditInputError(f"cannot resolve staging boundary: {error}") from error
    if _is_within(staging, addon_root):
        raise AuditInputError(
            f"staging root must be outside addon root {addon_root}: {staging}"
        )
    return requested


def _node_key(node_audit) -> tuple[str, float]:
    return node_audit.node.piece, node_audit.node.host_lod


def _finding_operation(finding, node_audit) -> set[str]:
    if (finding.piece, finding.host_lod) != _node_key(node_audit):
        return set()
    if finding.code == "ALIGNMENT-MISMATCH":
        return set(node_audit.eligible_operations).intersection({"yaw180", "affine-fit"})
    if finding.code == "ENGINE-AUTOCENTER-UNCONFIRMED":
        return set(node_audit.eligible_operations).intersection({"set-autocenter-zero"})
    return set()


def _directory_identity(path: Path) -> tuple[int, int]:
    stat_result = os.stat(path, follow_symlinks=False)
    return stat_result.st_dev, stat_result.st_ino


def _cleanup_owned_staging(
    staging: Path, owned_identity: tuple[int, int]
) -> None:
    """Quarantine by rename and delete only the committed directory identity."""
    if not os.path.lexists(staging):
        return
    quarantine = staging.with_name(
        f".{staging.name}.vehicle-proxy-cleanup-{uuid.uuid4().hex}"
    )
    try:
        os.rename(staging, quarantine)
    except OSError:
        return
    try:
        quarantined_identity = _directory_identity(quarantine)
    except OSError:
        quarantined_identity = None
    if quarantined_identity == owned_identity:
        try:
            shutil.rmtree(quarantine)
        except OSError:
            pass
        return
    if not os.path.lexists(staging):
        try:
            os.rename(quarantine, staging)
        except OSError:
            pass


def _repair_command(
    manifest: VehicleManifest, staging: Path, operation: str
) -> int:
    result = audit_module.audit(manifest)
    if not result.source_available:
        raise AuditInputError("repair requires complete source provenance")

    eligible = [
        item for item in result.nodes if operation in item.eligible_operations
    ]
    if not eligible:
        return 1

    fit_matrices = None
    if operation == "affine-fit":
        fit_matrices = {
            _node_key(item): item.affine_matrix for item in eligible
        }
    try:
        planned = plan_repairs(
            tuple(item.node for item in eligible),
            operation,
            fit_matrices=fit_matrices,
        )
    except RepairRefused as error:
        raise AuditInputError(str(error)) from error

    selected_keys = {_node_key(item) for item in eligible}
    unresolved = []
    blocked = []
    for finding in result.findings:
        if finding.severity != "ERROR":
            continue
        operations = set()
        for node_audit in result.nodes:
            operations.update(_finding_operation(finding, node_audit))
        repaired = (
            (finding.piece, finding.host_lod) in selected_keys
            and operation in operations
        )
        if repaired:
            continue
        unresolved.append(finding)
        if finding.code == "ENGINE-ANIMATION-OVERLAP":
            continue
        if (
            operation == "set-autocenter-zero"
            and finding.code == "ALIGNMENT-MISMATCH"
            and (finding.piece, finding.host_lod) in selected_keys
        ):
            continue
        if operations and operation not in operations:
            continue
        blocked.append(finding)
    if blocked:
        return 1

    repair_plan = {
        "vehicle": result.vehicle,
        "operation": operation,
        "operations": [
            {
                "piece": item.node.piece,
                "host_lod": item.node.host_lod,
                "source": str(item.node.proxy_path),
                "destination": str(staging / item.node.addon_relative_path),
                "fit_matrix": item.fit_matrix,
            }
            for item in planned
        ],
        "unresolved": [finding.as_dict() for finding in unresolved],
        "overall_status": "FAIL" if unresolved else "PASS",
    }
    try:
        json.dumps(repair_plan, allow_nan=False, sort_keys=True)
    except (TypeError, ValueError) as error:
        raise AuditInputError(f"repair plan is not strict JSON: {error}") from error

    try:
        stage_repairs(planned, staging)
    except RepairRefused as error:
        raise AuditInputError(str(error)) from error
    try:
        owned_identity = _directory_identity(staging)
    except OSError as error:
        raise AuditInputError(
            f"cannot capture committed staging identity {staging}: {error}"
        ) from error
    try:
        atomic_json(staging / "repair-plan.json", repair_plan)
    except Exception:
        _cleanup_owned_staging(staging, owned_identity)
        raise
    return 1 if unresolved else 0


def _self_test() -> dict[str, object]:
    reference = np.asarray(
        (
            (0.0, 0.0, 0.0),
            (2.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 3.0),
            (1.0, 2.0, 3.0),
        ),
        dtype=float,
    )
    thresholds = type(
        "SelfTestThresholds",
        (),
        {
            "translation_m": 0.01,
            "rotation_deg": 0.1,
            "scale_error": 0.005,
            "p95_m": 0.05,
        },
    )()
    positive_metrics = fit_surface(
        reference, reference.copy(), {"identity": audit_module.IDENTITY}
    )
    positive = classify_fit(positive_metrics, thresholds).passes

    offset = np.asarray((0.4, -0.2, 0.1))
    translation_metrics = fit_surface(
        reference,
        reference + offset,
        {"identity": audit_module.IDENTITY},
    )
    translation_classification = classify_fit(translation_metrics, thresholds)
    translation_discriminates = (
        translation_classification.repairable
        and not translation_classification.passes
        and np.allclose(translation_metrics.translation, -offset, atol=1.0e-5)
    )

    candidate = apply_matrix(reference, audit_module.YAW180)
    negative_metrics = fit_surface(
        reference,
        candidate,
        {"identity": audit_module.IDENTITY, "yaw180": audit_module.YAW180},
    )
    negative_classification = classify_fit(negative_metrics, thresholds)
    yaw_discriminates = (
        negative_metrics.seed == "yaw180"
        and negative_classification.repairable
        and not negative_classification.passes
    )

    property_lod = type(
        "SelfTestPropertyLod", (), {"resolution": 0.0, "properties": {}}
    )()
    property_findings = find_property_findings(
        (property_lod,), (("autocenter", "0"),)
    )
    autocenter_discriminates = (
        len(property_findings) == 1
        and property_findings[0].code == "ENGINE-AUTOCENTER-UNCONFIRMED"
    )

    class Point:
        pass

    class Vertex:
        def __init__(self, point_index: int):
            self.point_index = point_index

    class Face:
        def __init__(self):
            self.vertices = [Vertex(0), Vertex(1), Vertex(2)]

    class Selection:
        def __init__(self, points, face):
            self.points = {point: 1 for point in points}
            self.faces = {face: 1}

    points = [Point(), Point(), Point()]
    face = Face()
    proxy_name = "proxy:FIXTURE\\data\\proxy\\body.001"
    proxy_selection = Selection(points, face)
    animation_lod = type("SelfTestAnimationLod", (), {})()
    animation_lod.resolution = 0.0
    animation_lod.points = points
    animation_lod.faces = [face]
    animation_lod.selections = {
        proxy_name: proxy_selection,
        "mph": Selection(points, face),
    }
    animation_lod.get_proxies = lambda: (
        {
            "name": proxy_name,
            "path": "FIXTURE\\data\\proxy\\body",
        },
    )
    animation_findings = find_animation_overlaps(
        animation_lod, {"mph": ("Speed",)}, {}
    )
    animation_discriminates = (
        len(animation_findings) == 1
        and animation_findings[0].code == "ENGINE-ANIMATION-OVERLAP"
    )

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "data" / "item.bin"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"source")
        deployed = root / "fixture.pbo"
        name = b"data\\item.bin\x00"
        stale = b"stale"
        deployed.write_bytes(
            name
            + struct.pack("<5I", 0, len(stale), 0, 0, len(stale))
            + b"\x00"
            + struct.pack("<5I", 0, 0, 0, 0, 0)
            + stale
        )
        pbo_findings = verify_paths_against_pbo(deployed, root, (source,))
    pbo_discriminates = (
        len(pbo_findings) == 1
        and pbo_findings[0].code == "PBO-HASH-MISMATCH"
    )
    return {
        "positive": bool(positive),
        "controls": {
            "animation_overlap": bool(animation_discriminates),
            "autocenter": bool(autocenter_discriminates),
            "pbo_stale": bool(pbo_discriminates),
            "translation": bool(translation_discriminates),
            "yaw180": bool(yaw_discriminates),
        },
    }


def _self_test_status() -> int:
    try:
        result = _self_test()
        if (
            type(result) is not dict
            or set(result) != {"positive", "controls"}
            or type(result["positive"]) is not bool
            or type(result["controls"]) is not dict
            or set(result["controls"])
            != {
                "animation_overlap",
                "autocenter",
                "pbo_stale",
                "translation",
                "yaw180",
            }
            or any(type(value) is not bool for value in result["controls"].values())
        ):
            return 3
        if not result["positive"]:
            return 3
        if not all(result["controls"].values()):
            return 2
        return 0
    except Exception:
        return 3


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
    except UsageError as error:
        print(f"usage error: {error}", file=sys.stderr)
        return 64

    if arguments.command == "self-test":
        return _self_test_status()

    try:
        manifest = _load(arguments.manifest)
        if arguments.command == "audit":
            return _audit_command(manifest, Path(arguments.out))
        if arguments.command == "preview":
            return _preview_command(manifest, Path(arguments.out))
        staging = _validate_staging(manifest, arguments.staging)
        return _repair_command(manifest, staging, arguments.operation)
    except AuditInputError as error:
        print(f"input error: {error}", file=sys.stderr)
        return 4
    except Exception as error:
        print(
            f"internal error: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
