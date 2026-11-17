import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

from .errors import OdolStrictError


def invoke_worker(payload_path, verified_backend):
    request = {
        "backend_root": os.fspath(verified_backend["root"]),
        "files": verified_backend["files"],
        "payload_path": os.fspath(Path(payload_path).resolve()),
    }
    environment = os.environ.copy()
    package_root = os.fspath(Path(__file__).parents[1])
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        package_root
        if not existing
        else package_root + os.pathsep + existing
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "dayz_odol_strict.worker", "--worker"],
            input=json.dumps(request, separators=(",", ":"), sort_keys=True),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        _failure()
    if completed.returncode != 0 or completed.stderr:
        _failure()
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError:
        _failure()
    if not isinstance(value, dict):
        _failure()
    return value


def _failure():
    raise OdolStrictError(
        "ODOL_BACKEND_FAILURE",
        "isolated backend worker did not return valid JSON",
    )


class _PinnedBackendFinder:
    def __init__(self, root, files):
        self._module_paths = {}
        for item in files:
            relative = Path(item["path"])
            if relative.suffix != ".py" or len(relative.parts) != 1:
                continue
            module_name = relative.stem
            if module_name in self._module_paths:
                raise ImportError("duplicate pinned backend module")
            self._module_paths[module_name] = (root / relative).resolve()
        if "odol_reader" not in self._module_paths:
            raise ImportError("pinned odol_reader module is unavailable")

    def find_spec(self, fullname, path=None, target=None):
        module_path = self._module_paths.get(fullname)
        if module_path is None:
            return None
        return importlib.util.spec_from_file_location(fullname, module_path)

    def module_names(self):
        return tuple(self._module_paths)


def _load_pinned_odol(root, files):
    finder = _PinnedBackendFinder(root, files)
    if any(name in sys.modules for name in finder.module_names()):
        raise ImportError("pinned backend module was already imported")
    spec = finder.find_spec("odol_reader")
    if spec is None or spec.loader is None:
        raise ImportError("pinned odol_reader module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules["odol_reader"] = module
    sys.meta_path.insert(0, finder)
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop("odol_reader", None)
        raise
    finally:
        sys.meta_path.remove(finder)
    return module.ODOL


def _worker_main():
    try:
        request = json.loads(sys.stdin.read())
        root = Path(request["backend_root"]).resolve()
        payload_path = Path(request["payload_path"]).resolve()
        files = request["files"]
        if not root.is_dir() or not payload_path.is_file():
            return 2
        for item in files:
            candidate = (root / item["path"]).resolve()
            if os.path.commonpath((root, candidate)) != os.fspath(root):
                return 2
            if not candidate.is_file() or hashlib.sha256(
                candidate.read_bytes()
            ).hexdigest() != item["sha256"]:
                return 2
        ODOL = _load_pinned_odol(root, files)

        odol = ODOL.from_bytes(payload_path.read_bytes())
        lods = []
        for lod in odol.lods:
            if lod is None:
                lods.append(None)
                continue
            lods.append({
                "face_count": len(lod.faces),
                "material_count": len(lod.materials),
                "material_names": sorted(
                    material.material_name for material in lod.materials
                ),
                "named_properties": sorted(
                    [[name, value] for name, value in lod.named_properties],
                    key=lambda item: (item[0], item[1]),
                ),
                "normal_count": len(lod.normals),
                "proxy_count": len(lod.proxies),
                "resolution": lod.resolution,
                "selection_names": sorted(
                    selection.name for selection in lod.named_selections
                ),
                "vertex_count": len(lod.vertices),
            })
        output = {
            "lod_actual_end": odol.lod_actual_end,
            "lod_end_table": odol.lod_end_table,
            "lod_errors": odol.lod_errors,
            "lod_start_table": odol.lod_start_table,
            "lods": lods,
            "n_lods": odol.n_lods,
            "resolutions": odol.resolutions,
            "version": odol.version,
        }
        sys.stdout.write(
            json.dumps(output, separators=(",", ":"), sort_keys=True)
        )
        return 0
    except Exception:
        return 2


if __name__ == "__main__":
    if sys.argv[1:] != ["--worker"]:
        raise SystemExit(2)
    raise SystemExit(_worker_main())
