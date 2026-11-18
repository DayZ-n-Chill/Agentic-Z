#!/usr/bin/env python3
"""Tests for proxy_frame: canonical triangles, the 90/45/45 tie and round trips.

Run: python -m pytest skills/dayz-model-tools/scripts/test_proxy_frame.py, or python test_proxy_frame.py
(exit 0 = all pass, 1 = a failure). Needs numpy; without it the module skips.
"""
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")  # the CI runner installs pytest only

sys.path.insert(0, str(Path(__file__).resolve().parent))
from proxy_frame import derive_frame, canonical_triangle  # noqa: E402

def rot(axis, deg):
    a = np.asarray(axis, float); a = a/np.linalg.norm(a); th = np.radians(deg)
    x,y,z = a; c = np.cos(th); s = np.sin(th); C = 1-c
    return np.array([[c+x*x*C, x*y*C-z*s, x*z*C+y*s],
                     [y*x*C+z*s, c+y*y*C, y*z*C-x*s],
                     [z*x*C-y*s, z*y*C+x*s, c+z*z*C]])

# positive fixture: canonical identity -> R == I, not ambiguous, anchor preserved
@pytest.fixture
def canonical():
    return derive_frame(canonical_triangle([0.1,0.2,0.3]))

def test_canonical_identity_frame_is_identity(canonical):
    c,R,amb,deg = canonical
    assert np.allclose(R, np.eye(3), atol=1e-6)

def test_canonical_not_ambiguous(canonical):
    c,R,amb,deg = canonical
    assert amb is False

def test_canonical_anchor_preserved(canonical):
    c,R,amb,deg = canonical
    assert np.allclose(c, [0.1,0.2,0.3], atol=1e-9)

def test_canonical_angles_90_63_4_26_6(canonical):
    c,R,amb,deg = canonical
    assert abs(deg[0]-90)<0.5 and abs(deg[1]-63.43)<0.5 and abs(deg[2]-26.57)<0.5, deg

# negative fixture: the 90/45/45 isosceles triangle -> ambiguous
def test_shipped_45_45_isosceles_flagged_ambiguous():
    e = 0.00136
    c,R,amb,deg = derive_frame([[0,0,0],[0,0,e],[e,0,0]])  # legs +Z and +X equal
    assert amb is True

# round-trip: emit canonical(R0) -> derive == R0 (no ambiguity), several rotations
@pytest.mark.parametrize("ax,dd", [((0,1,0),35),((1,0,0),20),((0,0,1),90),((1,1,0),60),((0,1,0),-50)])
def test_round_trip_canonical_derives_same_frame(ax, dd):
    R0 = rot(ax,dd)
    c,R,amb,deg = derive_frame(canonical_triangle([0,1,0], R0))
    assert np.allclose(R, R0, atol=1e-6)
    assert not amb

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
