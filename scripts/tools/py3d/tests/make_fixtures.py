#!/usr/bin/env python3
"""Write the synthetic .p3d fixtures into tests/fixtures/.
No Bohemia Interactive asset is used.

Deterministic: the same output on every run. The fixtures are NOT
committed; this script is the source. Use: python3 tests/make_fixtures.py
"""

import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TESTS_DIR)
sys.path.insert(0, os.path.dirname(TESTS_DIR))

import py3d  # noqa: E402
from builders import (build_cube_p3d, build_icosphere_p3d,  # noqa: E402
                      build_multilod_p3d, build_multilod_v2_p3d)

FIXTURES = {
    "cube.p3d": build_cube_p3d,
    "icosphere.p3d": build_icosphere_p3d,
    "multilod.p3d": build_multilod_p3d,
    "multilod_v2.p3d": build_multilod_v2_p3d,
}


def main(out_dir=None):
    assert py3d.IS_DAYZ_FORK
    out_dir = out_dir or os.path.join(TESTS_DIR, "fixtures")
    os.makedirs(out_dir, exist_ok=True)
    for name, builder in FIXTURES.items():
        path = os.path.join(out_dir, name)
        with open(path, "wb") as f:
            builder(py3d).write(f)
        print("%s  (%d bytes)" % (path, os.path.getsize(path)))
    return out_dir


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
