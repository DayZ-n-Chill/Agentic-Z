#!/usr/bin/env python3
"""
proxy_frame.py - how a DayZ/Arma MLOD proxy triangle becomes an attachment frame.

A proxy is a named selection over one triangle. The attachment orientation is
derived from the triangle by angle sort, not by face vertex order:

  sort the 3 vertices by interior angle, descending:
    center = largest-angle vertex    (anchor / position)
    vert_y = middle-angle vertex     (-> local +Y)
    vert_z = smallest-angle vertex   (-> local +Z)
  y = normalize(vert_y - center); z = normalize(vert_z - center)
  x = normalize(y x z); z = normalize(x x y)        # re-orthogonalize
  R = rows [x, y, z]                                 # local -> world orientation

No vanilla file on P: shows the rule; it is MLOD tool and engine behaviour, the
same for Arma 3 and DayZ proxies.

Coordinates are raw MLOD (what py3d reads). Vanilla worn clothing is authored in
this same character space, so the identity frame means "item shown worn, upright".

Why a rotation used to look approximate: when the two edges from the anchor have
equal length (the 90/45/45 isosceles triangle that hand-rolled proxy builders
emit), the middle and smallest angles tie, y and z are assigned by raw vertex
order, and the frame comes out rotated. A canonical triangle has three distinct
angles, so the assignment has one answer. Rotating a canonical triangle keeps its
angles, so canonical triangles carry an exact frame through a write-back.

Engine frame against this frame (measured in game, 2026-06-24): the
engine renders the triangle as h(R) = P'.R, with
P' = [[-1,0,0],[0,0,1],[0,1,0]], relative to derive_frame. derive_frame is left
as it is because callers use it as the raw frame; bake canonical_triangle(anchor, P')
when the engine should render identity. An earlier guess, that Y/Z assignment and
handedness were swapped against the engine (a roll of about 90 degrees around the
long axis, invisible on cylindrical attachments), was replaced by this P' rule.
The full convention, and the muzzle-view method for custom weapon attachment
models, are in skills/_shared/models/proxy-frames.md.
"""
import numpy as np

def _angle(u, v):
    nu = float(np.linalg.norm(u)); nv = float(np.linalg.norm(v))
    if nu < 1e-12 or nv < 1e-12:
        return 0.0
    c = float(np.dot(u, v)) / (nu * nv)
    return float(np.arccos(max(-1.0, min(1.0, c))))

def derive_frame(tri):
    """tri: 3 x (x,y,z) MLOD coords. Returns (anchor[list], R 3x3 rows[x,y,z],
    ambiguous: bool, angles_deg_desc: list)."""
    P = [np.asarray(p, float) for p in tri]
    ang = [ _angle(P[(i+1) % 3] - P[i], P[(i+2) % 3] - P[i]) for i in range(3) ]
    order = sorted(range(3), key=lambda i: ang[i], reverse=True)  # largest angle first
    center, vy, vz = P[order[0]], P[order[1]], P[order[2]]
    deg = sorted([float(np.degrees(a)) for a in ang], reverse=True)
    ambiguous = abs(deg[1] - deg[2]) < 1.0   # middle vs smallest within 1 deg => tie
    y = vy - center; ny = np.linalg.norm(y); y = y/ny if ny > 1e-12 else np.array([0.,1.,0.])
    z = vz - center; nz = np.linalg.norm(z); z = z/nz if nz > 1e-12 else np.array([0.,0.,1.])
    x = np.cross(y, z); nx = np.linalg.norm(x); x = x/nx if nx > 1e-12 else np.array([1.,0.,0.])
    z = np.cross(x, y); z = z/(np.linalg.norm(z) + 1e-12)
    R = np.array([x, y, z])  # rows = world dirs of local x,y,z
    return center.tolist(), R, bool(ambiguous), deg

def canonical_triangle(anchor, R=None, scale=0.001):
    """Unambiguous triangle at `anchor` whose derived frame == R (identity if None).
    Point order: [anchor, vert_y(+Y short leg), vert_z(+Z long leg, 2x)]."""
    anchor = np.asarray(anchor, float)
    R = np.eye(3) if R is None else np.asarray(R, float)
    vy = anchor + scale * R[1]          # local +Y (short leg) -> middle angle -> vert_y
    vz = anchor + 2.0 * scale * R[2]    # local +Z (long  leg) -> smallest angle -> vert_z
    return [anchor.tolist(), vy.tolist(), vz.tolist()]
