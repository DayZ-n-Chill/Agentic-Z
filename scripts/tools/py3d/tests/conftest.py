import importlib.util
import os
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FORK_ROOT = os.path.dirname(TESTS_DIR)

# This copy wins over any py3d in site-packages; tests stay importable.
sys.path.insert(0, TESTS_DIR)
sys.path.insert(0, FORK_ROOT)


@pytest.fixture(scope="session")
def fork():
    import py3d
    assert getattr(py3d, "IS_DAYZ_FORK", False), (
        "the py3d module that got imported is NOT this library "
        "(is site-packages shadowing it?): %r"
        % getattr(py3d, "__file__", None))
    assert py3d.__version__ == "1.10.1"
    return py3d


def _load_bare():
    root = os.environ.get("PY3D_REFERENCE_PATH")
    if not root:
        return None, ("PY3D_REFERENCE_PATH is not set - point it at a "
                      "checkout of the bare codec (plain py3d at revision "
                      "7acd58b)")
    init = os.path.join(root, "py3d", "__init__.py")
    if not os.path.isfile(init):
        return None, "does not exist: %s" % init
    spec = importlib.util.spec_from_file_location("py3d_bare", init)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, None


@pytest.fixture(scope="session")
def bare():
    """The bare codec loaded by path, without pip. When it is not available the
    CANON tests skip with an explicit reason, so the suite stays green
    offline."""
    mod, why = _load_bare()
    if mod is None:
        pytest.skip("byte-identity tests skipped: " + why)
    assert not getattr(mod, "IS_DAYZ_FORK", False), \
        "PY3D_REFERENCE_PATH points at this library, not at the bare codec"
    return mod
