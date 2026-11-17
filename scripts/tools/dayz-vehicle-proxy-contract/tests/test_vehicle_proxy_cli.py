from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import py3d


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
CLI = SCRIPTS / "vehicle_proxy_contract.py"
sys.path.insert(0, str(SCRIPTS))

from vehicle_proxy_fixtures import make_complete_cli_fixture, write_test_pbo


def _run(*arguments: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *(str(item) for item in arguments)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )


def _run_python(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT,
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )


def _manifest_payload(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_manifest(path: pathlib.Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _refresh_pbo(payload: dict) -> None:
    addon_root = pathlib.Path(payload["addon_root"])
    host = pathlib.Path(payload["host_p3d"])
    proxy_root = addon_root / "data" / "proxy"
    entries = {
        "data\\host.p3d": host.read_bytes(),
        **{
            str(path.relative_to(addon_root)).replace("/", "\\"): path.read_bytes()
            for path in proxy_root.glob("*.p3d")
        },
    }
    write_test_pbo(
        pathlib.Path(payload["deployed_pbo"]),
        entries,
    )


def _save_model(path: pathlib.Path, model: py3d.P3D) -> None:
    temporary = path.with_suffix(".new.p3d")
    model.save(temporary, verify=True)
    os.replace(temporary, path)


def _shift_proxy(manifest_path: pathlib.Path, amount: float = 0.25) -> None:
    payload = _manifest_payload(manifest_path)
    proxy = pathlib.Path(payload["addon_root"]) / "data" / "proxy" / "body.p3d"
    with proxy.open("rb") as handle:
        model = py3d.P3D(handle)
    for lod in model.lods:
        for point in lod.points:
            x, y, z = point.coords
            point.coords = (x + amount, y, z)
    _save_model(proxy, model)
    _refresh_pbo(payload)


def _add_animation_overlap(manifest_path: pathlib.Path) -> None:
    payload = _manifest_payload(manifest_path)
    host_path = pathlib.Path(payload["host_p3d"])
    with host_path.open("rb") as handle:
        host = py3d.P3D(handle)
    lod = host.lods[0]
    proxy_name = next(iter(lod.get_proxies()))["name"]
    proxy_selection = lod.selections[proxy_name]
    overlap = lod.new_selection("mph")
    overlap.points = dict(proxy_selection.points)
    overlap.faces = dict(proxy_selection.faces)
    _save_model(host_path, host)

    shim = host_path.parents[1] / "cfgconvert_shim.py"
    shim.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "args = sys.argv[1:]\n"
        "dst = Path(args[args.index('-dst') + 1])\n"
        "dst.write_text('<CfgSkeletons></CfgSkeletons><CfgModels><car>"
        "<Animations><Speed><selection>mph</selection></Speed></Animations>"
        "</car></CfgModels>', encoding='iso-8859-1')\n",
        encoding="utf-8",
    )
    _refresh_pbo(payload)


def _configure_exact_host_animation_fixture(
    manifest_path: pathlib.Path,
    *,
    include_dashboard: bool = False,
) -> None:
    payload = _manifest_payload(manifest_path)
    addon_root = pathlib.Path(payload["addon_root"])
    host_path = pathlib.Path(payload["host_p3d"])
    body_proxy = addon_root / "data" / "proxy" / "body.p3d"
    steering_proxy = addon_root / "data" / "proxy" / "mb_steering.p3d"
    steering_proxy.write_bytes(body_proxy.read_bytes())

    host = py3d.P3D()
    wheel_bindings = (
        (1, "wheel_1_1"),
        (2, "wheel_2_1"),
        (3, "wheel_1_2"),
        (4, "wheel_2_2"),
    )
    allowances = []
    for resolution in range(5):
        lod = py3d.LOD()
        lod.resolution = float(resolution)
        if resolution == 0:
            lod.add_proxy("FIXTURE\\data\\proxy\\body", index=9)
        for index, wheel in wheel_bindings:
            proxy_name = lod.add_proxy(
                f"FIXTURE\\data\\proxy\\{wheel}", index=index
            )
            overlap = lod.new_selection(wheel)
            overlap.points = dict(lod.selections[proxy_name].points)
            overlap.faces = dict(lod.selections[proxy_name].faces)
            allowances.append(
                {
                    "host_lod": float(resolution),
                    "proxy_selection_name": proxy_name,
                    "animated_selection": wheel,
                }
            )
        if resolution == 0:
            steering_name = lod.add_proxy(
                "FIXTURE\\data\\proxy\\mb_steering", index=6
            )
            drivewheel = lod.new_selection("drivewheel")
            drivewheel.points = dict(lod.selections[steering_name].points)
            drivewheel.faces = dict(lod.selections[steering_name].faces)
            if include_dashboard:
                dashboard_name = lod.add_proxy(
                    "FIXTURE\\data\\proxy\\mb_dash", index=5
                )
                for name in (
                    "mph",
                    "rpm",
                    "fuel_1",
                    "oil",
                    "battery",
                    "temp",
                    "lights",
                    "check_engine",
                    "brake",
                ):
                    overlap = lod.new_selection(name)
                    overlap.points = dict(lod.selections[dashboard_name].points)
                    overlap.faces = dict(lod.selections[dashboard_name].faces)
        host.lods.append(lod)
    _save_model(host_path, host)

    steering_piece = json.loads(json.dumps(payload["pieces"][0]))
    steering_piece["name"] = "steering"
    steering_piece["include_host_direct"] = False
    steering_piece["host_direct_material_prefixes"] = []
    steering_piece["allowed_animated_selections"] = ["drivewheel"]
    steering_piece["variants"][0]["expected_proxy_basename"] = "mb_steering"
    payload["pieces"].append(steering_piece)
    payload["allowed_host_animation_overlaps"] = allowances
    _write_manifest(manifest_path, payload)

    animated_names = [wheel for _, wheel in wheel_bindings] + ["drivewheel"]
    if include_dashboard:
        animated_names.extend(
            [
                "mph",
                "rpm",
                "fuel_1",
                "oil",
                "battery",
                "temp",
                "lights",
                "check_engine",
                "brake",
            ]
        )
    animations = "".join(
        f"<A{index}><selection>{name}</selection></A{index}>"
        for index, name in enumerate(animated_names)
    )
    shim = host_path.parents[1] / "cfgconvert_shim.py"
    shim.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "args = sys.argv[1:]\n"
        "dst = Path(args[args.index('-dst') + 1])\n"
        f"dst.write_text({('<CfgSkeletons></CfgSkeletons><CfgModels><car><Animations>' + animations + '</Animations></car></CfgModels>')!r}, encoding='iso-8859-1')\n",
        encoding="utf-8",
    )
    _refresh_pbo(payload)


