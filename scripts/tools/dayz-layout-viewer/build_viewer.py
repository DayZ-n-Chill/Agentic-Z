"""Script-path entry: python tools/dayz-layout-viewer/build_viewer.py <layout>."""

from __future__ import annotations

import sys
from pathlib import Path

_TOOL_ROOT = Path(__file__).resolve().parent
_UI_LAB_ROOT = Path(__file__).resolve().parent.parent / "dayz-ui-lab"
for _path in (_TOOL_ROOT, _UI_LAB_ROOT):
    _text = str(_path)
    if _text not in sys.path:
        sys.path.insert(0, _text)

from dayz_layout_viewer.viewer import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
