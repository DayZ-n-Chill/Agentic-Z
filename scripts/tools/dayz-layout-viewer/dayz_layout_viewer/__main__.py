"""python -m dayz_layout_viewer  /  script-path launch."""

from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap() -> None:
    if __package__ not in {None, ""}:
        return
    tool_root = Path(__file__).resolve().parents[1]
    ui_lab_root = Path(__file__).resolve().parents[2] / "dayz-ui-lab"
    for path in (tool_root, ui_lab_root):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)


_bootstrap()

if __package__ in {None, ""}:
    from dayz_layout_viewer.viewer import main
else:
    from .viewer import main


if __name__ == "__main__":
    raise SystemExit(main())