def _duplicate_declared_host_overlap(manifest_path: pathlib.Path) -> None:
    payload = _manifest_payload(manifest_path)
    host_path = pathlib.Path(payload["host_p3d"])
    with host_path.open("rb") as handle:
        host = py3d.P3D(handle)
    duplicate = py3d.LOD()
    duplicate.resolution = 4.0
    proxy_name = duplicate.add_proxy(
        "FIXTURE\\data\\proxy\\wheel_1_1", index=1
    )
    overlap = duplicate.new_selection("wheel_1_1")
    overlap.points = dict(duplicate.selections[proxy_name].points)
    overlap.faces = dict(duplicate.selections[proxy_name].faces)
    host.lods.append(duplicate)
    _save_model(host_path, host)
    _refresh_pbo(payload)


def _add_host_memory_axis(
    manifest_path: pathlib.Path,
    base: str,
    point_count: int = 2,
    force_new_memory_lod: bool = False,
) -> None:
    payload = _manifest_payload(manifest_path)
    host_path = pathlib.Path(payload["host_p3d"])
    with host_path.open("rb") as handle:
        host = py3d.P3D(handle)
    memory = None
    if not force_new_memory_lod:
        memory = next((lod for lod in host.lods if lod.kind() == "memory"), None)
    if memory is None:
        memory = py3d.LOD()
        memory.resolution = 1.0e15
        host.lods.append(memory)
    points = []
    for index in range(point_count):
        point = py3d.Point()
        point.coords = (0.0, float(index), 0.0)
        point.flags = 0
        point.mass = None
        memory.points.append(point)
        points.append(point)
    selection = memory.new_selection(f"{base}_axis")
    selection.points = {point: 1 for point in points}
    selection.faces = {}
    temporary = host_path.with_suffix(".new.p3d")
    host.save(temporary, verify=False)
    os.replace(temporary, host_path)
    _refresh_pbo(payload)


def _add_proxy_memory_axis(manifest_path: pathlib.Path, base: str) -> None:
    payload = _manifest_payload(manifest_path)
    proxy_path = pathlib.Path(payload["addon_root"]) / "data" / "proxy" / "body.p3d"
    with proxy_path.open("rb") as handle:
        proxy = py3d.P3D(handle)
    memory = py3d.LOD()
    memory.resolution = 1.0e15
    points = []
    for index in range(2):
        point = py3d.Point()
        point.coords = (0.0, float(index), 0.0)
        point.flags = 0
        point.mass = None
        memory.points.append(point)
        points.append(point)
    selection = memory.new_selection(f"{base}_axis")
    selection.points = {point: 1 for point in points}
    selection.faces = {}
    proxy.lods.append(memory)
    temporary = proxy_path.with_suffix(".new.p3d")
    proxy.save(temporary, verify=False)
    os.replace(temporary, proxy_path)
    _refresh_pbo(payload)


def _make_property_repair_fixture(root: pathlib.Path):
    manifest, out = make_complete_cli_fixture(root)
    payload = _manifest_payload(manifest)
    proxy = pathlib.Path(payload["addon_root"]) / "data" / "proxy" / "body.p3d"
    with proxy.open("rb") as handle:
        model = py3d.P3D(handle)
    for lod in model.lods:
        lod.properties.pop("autocenter", None)
    _save_model(proxy, model)
    payload["pieces"][0]["variants"][0]["repairs"] = ["set-autocenter-zero"]
    _write_manifest(manifest, payload)
    _refresh_pbo(payload)
    out.rmdir()
    return manifest, out


def _make_property_repair_with_alignment_fixture(root: pathlib.Path):
    manifest, out = _make_property_repair_fixture(root)
    _shift_proxy(manifest)
    return manifest, out


def _make_two_node_authorization_fixture(root: pathlib.Path):
    manifest, out = make_complete_cli_fixture(root)
    _shift_proxy(manifest)
    payload = _manifest_payload(manifest)
    addon_root = pathlib.Path(payload["addon_root"])

    body_variant = payload["pieces"][0]["variants"][0]
    body_variant["repairs"] = ["affine-fit"]
    body_variant["allowed_fit_components"] = ["rotation"]

    body_proxy = addon_root / "data" / "proxy" / "body.p3d"
    property_proxy = addon_root / "data" / "proxy" / "property.p3d"
    with body_proxy.open("rb") as handle:
        property_model = py3d.P3D(handle)
    for lod in property_model.lods:
        lod.properties.pop("autocenter", None)
        for point in lod.points:
            x, y, z = point.coords
            point.coords = (x - 0.25, y, z)
    _save_model(property_proxy, property_model)

    host_path = pathlib.Path(payload["host_p3d"])
    with host_path.open("rb") as handle:
        host = py3d.P3D(handle)
    host.lods[0].add_proxy("FIXTURE\\data\\proxy\\property", index=2)
    _save_model(host_path, host)

    property_source = root / "property.obj"
    property_source.write_bytes(pathlib.Path(payload["pieces"][0]["source_obj"]).read_bytes())
    second = json.loads(json.dumps(payload["pieces"][0]))
    second["name"] = "property"
    second["source_obj"] = str(property_source.resolve())
    second["source_sha256"] = _sha256(property_source)
    second["variants"][0]["expected_proxy_basename"] = "property"
    second["variants"][0]["repairs"] = ["set-autocenter-zero"]
    second["variants"][0]["allowed_fit_components"] = []
    payload["pieces"].append(second)
    _write_manifest(manifest, payload)
    write_test_pbo(
        pathlib.Path(payload["deployed_pbo"]),
        {
            "data\\host.p3d": host_path.read_bytes(),
            "data\\proxy\\body.p3d": body_proxy.read_bytes(),
            "data\\proxy\\property.p3d": property_proxy.read_bytes(),
        },
    )
    out.rmdir()
    return manifest, out


