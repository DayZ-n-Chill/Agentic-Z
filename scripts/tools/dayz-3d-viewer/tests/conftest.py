from pathlib import Path
import sys


TOOL_ROOT = Path(__file__).parents[1]
PY3D_ROOT = Path(__file__).parents[2] / "py3d"
for path in (TOOL_ROOT, PY3D_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)
