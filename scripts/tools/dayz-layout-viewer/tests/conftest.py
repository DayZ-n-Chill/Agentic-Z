from pathlib import Path
import sys


TOOL_ROOT = Path(__file__).resolve().parents[1]
UI_LAB_ROOT = Path(__file__).resolve().parents[2] / "dayz-ui-lab"
for path in (TOOL_ROOT, UI_LAB_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)