class TestVehicleProxyCli(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.tempdir = pathlib.Path(self._temporary.name)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def fixture(self, name: str = "fixture") -> tuple[pathlib.Path, pathlib.Path]:
        manifest, out = make_complete_cli_fixture(self.tempdir / name)
        out.rmdir()
        return manifest, out

    def test_exit_64_for_invalid_usage(self):
        self.assertEqual(64, _run().returncode)
        self.assertEqual(64, _run("unknown-command").returncode)

    def test_exit_4_for_missing_manifest_and_no_partial_output(self):
        out = self.tempdir / "out"
        result = _run("audit", "--manifest", self.tempdir / "missing.json", "--out", out)
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertFalse(out.exists())

    def test_exit_0_audit_writes_complete_deterministic_report_set(self):
        manifest, out = self.fixture("first")
        result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(0, result.returncode, result.stderr)
        names = ("report.json", "summary.txt", "lod-overview.json")
        first = {name: (out / name).read_bytes() for name in names}
        for name, data in first.items():
            self.assertTrue(data.endswith(b"\n"), name)

        second_out = self.tempdir / "second-out"
        second = _run("audit", "--manifest", manifest, "--out", second_out)
        self.assertEqual(0, second.returncode, second.stderr)
        self.assertEqual(first, {name: (second_out / name).read_bytes() for name in names})

    def test_allowed_host_axis_error_is_deferred_as_warning(self):
        manifest, out = self.fixture("allowed-axis")
        payload = _manifest_payload(manifest)
        payload["allowed_axis_parent_selections"] = ["damper"]
        _write_manifest(manifest, payload)
        _add_host_memory_axis(manifest, "damper")

        result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        deferred = [
            finding
            for finding in report["findings"]
            if finding["code"] == "P3D-AXIS-SELECTION-DEFERRED"
        ]
        self.assertEqual(1, len(deferred))
        self.assertEqual("WARNING", deferred[0]["severity"])
        self.assertEqual("damper_axis", deferred[0]["measured"]["axis_selection"])
        self.assertEqual("damper", deferred[0]["measured"]["parent_selection"])
        self.assertEqual("ERR_AXIS_SELECTION_MISSING", deferred[0]["measured"]["source_code"])
        self.assertEqual("PASS", report["overall_status"])
        self.assertEqual("PASS", report["alignment_status"])

    def test_unlisted_host_axis_error_is_exit_4_without_report(self):
        manifest, out = self.fixture("unlisted-axis")
        _add_host_memory_axis(manifest, "damper")
        result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertFalse(out.exists())

    def test_allowed_host_axis_requires_exactly_two_points(self):
        manifest, out = self.fixture("short-axis")
        payload = _manifest_payload(manifest)
        payload["allowed_axis_parent_selections"] = ["damper"]
        _write_manifest(manifest, payload)
        _add_host_memory_axis(manifest, "damper", point_count=1)
        result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertFalse(out.exists())

    def test_stale_allowed_host_axis_is_exit_4_without_report(self):
        manifest, out = self.fixture("stale-axis")
        payload = _manifest_payload(manifest)
        payload["allowed_axis_parent_selections"] = ["damper"]
        _write_manifest(manifest, payload)
        result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertFalse(out.exists())

    def test_one_allowance_cannot_defer_two_memory_lod_occurrences(self):
        manifest, out = self.fixture("duplicate-axis-occurrence")
        payload = _manifest_payload(manifest)
        payload["allowed_axis_parent_selections"] = ["damper"]
        _write_manifest(manifest, payload)
        _add_host_memory_axis(manifest, "damper")
        _add_host_memory_axis(manifest, "damper", force_new_memory_lod=True)
        result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertFalse(out.exists())

    def test_host_allowance_does_not_exempt_proxy_axis_error(self):
        manifest, out = self.fixture("proxy-axis")
        payload = _manifest_payload(manifest)
        payload["allowed_axis_parent_selections"] = ["damper"]
        _write_manifest(manifest, payload)
        _add_host_memory_axis(manifest, "damper")
        _add_proxy_memory_axis(manifest, "damper")
        result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertFalse(out.exists())

    def test_unrelated_p3d_error_remains_exit_4_without_report(self):
        manifest, out = self.fixture("unrelated-p3d-error")
        source = "\n".join(
            (
                "import sys",
                f"sys.path.insert(0, {str(SCRIPTS)!r})",
                "import py3d",
                "import vehicle_proxy.audit as audit",
                "import vehicle_proxy_contract as cli",
                "original = py3d.P3D.validate",
                "def invalid(model, *args, **kwargs):",
                "    findings = list(original(model, *args, **kwargs))",
                "    findings.append(py3d.Finding('ERR_UNRELATED', 'ERROR', None, 'opaque'))",
                "    return findings",
                "py3d.P3D.validate = invalid",
                f"raise SystemExit(cli.main(['audit','--manifest',{str(manifest)!r},"
                f"'--out',{str(out)!r}]))",
            )
        )
        result = _run_python(source)
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertFalse(out.exists())

    def test_exit_1_degraded_audit_and_preview_keep_alignment_unknown(self):
        manifest, out = self.fixture()
        payload = _manifest_payload(manifest)
        pathlib.Path(payload["source"]["scene"]).unlink()
        for dependency in payload["source"]["dependencies"]:
            pathlib.Path(dependency["path"]).unlink()
        pathlib.Path(payload["pieces"][0]["source_obj"]).unlink()

        audit_result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(1, audit_result.returncode, audit_result.stderr)
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        self.assertEqual("FAIL", report["overall_status"])
        self.assertEqual("UNKNOWN", report["alignment_status"])

        preview_out = self.tempdir / "preview-out"
        preview_result = _run("preview", "--manifest", manifest, "--out", preview_out)
        self.assertEqual(1, preview_result.returncode, preview_result.stderr)
        pngs = sorted((preview_out / "preview").glob("*.png"))
        self.assertTrue(pngs)
        self.assertTrue(pngs[0].read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

        staging = self.tempdir / "staging"
        repair = _run(
            "repair", "--manifest", manifest, "--staging", staging,
            "--operation", "yaw180",
        )
        self.assertEqual(4, repair.returncode, repair.stderr)
        self.assertFalse(staging.exists())

    def test_existing_source_hash_mismatch_is_exit_4_without_reports(self):
        manifest, out = self.fixture()
        payload = _manifest_payload(manifest)
        pathlib.Path(payload["pieces"][0]["source_obj"]).write_text(
            "v 0 0 0\nv 2 0 0\nv 0 2 0\nf 1 2 3\n", encoding="utf-8"
        )
        result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertFalse((out / "report.json").exists())
        self.assertFalse((out / "summary.txt").exists())
        self.assertFalse((out / "lod-overview.json").exists())

    def test_persistent_model_generation_change_at_pbo_boundary_is_exit_4(self):
        manifest, out = self.fixture()
        source = "\n".join(
            (
                "import sys",
                f"sys.path[:0] = [{str(SCRIPTS)!r}, {str(ROOT / 'tests')!r}]",
                "import vehicle_proxy.audit as audit",
                "import vehicle_proxy_contract as cli",
                "import test_vehicle_proxy_cli as helpers",
                "import pathlib",
                "original = audit.verify_deployed_closure",
                "def changed(manifest, nodes):",
                f"    helpers._shift_proxy(pathlib.Path({str(manifest)!r}), 0.4)",
                "    return original(manifest, nodes)",
                "audit.verify_deployed_closure = changed",
                f"raise SystemExit(cli.main(['audit','--manifest',{str(manifest)!r},"
                f"'--out',{str(out)!r}]))",
            )
        )
        result = _run_python(source)
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("generation", result.stderr.lower())
        self.assertFalse(out.exists())

    def test_declared_obj_geometry_is_parsed_from_accepted_snapshot_bytes(self):
        manifest, out = self.fixture()
        payload = _manifest_payload(manifest)
        source_obj = pathlib.Path(payload["pieces"][0]["source_obj"])
        declared = (
            "v 0.4 0 0\nv 1.4 0 0\nv 0.4 1 0\n"
            "usemtl BODY\nf 1 2 3\n"
        ).encode("utf-8")
        source_obj.write_bytes(declared)
        payload["pieces"][0]["source_sha256"] = hashlib.sha256(declared).hexdigest().upper()
        _write_manifest(manifest, payload)

        unshifted = (
            "v 0 0 0\nv 1 0 0\nv 0 1 0\nusemtl BODY\nf 1 2 3\n"
        ).encode("utf-8")
        source = "\n".join(
            (
                "import sys",
                f"sys.path.insert(0, {str(SCRIPTS)!r})",
                "import pathlib",
                "import vehicle_proxy.audit as audit",
                "import vehicle_proxy_contract as cli",
                "original = audit.load_obj_geometry",
                "def temporary_old_generation(path):",
                "    path = pathlib.Path(path)",
                "    declared = path.read_bytes()",
                f"    path.write_bytes({unshifted!r})",
                "    try:",
                "        return original(path)",
                "    finally:",
                "        path.write_bytes(declared)",
                "audit.load_obj_geometry = temporary_old_generation",
                f"raise SystemExit(cli.main(['audit','--manifest',{str(manifest)!r},"
                f"'--out',{str(out)!r}]))",
            )
        )
        result = _run_python(source)
        self.assertEqual(1, result.returncode, result.stderr)
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        self.assertEqual("FAIL", report["alignment_status"])
        self.assertEqual(
            ["ALIGNMENT-MISMATCH"],
            [item["code"] for item in report["findings"]],
        )
        self.assertEqual(declared, source_obj.read_bytes())

    def test_one_bad_node_emits_one_alignment_mismatch_with_three_layers(self):
        manifest, out = self.fixture()
        _shift_proxy(manifest)
        result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(1, result.returncode, result.stderr)
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        mismatches = [item for item in report["findings"] if item["code"] == "ALIGNMENT-MISMATCH"]
        self.assertEqual(1, len(mismatches))
        self.assertEqual({"raw", "resolved", "union"}, set(mismatches[0]["measured"]))
        self.assertEqual(1, len(report["nodes"]))
        self.assertEqual({"raw", "resolved", "union"}, set(report["nodes"][0]["layers"]))

    def test_animation_only_failure_keeps_alignment_pass(self):
        manifest, out = self.fixture()
        _add_animation_overlap(manifest)
        result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(1, result.returncode, result.stderr)
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        self.assertEqual("FAIL", report["overall_status"])
        self.assertEqual("PASS", report["alignment_status"])
        self.assertEqual(
            ["ENGINE-ANIMATION-OVERLAP"],
            [item["code"] for item in report["findings"]],
        )

    def test_exact_twenty_wheel_allowances_pass_and_nine_dashboard_overlaps_fail(self):
        manifest, out = self.fixture("exact-wheel-allowances")
        _configure_exact_host_animation_fixture(manifest, include_dashboard=True)
        payload = _manifest_payload(manifest)
        self.assertEqual(20, len(payload["allowed_host_animation_overlaps"]))

        result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(1, result.returncode, result.stderr)
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        overlaps = [
            finding
            for finding in report["findings"]
            if finding["code"] == "ENGINE-ANIMATION-OVERLAP"
        ]
        self.assertEqual(9, len(overlaps))
        self.assertTrue(all(finding["severity"] == "ERROR" for finding in overlaps))
        self.assertEqual(
            {
                "battery",
                "brake",
                "check_engine",
                "fuel_1",
                "lights",
                "mph",
                "oil",
                "rpm",
                "temp",
            },
            {finding["measured"]["selection"] for finding in overlaps},
        )
        self.assertTrue(
            all(finding["measured"]["proxy_basename"] == "mb_dash" for finding in overlaps)
        )

    def test_existing_drivewheel_permission_is_lowered_to_exact_host_triple(self):
        manifest, out = self.fixture("lowered-drivewheel")
        _configure_exact_host_animation_fixture(manifest)
        payload = _manifest_payload(manifest)
        self.assertTrue(
            all(
                item["animated_selection"] != "drivewheel"
                for item in payload["allowed_host_animation_overlaps"]
            )
        )

        result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_crossed_wrong_lod_stale_duplicate_and_malformed_allowances_are_input_fatal(self):
        for case in (
            "crossed",
            "wrong-lod",
            "stale",
            "duplicate-normalized",
            "malformed-root",
        ):
            with self.subTest(case=case):
                manifest, out = self.fixture(f"invalid-host-allowance-{case}")
                _configure_exact_host_animation_fixture(manifest)
                payload = _manifest_payload(manifest)
                if case == "crossed":
                    payload["allowed_host_animation_overlaps"][0][
                        "animated_selection"
                    ] = "wheel_2_1"
                elif case == "wrong-lod":
                    payload["allowed_host_animation_overlaps"][0]["host_lod"] = 99
                elif case == "stale":
                    payload["allowed_host_animation_overlaps"].append(
                        {
                            "host_lod": 0,
                            "proxy_selection_name": "proxy:fixture\\data\\proxy\\stale.099",
                            "animated_selection": "stale",
                        }
                    )
                elif case == "duplicate-normalized":
                    first = payload["allowed_host_animation_overlaps"][0]
                    payload["allowed_host_animation_overlaps"].append(
                        {
                            "host_lod": 0.0,
                            "proxy_selection_name": (
                                f" {first['proxy_selection_name'].upper()} "
                            ),
                            "animated_selection": (
                                f" {first['animated_selection'].upper()} "
                            ),
                        }
                    )
                else:
                    payload["allowed_host_animation_overlaps"] = {}
                _write_manifest(manifest, payload)

                result = _run("audit", "--manifest", manifest, "--out", out)
                self.assertEqual(4, result.returncode, result.stderr)
                self.assertFalse((out / "report.json").exists())
                self.assertFalse((out / "summary.txt").exists())
                self.assertFalse((out / "lod-overview.json").exists())

    def test_one_declared_allowance_cannot_cover_two_identical_real_occurrences(self):
        manifest, out = self.fixture("duplicate-real-host-overlap")
        _configure_exact_host_animation_fixture(manifest)
        _duplicate_declared_host_overlap(manifest)

        result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertFalse((out / "report.json").exists())
        self.assertFalse((out / "summary.txt").exists())
        self.assertFalse((out / "lod-overview.json").exists())

    def test_uncovered_overlap_is_a_reported_defect_not_an_input_error(self):
        manifest, out = self.fixture("uncovered-wheel")
        _configure_exact_host_animation_fixture(manifest)
        payload = _manifest_payload(manifest)
        omitted = payload["allowed_host_animation_overlaps"].pop()
        _write_manifest(manifest, payload)

        result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(1, result.returncode, result.stderr)
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        overlaps = [
            finding
            for finding in report["findings"]
            if finding["code"] == "ENGINE-ANIMATION-OVERLAP"
        ]
        self.assertEqual(1, len(overlaps))
        self.assertEqual(omitted["host_lod"], overlaps[0]["host_lod"])
        self.assertEqual(
            omitted["animated_selection"], overlaps[0]["measured"]["selection"]
        )

    def test_preview_publishes_png_without_changing_reports(self):
        manifest, out = self.fixture()
        self.assertEqual(0, _run("audit", "--manifest", manifest, "--out", out).returncode)
        report_before = (out / "report.json").read_bytes()
        report_identity = tuple(
            (out / name).stat().st_ino
            for name in ("report.json", "summary.txt", "lod-overview.json")
        )
        result = _run("preview", "--manifest", manifest, "--out", out)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(report_before, (out / "report.json").read_bytes())
        self.assertEqual(
            report_identity,
            tuple(
                (out / name).stat().st_ino
                for name in ("report.json", "summary.txt", "lod-overview.json")
            ),
        )
        pngs = sorted((out / "preview").glob("*.png"))
        self.assertTrue(pngs)
        self.assertTrue(all(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for path in pngs))

    def test_preview_brackets_existing_report_generation_during_render_and_commit(self):
        for phase in ("render", "commit"):
            with self.subTest(phase=phase):
                manifest, out = self.fixture(f"report-race-{phase}")
                audit_result = _run("audit", "--manifest", manifest, "--out", out)
                self.assertEqual(0, audit_result.returncode, audit_result.stderr)
                foreign = b"foreign generation\n"
                source_lines = [
                    "import sys",
                    f"sys.path.insert(0, {str(SCRIPTS)!r})",
                    "import pathlib",
                    "import vehicle_proxy.preview as preview",
                    "import vehicle_proxy_contract as cli",
                    f"report = pathlib.Path({str(out / 'report.json')!r})",
                ]
                if phase == "render":
                    source_lines.extend(
                        (
                            "original = preview._render_previews",
                            "def raced(result, root):",
                            f"    report.write_bytes({foreign!r})",
                            "    return original(result, root)",
                            "preview._render_previews = raced",
                        )
                    )
                else:
                    source_lines.extend(
                        (
                            "original = preview.os.rename",
                            "def raced(source, destination):",
                            "    original(source, destination)",
                            f"    report.write_bytes({foreign!r})",
                            "preview.os.rename = raced",
                        )
                    )
                source_lines.append(
                    f"raise SystemExit(cli.main(['preview','--manifest',{str(manifest)!r},"
                    f"'--out',{str(out)!r}]))"
                )
                result = _run_python("\n".join(source_lines))
                self.assertEqual(4, result.returncode, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(foreign, (out / "report.json").read_bytes())
                self.assertFalse((out / "preview").exists())

    def test_preexisting_preview_directory_is_exit_4_and_unchanged(self):
        manifest, out = self.fixture()
        preview = out / "preview"
        preview.mkdir(parents=True)
        sentinel = preview / "keep.txt"
        sentinel.write_text("unchanged", encoding="utf-8")
        result = _run("preview", "--manifest", manifest, "--out", out)
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertEqual("unchanged", sentinel.read_text(encoding="utf-8"))

    def test_audit_requires_absent_output_and_preserves_existing_tree(self):
        manifest, out = self.fixture()
        out.mkdir()
        sentinel = out / "foreign.txt"
        sentinel.write_text("unchanged", encoding="utf-8")
        result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertEqual(["foreign.txt"], [item.name for item in out.iterdir()])
        self.assertEqual("unchanged", sentinel.read_text(encoding="utf-8"))

    def test_unexpected_audit_report_and_preview_exceptions_are_exit_4_atomic(self):
        for adapter in ("audit_module.audit", "write_reports", "write_previews"):
            with self.subTest(adapter=adapter):
                manifest, out = self.fixture(adapter.replace(".", "-"))
                command = "preview" if adapter == "write_previews" else "audit"
                source = "\n".join(
                    (
                        "import sys",
                        f"sys.path.insert(0, {str(SCRIPTS)!r})",
                        "import vehicle_proxy_contract as cli",
                        "def boom(*args, **kwargs):",
                        "    raise RuntimeError('adapter boom')",
                        (
                            "cli.audit_module.audit = boom"
                            if adapter == "audit_module.audit"
                            else f"cli.{adapter} = boom"
                        ),
                        f"raise SystemExit(cli.main([{command!r},'--manifest',"
                        f"{str(manifest)!r},'--out',{str(out)!r}]))",
                    )
                )
                result = _run_python(source)
                self.assertEqual(4, result.returncode, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertIn("internal error", result.stderr.lower())
                self.assertFalse(out.exists())

    def test_unexpected_repair_publication_exception_is_exit_4_and_cleans_owned_stage(self):
        manifest, _ = _make_property_repair_fixture(self.tempdir / "repair-boom")
        staging = self.tempdir / "repair-boom-stage"
        source = "\n".join(
            (
                "import sys",
                f"sys.path.insert(0, {str(SCRIPTS)!r})",
                "import vehicle_proxy_contract as cli",
                "def boom(*args, **kwargs):",
                "    raise RuntimeError('adapter boom')",
                "cli.atomic_json = boom",
                f"raise SystemExit(cli.main(['repair','--manifest',{str(manifest)!r},"
                f"'--staging',{str(staging)!r},'--operation','set-autocenter-zero']))",
            )
        )
        result = _run_python(source)
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("internal error", result.stderr.lower())
        self.assertFalse(staging.exists())

    def test_property_repair_stages_selected_node_with_unrepairable_alignment_unresolved(self):
        manifest, _ = _make_property_repair_with_alignment_fixture(
            self.tempdir / "property-with-alignment"
        )
        staging = self.tempdir / "property-with-alignment-stage"

        result = _run(
            "repair",
            "--manifest",
            manifest,
            "--staging",
            staging,
            "--operation",
            "set-autocenter-zero",
        )

        self.assertEqual(1, result.returncode, result.stderr)
        plan_path = staging / "repair-plan.json"
        self.assertTrue(plan_path.is_file(), "property repair did not publish a plan")
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        self.assertEqual("set-autocenter-zero", plan["operation"])
        self.assertEqual("FAIL", plan["overall_status"])
        self.assertEqual(1, len(plan["operations"]))
        self.assertEqual(
            ["ALIGNMENT-MISMATCH"],
            [finding["code"] for finding in plan["unresolved"]],
        )

    def test_property_repair_with_alignment_preserves_digests_and_sets_every_autocenter(self):
        from vehicle_proxy.p3d_graph import geometry_digest, structural_digest

        manifest, _ = _make_property_repair_with_alignment_fixture(
            self.tempdir / "property-invariants"
        )
        payload = _manifest_payload(manifest)
        source = pathlib.Path(payload["addon_root"]) / "data" / "proxy" / "body.p3d"
        staging = self.tempdir / "property-invariants-stage"

        result = _run(
            "repair",
            "--manifest",
            manifest,
            "--staging",
            staging,
            "--operation",
            "set-autocenter-zero",
        )

        self.assertEqual(1, result.returncode, result.stderr)
        destination = staging / source.relative_to(pathlib.Path(payload["addon_root"]))
        self.assertTrue(destination.is_file(), "property repair did not stage its P3D")
        with source.open("rb") as handle:
            before = py3d.P3D(handle)
        with destination.open("rb") as handle:
            after = py3d.P3D(handle)
        self.assertEqual(
            tuple(geometry_digest(lod) for lod in before.lods),
            tuple(geometry_digest(lod) for lod in after.lods),
        )
        self.assertEqual(
            tuple(structural_digest(lod) for lod in before.lods),
            tuple(structural_digest(lod) for lod in after.lods),
        )
        self.assertTrue(all(lod.properties.get("autocenter") == "0" for lod in after.lods))

    def test_nonrepairable_alignment_still_blocks_yaw_without_staging(self):
        manifest, _ = _make_property_repair_with_alignment_fixture(
            self.tempdir / "alignment-blocks-yaw"
        )
        staging = self.tempdir / "alignment-blocks-yaw-stage"

        result = _run(
            "repair",
            "--manifest",
            manifest,
            "--staging",
            staging,
            "--operation",
            "yaw180",
        )

        self.assertEqual(1, result.returncode, result.stderr)
        self.assertFalse(staging.exists())

    def test_nonrepairable_alignment_still_blocks_affine_without_staging(self):
        manifest, _ = _make_property_repair_with_alignment_fixture(
            self.tempdir / "alignment-blocks-affine"
        )
        staging = self.tempdir / "alignment-blocks-affine-stage"
        source = "\n".join(
            (
                "import dataclasses, sys",
                f"sys.path.insert(0, {str(SCRIPTS)!r})",
                "import vehicle_proxy_contract as cli",
                "original_audit = cli.audit_module.audit",
                "original_finding_operation = cli._finding_operation",
                "identity = ((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0))",
                "def injected(manifest):",
                "    result = original_audit(manifest)",
                "    node_audit = result.nodes[0]",
                "    node = dataclasses.replace(node_audit.node, repairs=('set-autocenter-zero', 'affine-fit'), allowed_fit_components=())",
                "    selected = dataclasses.replace(node_audit, node=node, eligible_operations=('set-autocenter-zero', 'affine-fit'), affine_matrix=identity)",
                "    return dataclasses.replace(result, nodes=(selected,))",
                "def nonrepairable(finding, node_audit):",
                "    if finding.code == 'ALIGNMENT-MISMATCH':",
                "        return set()",
                "    return original_finding_operation(finding, node_audit)",
                "cli.audit_module.audit = injected",
                "cli._finding_operation = nonrepairable",
                f"raise SystemExit(cli.main(['repair','--manifest',{str(manifest)!r},"
                f"'--staging',{str(staging)!r},'--operation','affine-fit']))",
            )
        )

        result = _run_python(source)

        self.assertEqual(1, result.returncode, result.stderr)
        self.assertFalse(staging.exists())

    def test_unknown_hard_finding_still_blocks_property_repair_without_staging(self):
        manifest, _ = _make_property_repair_with_alignment_fixture(
            self.tempdir / "unknown-hard-finding"
        )
        staging = self.tempdir / "unknown-hard-finding-stage"
        source = "\n".join(
            (
                "import dataclasses, sys",
                f"sys.path.insert(0, {str(SCRIPTS)!r})",
                "import vehicle_proxy_contract as cli",
                "from vehicle_proxy.audit import AuditFinding",
                "original = cli.audit_module.audit",
                "def injected(manifest):",
                "    result = original(manifest)",
                "    node = result.nodes[0].node",
                "    finding = AuditFinding('UNKNOWN-PROPERTY-HARD', 'ERROR', node.piece, node.host_lod, str(node.proxy_path), {}, {})",
                "    return dataclasses.replace(result, findings=result.findings + (finding,), overall_status='FAIL')",
                "cli.audit_module.audit = injected",
                f"raise SystemExit(cli.main(['repair','--manifest',{str(manifest)!r},"
                f"'--staging',{str(staging)!r},'--operation','set-autocenter-zero']))",
            )
        )

        result = _run_python(source)

        self.assertEqual(1, result.returncode, result.stderr)
        self.assertFalse(staging.exists())

    def test_unselected_node_alignment_still_blocks_property_repair_without_staging(self):
        manifest, _ = _make_two_node_authorization_fixture(
            self.tempdir / "unselected-alignment"
        )
        staging = self.tempdir / "unselected-alignment-stage"

        result = _run(
            "repair",
            "--manifest",
            manifest,
            "--staging",
            staging,
            "--operation",
            "set-autocenter-zero",
        )

        self.assertEqual(1, result.returncode, result.stderr)
        self.assertFalse(staging.exists())

    def test_same_piece_other_host_lod_alignment_still_blocks_property_repair(self):
        manifest, _ = _make_property_repair_with_alignment_fixture(
            self.tempdir / "same-piece-other-lod"
        )
        staging = self.tempdir / "same-piece-other-lod-stage"
        source = "\n".join(
            (
                "import dataclasses, sys",
                f"sys.path.insert(0, {str(SCRIPTS)!r})",
                "import vehicle_proxy_contract as cli",
                "from vehicle_proxy.audit import AuditFinding",
                "original = cli.audit_module.audit",
                "def injected(manifest):",
                "    result = original(manifest)",
                "    node = result.nodes[0].node",
                "    finding = AuditFinding('ALIGNMENT-MISMATCH', 'ERROR', node.piece, node.host_lod + 1.0, str(node.proxy_path), {}, {})",
                "    return dataclasses.replace(result, findings=result.findings + (finding,), overall_status='FAIL')",
                "cli.audit_module.audit = injected",
                f"raise SystemExit(cli.main(['repair','--manifest',{str(manifest)!r},"
                f"'--staging',{str(staging)!r},'--operation','set-autocenter-zero']))",
            )
        )

        result = _run_python(source)

        self.assertEqual(1, result.returncode, result.stderr)
        self.assertFalse(staging.exists())

    def test_repair_never_stages_authorized_but_not_causally_needed_node(self):
        manifest, _ = self.fixture()
        payload = _manifest_payload(manifest)
        payload["pieces"][0]["variants"][0]["repairs"] = ["yaw180"]
        _write_manifest(manifest, payload)
        staging = self.tempdir / "staging"
        result = _run(
            "repair", "--manifest", manifest, "--staging", staging,
            "--operation", "yaw180",
        )
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertFalse(staging.exists())

    def test_denied_affine_component_is_not_eligible_and_blocks_other_stage(self):
        manifest, out = _make_two_node_authorization_fixture(
            self.tempdir / "denied-affine"
        )
        audit_result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(1, audit_result.returncode, audit_result.stderr)
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        body = next(item for item in report["nodes"] if item["piece"] == "body")
        self.assertNotIn("affine-fit", body["eligible_operations"])

        staging = self.tempdir / "denied-affine-stage"
        repair = _run(
            "repair",
            "--manifest",
            manifest,
            "--staging",
            staging,
            "--operation",
            "set-autocenter-zero",
        )
        self.assertEqual(1, repair.returncode, repair.stderr)
        self.assertFalse(staging.exists())

    def test_preexisting_staging_root_is_exit_4_and_unchanged(self):
        manifest, _ = self.fixture()
        staging = self.tempdir / "staging"
        staging.mkdir()
        sentinel = staging / "keep.txt"
        sentinel.write_text("unchanged", encoding="utf-8")
        result = _run(
            "repair", "--manifest", manifest, "--staging", staging,
            "--operation", "yaw180",
        )
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertEqual("unchanged", sentinel.read_text(encoding="utf-8"))

    def test_raced_staging_root_is_not_deleted_by_cli_cleanup(self):
        manifest, _ = self.fixture()
        _shift_proxy(manifest)
        payload = _manifest_payload(manifest)
        variant = payload["pieces"][0]["variants"][0]
        variant["repairs"] = ["affine-fit"]
        variant["allowed_fit_components"] = ["translation"]
        _write_manifest(manifest, payload)
        staging = self.tempdir / "raced-staging"
        source = "\n".join(
            (
                "import sys",
                f"sys.path.insert(0, {str(SCRIPTS)!r})",
                "import pathlib",
                "import vehicle_proxy_contract as cli",
                "from vehicle_proxy.repair import RepairRefused",
                "def raced(plan, root):",
                "    pathlib.Path(root).mkdir()",
                "    (pathlib.Path(root) / 'foreign.txt').write_text('unchanged')",
                "    raise RepairRefused('staging root already exists')",
                "cli.stage_repairs = raced",
                f"raise SystemExit(cli.main(['repair','--manifest',{str(manifest)!r},"
                f"'--staging',{str(staging)!r},'--operation','affine-fit']))",
            )
        )
        result = _run_python(source)
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertEqual(
            "unchanged", (staging / "foreign.txt").read_text(encoding="utf-8")
        )

    def test_postcommit_plan_failure_preserves_swapped_foreign_identity(self):
        manifest, _ = _make_property_repair_fixture(self.tempdir / "postcommit")
        staging = self.tempdir / "postcommit-stage"
        record = self.tempdir / "postcommit-record.json"
        source = "\n".join(
            (
                "import sys",
                f"sys.path.insert(0, {str(SCRIPTS)!r})",
                "import json, os, pathlib",
                "import vehicle_proxy_contract as cli",
                "from vehicle_proxy.audit import AuditInputError",
                "def swapped(path, value):",
                "    root = pathlib.Path(path).parent",
                "    owned = root.with_name(root.name + '-owned-displaced')",
                "    os.rename(root, owned)",
                "    root.mkdir()",
                "    (root / 'foreign.txt').write_text('unchanged')",
                f"    pathlib.Path({str(record)!r}).write_text(json.dumps({{'foreign': str(root), 'owned': str(owned)}}))",
                "    raise AuditInputError('publication failed')",
                "cli.atomic_json = swapped",
                f"raise SystemExit(cli.main(['repair','--manifest',{str(manifest)!r},"
                f"'--staging',{str(staging)!r},'--operation','set-autocenter-zero']))",
            )
        )
        result = _run_python(source)
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        paths = json.loads(record.read_text(encoding="utf-8"))
        foreign = pathlib.Path(paths["foreign"])
        self.assertEqual("unchanged", (foreign / "foreign.txt").read_text(encoding="utf-8"))

    def test_two_host_direct_owners_at_same_host_lod_are_input_ambiguity(self):
        manifest, out = _make_two_node_authorization_fixture(
            self.tempdir / "direct-owners"
        )
        payload = _manifest_payload(manifest)
        partitioned = (
            "v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\n"
            "usemtl CORE_DIRECT\nf 1 2 3\nusemtl DETAIL\nf 1 3 4\n"
        )
        for piece in payload["pieces"]:
            source_path = pathlib.Path(piece["source_obj"])
            source_path.write_text(partitioned, encoding="utf-8")
            piece["source_sha256"] = _sha256(source_path)
            piece["include_host_direct"] = True
            piece["host_direct_material_prefixes"] = ["CORE_"]
            piece["host_direct_material_exact"] = []
        _write_manifest(manifest, payload)

        result = _run("audit", "--manifest", manifest, "--out", out)
        self.assertEqual(4, result.returncode, result.stderr)
        self.assertIn("more than one include_host_direct", result.stderr)
        self.assertFalse(out.exists())

    def test_self_test_exit_0_and_mutated_yaw_seed_exit_2(self):
        self.assertEqual(0, _run("self-test").returncode)
        source = (
            f"import sys; sys.path.insert(0, {str(SCRIPTS)!r}); "
            "import numpy as np; import vehicle_proxy.audit as audit; "
            "audit.YAW180 = np.eye(4); import vehicle_proxy_contract as cli; "
            "raise SystemExit(cli.main(['self-test']))"
        )
        result = _run_python(source)
        self.assertEqual(2, result.returncode, result.stderr)

    def test_self_test_covers_every_contract_negative_control(self):
        source = (
            f"import sys; sys.path.insert(0, {str(SCRIPTS)!r}); "
            "import json; import vehicle_proxy_contract as cli; "
            "print(json.dumps(cli._self_test(), sort_keys=True))"
        )
        result = _run_python(source)
        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["positive"])
        self.assertEqual(
            {
                "animation_overlap",
                "autocenter",
                "pbo_stale",
                "translation",
                "yaw180",
            },
            set(payload["controls"]),
        )
        self.assertTrue(all(payload["controls"].values()))

    def test_self_test_invalid_schema_and_exception_are_exit_3(self):
        cases = (
            "lambda: {'positive': True, 'controls': []}",
            "lambda: (_ for _ in ()).throw(RuntimeError('boom'))",
        )
        for replacement in cases:
            with self.subTest(replacement=replacement):
                source = (
                    f"import sys; sys.path.insert(0, {str(SCRIPTS)!r}); "
                    "import vehicle_proxy_contract as cli; "
                    f"cli._self_test = {replacement}; "
                    "raise SystemExit(cli.main(['self-test']))"
                )
                result = _run_python(source)
                self.assertEqual(3, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
