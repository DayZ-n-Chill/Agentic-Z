"""Optional-extra and py3d fork gates. Fail with a message, not a traceback."""

from __future__ import annotations

import importlib
import re

from .errors import MissingDependencyError, ViewerError

MINIMUM_PY3D_VERSION = (1, 6, 0)


def require_dayz_py3d(module=None):
    if module is None:
        try:
            module = importlib.import_module("py3d")
        except (ImportError, ModuleNotFoundError) as exc:
            raise MissingDependencyError(
                "the DayZ py3d fork >=1.6.0 is required "
                "(pip install -e tools/py3d). The PyPI package named py3d "
                "is a different library."
            ) from exc
    version_text = getattr(module, "__version__", "")
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version_text)
    version = tuple(int(part) for part in match.groups()) if match else ()
    if getattr(module, "IS_DAYZ_FORK", False) is not True or version < MINIMUM_PY3D_VERSION:
        raise ViewerError(
            "the DayZ py3d fork >=1.6.0 is required "
            "(pip install -e tools/py3d). The PyPI package named py3d "
            "is a different library."
        )
    return module


def require_pillow():
    try:
        from PIL import Image
    except ImportError as exc:
        raise MissingDependencyError(
            "Pillow is required for PAA decoding. "
            "Install it with: pip install 'dayz-3d-viewer[paa]'"
        ) from exc
    return Image
