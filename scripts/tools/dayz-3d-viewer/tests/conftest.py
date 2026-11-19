from pathlib import Path
import sys


TOOL_ROOT = Path(__file__).parents[1]
PY3D_ROOT = Path(__file__).parents[2] / "py3d"
for path in (TOOL_ROOT, PY3D_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

# A different py3d may be installed in site-packages, and a test collected
# earlier in the same run may already have imported it (a py3d from outside
# this repo lacks API these tests use, for example P3D.save and
# LOD.new_selection). Put the repo copy first and drop a py3d that was
# imported from anywhere else.
_py3d_root = PY3D_ROOT.resolve()
_value = str(PY3D_ROOT)
if sys.path[0] != _value:
    if _value in sys.path:
        sys.path.remove(_value)
    sys.path.insert(0, _value)
_loaded = sys.modules.get("py3d")
if _loaded is not None:
    _origin = Path(getattr(_loaded, "__file__", "") or "").resolve()
    if _py3d_root not in _origin.parents:
        for _name in [n for n in sys.modules if n == "py3d" or n.startswith("py3d.")]:
            del sys.modules[_name]
