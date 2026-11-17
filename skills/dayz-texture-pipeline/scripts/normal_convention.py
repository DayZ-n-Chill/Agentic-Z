#!/usr/bin/env python3
"""Propose whether a normal map is OpenGL (Y+) or DirectX (Y-) from measurement, not by eye.

DayZ `_nohq` is DirectX/Y- (rule 3 in this skill's SKILL.md). A source map of unknown convention
is otherwise a guess, and a wrong guess turns every groove into a ridge.

Pure offline script: it reads two image files and prints a report. It needs numpy and Pillow and
does not need the P: work drive, DayZ Tools or the game, so it does not run /dayz-preflight.

Two independent readings; a candidate needs both to agree, otherwise INCONCLUSIVE. A candidate
is not proof: both readings agreed on the wrong convention for a valid tangent-space bake on a
sphere patch and for undersampled tileable detail. Confirm it independently (the baker's export
setting, or a render under a raking light) before inverting a channel. A raking light confirms
only if it crosses V: the green changes the shading only through the light's V component, so a
light parallel to U, or a groove that runs along V, renders this map and its inverted-green copy
alike and leaves the check inconclusive. What confirms: a light from the top or the bottom of the
texture, a groove that runs along U, and the inverted copy reading that groove as a ridge.

1. Albedo reading: across a groove (a valley) the surface normals converge.
     - Red, X: +U is right in both conventions, so d(nx)/dx < 0 when a valley is crossed
       left to right.
     - Green, Y: in OpenGL +Y is +V, up in the image, so walking down the rows d(ny)/dy > 0
       (the opposite sign to red); in DirectX +Y points down and the sign equals red's.
   The grooves are found in the albedo: dirt collects in hollows, so a pixel darker than its
   blurred surroundings (a high-pass of the albedo) marks a hollow. The red channel calibrates
   the sign of that hollow signal; the green channel decides. It assumes the hollows curve the
   same way along both axes (pits, or grooves in both directions): on a surface whose
   curvature has opposite signs along the two axes the green correlation follows the geometry,
   not the convention, and the reading is wrong with strong correlations.
2. Curl reading (no albedo): the slopes of a height field have no curl. With
   p = -nx/nz and q = ny/nz, d(p)/d(row) - d(q)/d(col) is ~0 under OpenGL and
   d(p)/d(row) + d(q)/d(col) is ~0 under DirectX. The smaller median residual wins if it is
   below CURL_RATIO times the other and the two differ by more than CURL_FLOOR, one 8-bit step
   of the normal (2/255). The floor is a heuristic, not a bound on rounding noise: where the
   normals are nearly flat (nz close to 1) rounding to 8 bits moves each residual by up to about
   one step, but dividing by a smaller nz amplifies that error. It was added after a vanilla map
   whose residuals sat half a step apart read OpenGL.
3. Block stability (added after a test on vanilla maps): a candidate stands only if each reading
   keeps it across a BLOCK_GRID x BLOCK_GRID grid of blocks. Each block gets each reading's
   verdict from its own pixels (the derivatives, masks and thresholds of the whole map); among
   the blocks that name a convention, at most BLOCK_CURL_MAX_OPPOSED (curl) or
   BLOCK_ALBEDO_MAX_OPPOSED (albedo) may name the other one, and at least one must name the
   candidate. A really inverted convention inverts a reading wherever there is relief; a curved
   bake, a decal or a map stitched from two sources leaves blocks that disagree.

What it does NOT check: inverting the green channel of the same map only negates the green
correlation and swaps the two curl residuals, so it always flips the verdict and is no control.
The controls are maps of known convention (test_normal_convention.py, next to this file). A map
that is not a height field's slopes (painted, hand-edited, heavily compressed) can leave the curl
reading inconclusive. Nor does it tell which channel is off: both readings compare the green's
sign with the red's, so a map whose red is inverted against the real relief (X-, Y-) also reads
OpenGL, and inverting its green then gives a consistent map with the relief upside down. Check
red on a feature of known relief before choosing the channel. Nor does the block check see a map
that mixes the two conventions inside every block (a known, accepted limit): vanilla
kancel_008_nohq, whose glass panes read DirectX and whose bolts and window frames read OpenGL a
few pixels away, reads OpenGL with stable blocks. Measured on three vanilla samples: 1 wrong
candidate in 502, 0 in the 165 not used to design the check.

Input: 8-bit PNG (or any format Pillow reads) of the same size. Convert a `.paa` first with
DayZ Tools ImageToPAA; a `_nohq` name makes it write the RGB normal.

Usage:
  python normal_convention.py --normal heater_Normal.png --albedo heater_BaseColor.png [--json]
Exit: 0 = both readings agree on a candidate (DirectX or OpenGL), stable across the blocks,
2 = INCONCLUSIVE, 1 = bad input (a missing or unreadable file, sizes that differ, or numpy or
Pillow not installed).
JSON keeps the key "verdict" for that candidate.

Differences from the script this one grew from: command-line paths instead of fixed ones, a
non-finite correlation is INCONCLUSIVE (the first version read NaN as DirectX), a size check, JSON
output (null for undefined numbers), and the curl reading with the agreement rule, added after a
review found a confident wrong verdict.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from fractions import Fraction

try:
    import numpy as np
    from PIL import Image, ImageFilter
except ImportError as exc:  # optional dependencies: say which one, then stop as bad input
    print("ERROR: normal_convention.py needs numpy and Pillow (%s). "
          "Install them with: python -m pip install numpy Pillow" % exc, file=sys.stderr)
    raise SystemExit(1)

DETAIL_MIN = 0.04   # |nx| + |ny| above which the normal map carries detail
LUMA_MIN = 0.02     # albedo floor: skips the atlas background
BLUR_RADIUS = 6     # Gaussian radius of the albedo's low-pass, in pixels
MIN_CORR = 0.02     # weaker albedo correlations are INCONCLUSIVE
NZ_MIN = 0.2        # floor for nz when normals are turned into slopes
CURL_RATIO = 0.8    # the smaller curl residual must be below this times the other
CURL_FLOOR = 2.0 / 255.0  # one 8-bit step of the normal: residual medians closer than this are not trusted
BLOCK_GRID = 6                             # blocks per axis in the block-stability check
BLOCK_CURL_MAX_OPPOSED = Fraction(1, 10)   # at most this share of the voting blocks may oppose the curl candidate
BLOCK_ALBEDO_MAX_OPPOSED = Fraction(1, 3)  # at most this share of the voting blocks may oppose the albedo candidate

DIRECTX, OPENGL, INCONCLUSIVE = "DirectX", "OpenGL", "INCONCLUSIVE"


def _corr(a: np.ndarray, b: np.ndarray, mask: np.ndarray) -> float:
    a, b = a[mask], b[mask]
    a = a - a.mean()
    b = b - b.mean()
    denom = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
    if denom == 0.0:
        return float("nan")
    return float((a * b).sum() / denom)


def _albedo_fields(nx, ny, albedo_img, blur_radius, detail_min, luma_min) -> tuple:
    alb_rgb = albedo_img.convert("RGB")
    alb = np.asarray(alb_rgb).astype(np.float64) / 255.0
    luma = 0.2126 * alb[:, :, 0] + 0.7152 * alb[:, :, 1] + 0.0722 * alb[:, :, 2]
    smooth = np.asarray(alb_rgb.convert("L").filter(ImageFilter.GaussianBlur(blur_radius))).astype(np.float64) / 255.0
    hollow = smooth - luma            # > 0 where the pixel is darker than its surroundings

    dnx_dx = np.gradient(nx, axis=1)
    dny_dy = np.gradient(ny, axis=0)

    mask = ((np.abs(nx) + np.abs(ny)) > detail_min) & (luma > luma_min)
    return dnx_dx, dny_dy, hollow, mask


def _albedo_verdict(red, green, min_corr) -> str:
    if not (math.isfinite(red) and math.isfinite(green)) or abs(red) < min_corr or abs(green) < min_corr:
        return INCONCLUSIVE
    if (red > 0) == (green > 0):
        return DIRECTX
    return OPENGL


def _albedo_reading(fields, window, min_corr) -> dict:
    dnx_dx, dny_dy, hollow, mask = fields
    m = mask[window]
    red = _corr(dnx_dx[window], hollow[window], m) if m.any() else float("nan")
    green = _corr(dny_dy[window], hollow[window], m) if m.any() else float("nan")
    return {"verdict": _albedo_verdict(red, green, min_corr), "corr_red": red, "corr_green": green,
            "pixels": int(m.sum())}


def _curl_fields(nx, ny, nz, detail_min) -> tuple:
    nz = np.clip(nz, NZ_MIN, None)
    p = -nx / nz                       # dh/dcol in both conventions
    q = ny / nz                        # dh/drow under OpenGL, -dh/drow under DirectX
    dp_drow = np.gradient(p, axis=0)
    dq_dcol = np.gradient(q, axis=1)
    mask = (np.abs(nx) + np.abs(ny)) > detail_min
    # DirectX residual per pixel, OpenGL residual per pixel, detail mask
    return np.abs(dp_drow + dq_dcol), np.abs(dp_drow - dq_dcol), mask


def _curl_reading(fields, window, curl_ratio, curl_floor) -> dict:
    res_dx, res_gl, mask = fields
    m = mask[window]
    if not m.any():
        return {"verdict": INCONCLUSIVE, "residual_directx": float("nan"), "residual_opengl": float("nan")}
    res_opengl = float(np.median(res_gl[window][m]))
    res_directx = float(np.median(res_dx[window][m]))
    verdict = _curl_verdict(res_directx, res_opengl, curl_ratio, curl_floor)
    return {"verdict": verdict, "residual_directx": res_directx, "residual_opengl": res_opengl}


def _curl_verdict(res_directx: float, res_opengl: float, curl_ratio: float, curl_floor: float) -> str:
    # Where the normals are flat enough that nz decodes to 1, the medians sit on multiples of 1/255 up
    # to float error: a difference of exactly one step computes as 2/255 plus a few ulps, and the
    # relative tolerance keeps it below the floor.
    if abs(res_directx - res_opengl) <= curl_floor * (1.0 + 1e-9):
        return INCONCLUSIVE
    if res_directx < curl_ratio * res_opengl:
        return DIRECTX
    if res_opengl < curl_ratio * res_directx:
        return OPENGL
    return INCONCLUSIVE


def _block_edges(size, grid) -> list:
    return [int(v) for v in np.linspace(0, size, grid + 1).round()]


def _block_counts(albedo_fields, curl_fields, shape, verdict, grid, min_corr, curl_ratio, curl_floor) -> dict:
    other = OPENGL if verdict == DIRECTX else DIRECTX
    row_edges = _block_edges(shape[0], grid)
    col_edges = _block_edges(shape[1], grid)
    counts = {"albedo": [0, 0], "curl": [0, 0]}
    for i in range(grid):
        for j in range(grid):
            window = (slice(row_edges[i], row_edges[i + 1]), slice(col_edges[j], col_edges[j + 1]))
            albedo_v = _albedo_reading(albedo_fields, window, min_corr)["verdict"]
            if albedo_v == verdict:
                counts["albedo"][0] += 1
            elif albedo_v == other:
                counts["albedo"][1] += 1
            curl_v = _curl_reading(curl_fields, window, curl_ratio, curl_floor)["verdict"]
            if curl_v == verdict:
                counts["curl"][0] += 1
            elif curl_v == other:
                counts["curl"][1] += 1
    return counts


def _stable(agree, opposed, max_opposed) -> bool:
    return agree >= 1 and opposed <= Fraction(max_opposed) * (agree + opposed)


def detect(normal_img: Image.Image, albedo_img: Image.Image, *, blur_radius: float = BLUR_RADIUS,
           detail_min: float = DETAIL_MIN, luma_min: float = LUMA_MIN, min_corr: float = MIN_CORR,
           curl_ratio: float = CURL_RATIO, curl_floor: float = CURL_FLOOR,
           block_grid: int = BLOCK_GRID, block_curl_max_opposed: Fraction = BLOCK_CURL_MAX_OPPOSED,
           block_albedo_max_opposed: Fraction = BLOCK_ALBEDO_MAX_OPPOSED) -> dict:
    """Return the verdict and the numbers behind it. Raises ValueError on mismatched sizes."""
    if normal_img.size != albedo_img.size:
        raise ValueError("normal map %s and albedo %s differ in size" % (normal_img.size, albedo_img.size))
    # (2c - 255) / 255 is exactly antisymmetric: a channel inverted as 255 - c decodes to exactly the
    # negated value, so an inverted-green copy flips every reading and keeps every block count.
    nrm = np.asarray(normal_img.convert("RGB")).astype(np.float64)
    nx = (2.0 * nrm[:, :, 0] - 255.0) / 255.0
    ny = (2.0 * nrm[:, :, 1] - 255.0) / 255.0
    nz = (2.0 * nrm[:, :, 2] - 255.0) / 255.0

    albedo_fields = _albedo_fields(nx, ny, albedo_img, blur_radius, detail_min, luma_min)
    curl_fields = _curl_fields(nx, ny, nz, detail_min)
    whole = (slice(None), slice(None))
    albedo = _albedo_reading(albedo_fields, whole, min_corr)
    curl = _curl_reading(curl_fields, whole, curl_ratio, curl_floor)
    if albedo["verdict"] == curl["verdict"] and albedo["verdict"] != INCONCLUSIVE:
        verdict = albedo["verdict"]
        blocks = _block_counts(albedo_fields, curl_fields, nx.shape, verdict, block_grid,
                               min_corr, curl_ratio, curl_floor)
        stable = (_stable(*blocks["curl"], block_curl_max_opposed)
                  and _stable(*blocks["albedo"], block_albedo_max_opposed))
        if not stable:
            verdict = INCONCLUSIVE
    else:
        verdict = INCONCLUSIVE
        blocks = None
        stable = None
    return {
        "verdict": verdict,
        "albedo_verdict": albedo["verdict"],
        "curl_verdict": curl["verdict"],
        "corr_red": albedo["corr_red"],
        "corr_green": albedo["corr_green"],
        "pixels_with_detail": albedo["pixels"],
        "pixels_total": int(nx.size),
        "curl_residual_directx": curl["residual_directx"],
        "curl_residual_opengl": curl["residual_opengl"],
        "min_corr": min_corr,
        "curl_ratio": curl_ratio,
        "curl_floor": curl_floor,
        "block_grid": block_grid,
        "block_curl_max_opposed": float(block_curl_max_opposed),
        "block_albedo_max_opposed": float(block_albedo_max_opposed),
        "curl_blocks_agree": None if blocks is None else blocks["curl"][0],
        "curl_blocks_opposed": None if blocks is None else blocks["curl"][1],
        "albedo_blocks_agree": None if blocks is None else blocks["albedo"][0],
        "albedo_blocks_opposed": None if blocks is None else blocks["albedo"][1],
        "blocks_stable": stable,
    }


def _json_safe(result: dict) -> dict:
    return {k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in result.items()}


def _fmt(value: float) -> str:
    return "%+.4f" % value if math.isfinite(value) else "undefined"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Propose OpenGL (Y+) or DirectX (Y-) for a normal map: a candidate to confirm, not proof.")
    parser.add_argument("--normal", required=True, help="tangent-space normal map (RGB)")
    parser.add_argument("--albedo", required=True, help="albedo/base colour of the same UV layout")
    parser.add_argument("--min-corr", type=float, default=MIN_CORR, help="weakest albedo correlation that counts (default 0.02)")
    parser.add_argument("--json", action="store_true", help="print the result as JSON (undefined numbers are null)")
    args = parser.parse_args(argv)
    try:
        with Image.open(args.normal) as normal_img, Image.open(args.albedo) as albedo_img:
            result = detect(normal_img, albedo_img, min_corr=args.min_corr)
    except (OSError, ValueError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(_json_safe(result), indent=2, allow_nan=False))
    else:
        share = 100.0 * result["pixels_with_detail"] / max(result["pixels_total"], 1)
        print("pixels with detail: %d of %d (%.1f %%)" % (result["pixels_with_detail"], result["pixels_total"], share))
        print("albedo reading: corr(d nx/dx, hollow) = %s (calibrates the sign), corr(d ny/dy, hollow) = %s -> %s"
              % (_fmt(result["corr_red"]), _fmt(result["corr_green"]), result["albedo_verdict"]))
        print("curl reading: median residual DirectX %s, OpenGL %s -> %s"
              % (_fmt(result["curl_residual_directx"]), _fmt(result["curl_residual_opengl"]), result["curl_verdict"]))
        if result["blocks_stable"] is not None:
            print("blocks (%dx%d): curl %d agree / %d opposed (max %.1f %%), albedo %d agree / %d opposed (max %.1f %%) -> %s"
                  % (result["block_grid"], result["block_grid"],
                     result["curl_blocks_agree"], result["curl_blocks_opposed"], 100.0 * result["block_curl_max_opposed"],
                     result["albedo_blocks_agree"], result["albedo_blocks_opposed"], 100.0 * result["block_albedo_max_opposed"],
                     "stable" if result["blocks_stable"] else "unstable"))
        if result["verdict"] == DIRECTX:
            print("CANDIDATE: DirectX (Y-) -> DayZ's convention; confirm it independently before shipping")
        elif result["verdict"] == OPENGL:
            print("CANDIDATE: OpenGL (Y+) -> invert the green channel once an independent check agrees")
        else:
            if result["blocks_stable"] is False:
                print("INCONCLUSIVE: the two readings agree on the whole map but not across its blocks")
            else:
                print("INCONCLUSIVE: the two readings do not agree on a convention")
    return 2 if result["verdict"] == INCONCLUSIVE else 0


if __name__ == "__main__":
    sys.exit(main())
