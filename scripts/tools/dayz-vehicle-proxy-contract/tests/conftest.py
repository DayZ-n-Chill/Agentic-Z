"""Make the tests import the py3d copy in scripts/tools/py3d.

A different py3d may be installed in site-packages (the PyPI release lacks
parts of the API used here, for example LOD.new_selection), so the repo copy
is put first on sys.path and any already imported py3d from elsewhere is
dropped.
"""
import os
from pathlib import Path
import sys


PY3D_ROOT = (Path(__file__).resolve().parents[2] / "py3d").resolve()

value = str(PY3D_ROOT)
if value in sys.path:
    sys.path.remove(value)
sys.path.insert(0, value)

# The tests also run the CLI in child processes, which inherit the environment.
_existing = os.environ.get("PYTHONPATH", "")
if value not in _existing.split(os.pathsep):
    os.environ["PYTHONPATH"] = value + (os.pathsep + _existing if _existing else "")

loaded = sys.modules.get("py3d")
if loaded is not None:
    origin = Path(getattr(loaded, "__file__", "") or "").resolve()
    if PY3D_ROOT not in origin.parents:
        for name in [n for n in sys.modules if n == "py3d" or n.startswith("py3d.")]:
            del sys.modules[name]
