import json
import subprocess
import sys
from pathlib import Path

from dayz_3d_viewer import MissingDependencyError
from dayz_3d_viewer.deps import require_pillow
from dayz_3d_viewer.__main__ import main

from _support import make_triangle_lod, save_model, write_rgba8888_paa


TOOL_ROOT = Path(__file__).resolve().parents[1]
PY3D_ROOT = Path(__file__).resolve().parents[2] / "py3d"


def _env():
    import os

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(TOOL_ROOT), str(PY3D_ROOT), env.get("PYTHONPATH", "")]
    )
    env["PYTHONUTF8"] = "1"
    return env


def test_cli_p3d_info_and_build_viewer(tmp_path):
    model = save_model(tmp_path / "tri.p3d", [make_triangle_lod()])
    result = subprocess.run(
        [sys.executable, "-m", "dayz_3d_viewer", "p3d-to-glb", str(model), "--info"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_env(),
        check=False,
    )
    assert result.returncode == 0, result.stderr
    info = json.loads(result.stdout)
    assert info["file"] == "tri.p3d"
    assert info["lods"][0]["points"] == 3

    out_dir = tmp_path / "out"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "dayz_3d_viewer",
            "build-viewer",
            str(model),
            "--output",
            str(out_dir),
            "--name",
            "tri",
            "--mode",
            "web",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_env(),
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (out_dir / "tri.glb").is_file()
    html = (out_dir / "tri_viewer.html").read_text(encoding="utf-8")
    assert "tri.glb" in html
    assert str(tmp_path) not in html


def test_cli_paa_and_rvmat(tmp_path):
    pixels = [(255, 0, 0, 255)] * 16
    paa = write_rgba8888_paa(tmp_path / "red.paa", pixels, 4, 4)
    png = tmp_path / "red.png"
    assert main(["paa-to-png", str(paa), str(png)]) == 0
    assert png.is_file()

    rvmat = tmp_path / "led.rvmat"
    rvmat.write_text(
        "diffuse[]={0.1,0.2,0.3,1};\nspecularPower=10;\n",
        encoding="utf-8",
        newline="\n",
    )
    assert main(["parse-rvmat", str(rvmat)]) == 0


def test_missing_pillow_message_has_no_import_error_type():
    try:
        require_pillow()
    except MissingDependencyError as exc:
        assert "Pillow" in str(exc)
        assert "Traceback" not in str(exc)
    else:
        # Pillow is installed in this environment; the helper still exists.
        assert require_pillow() is not None
