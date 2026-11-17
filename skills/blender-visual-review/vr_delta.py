#!/usr/bin/env python3
"""Deterministic same-camera render comparator for blender-visual-review.

Compares two renders of the SAME object taken with the SAME camera, framing
and resolution (before/after an edit, or iteration N vs N-1) and reports
pixel-math agreement signals.

REPORT-ONLY (LL-153): these numbers are a change filter — proof that a fix
actually landed, or that something outside the edited region drifted — NEVER
a correctness verdict. Correctness is decided by eyes on the renders. This
tool is NOT calibrated for render-vs-reference-photo scoring: framing and
background mismatch invalidate every signal (upstream divine_eye.py needs an
explicit reconstruction-rescue mode for exactly that pair type; this tool
deliberately refuses to pretend otherwise).

Environment assumptions:
- Uniform render background (Workbench default) — the foreground mask is
  corner-sampled.
- The wire scale cube (VR_ScaleRef_1m) appears identically in both images of
  a pair, so it cancels in parity signals; it inflates the foreground mask
  equally in both. Acceptable for change detection.

Provenance: adapted from img2threejs
https://github.com/img2threejs/img2threejs commit 9a8ecf12 (v1.4.3),
Apache-2.0. Function origins:
  - PNG codec + foreground mask: forge/stage1_intake/extract_pbr_evidence.py
  - mask resample / IoU / bbox / proportion / symmetry:
    forge/stage4_review/diagnose_render.py
  - luma / SSIM / Sobel edge / blowout / flat / tonal:
    forge/stage4_review/divine_eye.py
Deliberately omitted: pHash, objectness, CIEDE2000 colour metrics — colour is
judged on native-res crops by eye (LL-153). Pure stdlib, Python 3.10+.

Usage:
    python vr_delta.py before.png after.png --json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path
from typing import Any

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MASK_GRID_SIZE = 224   # diagnose_render.py MASK_GRID_SIZE
LUMA_SIZE = 64         # divine_eye.py LUMA_SIZE
EDGE_SIZE = 96         # divine_eye.py EDGE_SIZE

# Heuristic "this signal moved" thresholds for same-camera pairs. Pointers for
# the reviewer's attention, not gates (LL-153).
MOVED_THRESHOLDS = {
    "silhouetteIoU": 0.99,
    "ssim": 0.98,
    "edgeOverlap": 0.95,
    "tonalParity": 0.98,
    "blowoutParity": 0.98,
    "flatParity": 0.98,
    "symmetryParity": 0.98,
}
MOVED_DELTA_THRESHOLDS = {
    "scaleDelta": 0.005,
    "aspectRatioDelta": 0.005,
}


# --- PNG codec (extract_pbr_evidence.py:84-186, sips fallback dropped) -------

def paeth_predictor(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_png(path: Path) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("not a PNG file")
    cursor = len(PNG_SIGNATURE)
    width = height = bit_depth = color_type = None
    idat = bytearray()
    interlace = 0
    while cursor + 8 <= len(data):
        length = struct.unpack(">I", data[cursor : cursor + 4])[0]
        chunk_type = data[cursor + 4 : cursor + 8]
        chunk_data = data[cursor + 8 : cursor + 8 + length]
        cursor += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(">IIBBBBB", chunk_data)
        elif chunk_type == b"IDAT":
            idat.extend(chunk_data)
        elif chunk_type == b"IEND":
            break
    if width is None or height is None or bit_depth != 8 or interlace != 0:
        raise ValueError("unsupported PNG; expected 8-bit non-interlaced image")
    channels_by_type = {0: 1, 2: 3, 4: 2, 6: 4}
    if color_type not in channels_by_type:
        raise ValueError("unsupported PNG color type; convert to RGB/RGBA first")
    channels = channels_by_type[color_type]
    row_bytes = width * channels
    raw = zlib.decompress(bytes(idat))
    rows: list[bytearray] = []
    offset = 0
    previous = bytearray(row_bytes)
    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        row = bytearray(raw[offset : offset + row_bytes])
        offset += row_bytes
        for index in range(row_bytes):
            left = row[index - channels] if index >= channels else 0
            up = previous[index]
            up_left = previous[index - channels] if index >= channels else 0
            if filter_type == 1:
                row[index] = (row[index] + left) & 0xFF
            elif filter_type == 2:
                row[index] = (row[index] + up) & 0xFF
            elif filter_type == 3:
                row[index] = (row[index] + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                predictor = paeth_predictor(left, up, up_left)
                row[index] = (row[index] + predictor) & 0xFF
            elif filter_type != 0:
                raise ValueError(f"unsupported PNG filter {filter_type}")
        rows.append(row)
        previous = row
    pixels: list[tuple[int, int, int, int]] = []
    for row in rows:
        for x in range(width):
            base = x * channels
            if color_type == 0:
                gray = row[base]
                pixels.append((gray, gray, gray, 255))
            elif color_type == 2:
                pixels.append((row[base], row[base + 1], row[base + 2], 255))
            elif color_type == 4:
                gray = row[base]
                pixels.append((gray, gray, gray, row[base + 1]))
            elif color_type == 6:
                pixels.append((row[base], row[base + 1], row[base + 2], row[base + 3]))
    return width, height, pixels


def write_png_rgb(path: Path, width: int, height: int, rgb: bytes) -> None:
    if len(rgb) != width * height * 3:
        raise ValueError("RGB payload has the wrong size")
    path.parent.mkdir(parents=True, exist_ok=True)

    def chunk(kind: bytes, payload: bytes) -> bytes:
        checksum = zlib.crc32(kind)
        checksum = zlib.crc32(payload, checksum) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)

    scanlines = bytearray()
    stride = width * 3
    for y in range(height):
        scanlines.append(0)
        scanlines.extend(rgb[y * stride : (y + 1) * stride])
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        PNG_SIGNATURE
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(scanlines), level=6))
        + chunk(b"IEND", b"")
    )


# --- foreground mask (extract_pbr_evidence.py:52-81, 210-271) ---------------

def srgb_luma(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def saturation(rgb: tuple[int, int, int]) -> float:
    r, g, b = (v / 255.0 for v in rgb)
    hi, lo = max(r, g, b), min(r, g, b)
    return 0.0 if hi == 0 else (hi - lo) / hi


def percentile(values: list[float], fraction: float, fallback: float = 0.0) -> float:
    if not values:
        return fallback
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(fraction * (len(ordered) - 1))))
    return ordered[index]


def median_color(samples: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    if not samples:
        return (0, 0, 0)
    rs = sorted(s[0] for s in samples)
    gs = sorted(s[1] for s in samples)
    bs = sorted(s[2] for s in samples)
    m = len(samples) // 2
    return (rs[m], gs[m], bs[m])


def sample_corner_background(
    width: int,
    height: int,
    pixels: list[tuple[int, int, int, int]],
) -> tuple[tuple[int, int, int], float]:
    radius = max(3, min(width, height) // 40)
    samples: list[tuple[int, int, int]] = []
    corner_ranges = [
        (0, radius, 0, radius),
        (width - radius, width, 0, radius),
        (0, radius, height - radius, height),
        (width - radius, width, height - radius, height),
    ]
    for x0, x1, y0, y1 in corner_ranges:
        for y in range(max(0, y0), min(height, y1)):
            for x in range(max(0, x0), min(width, x1)):
                red, green, blue, alpha = pixels[y * width + x]
                if alpha > 16:
                    samples.append((red, green, blue))
    background = median_color(samples)
    noise = percentile([color_distance(sample, background) for sample in samples], 0.75, 0.0)
    return background, noise


def build_foreground_mask(
    width: int,
    height: int,
    pixels: list[tuple[int, int, int, int]],
) -> tuple[list[bool], dict[str, Any], list[str]]:
    warnings: list[str] = []
    alpha_values = [pixel[3] for pixel in pixels]
    transparent_fraction = sum(1 for alpha in alpha_values if alpha < 245) / max(1, len(alpha_values))
    background, background_noise = sample_corner_background(width, height, pixels)
    threshold = max(24.0, background_noise * 2.4)
    mask: list[bool] = []
    if transparent_fraction > 0.03:
        for red, green, blue, alpha in pixels:
            mask.append(alpha > 24)
    else:
        for red, green, blue, alpha in pixels:
            rgb = (red, green, blue)
            distance = color_distance(rgb, background)
            sat = saturation(rgb)
            luma = srgb_luma(rgb)
            mask.append(alpha > 16 and (distance > threshold or (sat > 0.16 and luma < 0.94)))
    coverage = sum(1 for value in mask if value) / max(1, len(mask))
    if coverage < 0.035:
        warnings.append("foreground mask is tiny; signals may be unreliable")
        mask = [pixel[3] > 16 for pixel in pixels]
        coverage = sum(1 for value in mask if value) / max(1, len(mask))
    if coverage > 0.9:
        warnings.append("image is not clearly isolated from background")
    return (
        mask,
        {
            "backgroundNoise": round(background_noise, 3),
            "transparentPixelFraction": round(transparent_fraction, 4),
            "foregroundCoverage": round(coverage, 4),
        },
        warnings,
    )


# --- mask geometry (diagnose_render.py:66-129) -------------------------------

def load_mask(png_path: Path, size: int = MASK_GRID_SIZE) -> tuple[list[bool], dict[str, Any]]:
    width, height, pixels = read_png(png_path)
    mask, diag, _warn = build_foreground_mask(width, height, pixels)
    resized: list[bool] = []
    for y in range(size):
        sy = min(height - 1, int(y * height / size))
        for x in range(size):
            sx = min(width - 1, int(x * width / size))
            resized.append(mask[sy * width + sx])
    return resized, diag


def silhouette_iou(reference_mask: list[bool], render_mask: list[bool]) -> float:
    intersection = 0
    union = 0
    for ref, render in zip(reference_mask, render_mask):
        if ref or render:
            union += 1
            if ref and render:
                intersection += 1
    return intersection / union if union else 1.0


def bbox_of(mask: list[bool], size: int = MASK_GRID_SIZE) -> tuple[int, int, int, int]:
    xs: list[int] = []
    ys: list[int] = []
    for index, value in enumerate(mask):
        if value:
            xs.append(index % size)
            ys.append(index // size)
    if not xs:
        return (0, 0, 0, 0)
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    return (x0, y0, x1 - x0 + 1, y1 - y0 + 1)


def proportion_delta(
    reference_bbox: tuple[int, int, int, int],
    render_bbox: tuple[int, int, int, int],
) -> dict[str, float]:
    _rx, _ry, rw, rh = reference_bbox
    _dx, _dy, dw, dh = render_bbox
    ref_ar = rw / rh if rh else 0.0
    render_ar = dw / dh if dh else 0.0
    aspect_ratio_delta = abs(ref_ar - render_ar) / ref_ar if ref_ar else (0.0 if render_ar == 0 else 1.0)
    ref_area = rw * rh
    render_area = dw * dh
    scale_delta = abs(ref_area - render_area) / ref_area if ref_area else (0.0 if render_area == 0 else 1.0)
    return {"aspect_ratio_delta": round(aspect_ratio_delta, 4), "scale_delta": round(scale_delta, 4)}


def bilateral_symmetry_error(mask: list[bool], size: int = MASK_GRID_SIZE) -> float:
    total = 0
    mismatches = 0
    for y in range(size):
        row_offset = y * size
        for x in range(size):
            mirrored_x = size - 1 - x
            total += 1
            if mask[row_offset + x] != mask[row_offset + mirrored_x]:
                mismatches += 1
    return mismatches / total if total else 0.0


# --- luma signals (divine_eye.py:180-272) ------------------------------------

def load_luma(png_path: Path, size: int) -> list[float]:
    width, height, pixels = read_png(png_path)
    acc = [0.0] * (size * size)
    cnt = [0] * (size * size)
    for idx, (r, g, b, _a) in enumerate(pixels):
        x = idx % width
        y = idx // width
        if y >= height:
            break
        cell = min(size - 1, y * size // height) * size + min(size - 1, x * size // width)
        acc[cell] += (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
        cnt[cell] += 1
    return [acc[i] / cnt[i] if cnt[i] else 0.0 for i in range(size * size)]


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def global_ssim(a: list[float], b: list[float]) -> float:
    n = len(a)
    if n == 0 or len(b) != n:
        return 0.0
    mu_a, mu_b = _mean(a), _mean(b)
    var_a = _mean([(x - mu_a) ** 2 for x in a])
    var_b = _mean([(x - mu_b) ** 2 for x in b])
    cov = _mean([(a[i] - mu_a) * (b[i] - mu_b) for i in range(n)])
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    ssim = ((2 * mu_a * mu_b + c1) * (2 * cov + c2)) / (
        (mu_a ** 2 + mu_b ** 2 + c1) * (var_a + var_b + c2)
    )
    return max(0.0, min(1.0, ssim))


def _sobel_edges(luma: list[float], size: int, thresh: float = 0.12) -> list[bool]:
    edges = [False] * (size * size)
    for y in range(1, size - 1):
        for x in range(1, size - 1):
            def g(dx, dy):
                return luma[(y + dy) * size + (x + dx)]
            gx = (g(-1, -1) + 2 * g(-1, 0) + g(-1, 1)) - (g(1, -1) + 2 * g(1, 0) + g(1, 1))
            gy = (g(-1, -1) + 2 * g(0, -1) + g(1, -1)) - (g(-1, 1) + 2 * g(0, 1) + g(1, 1))
            if math.hypot(gx, gy) > thresh:
                edges[y * size + x] = True
    return edges


def edge_overlap(a: list[float], b: list[float], size: int) -> float:
    ea, eb = _sobel_edges(a, size), _sobel_edges(b, size)
    inter = union = 0
    for i in range(len(ea)):
        if ea[i] or eb[i]:
            union += 1
            if ea[i] and eb[i]:
                inter += 1
    return inter / union if union else 1.0


def _blown_fraction(luma: list[float], hi: float = 0.95) -> float:
    return sum(1 for v in luma if v >= hi) / max(1, len(luma))


def blowout_parity(ref: list[float], ren: list[float]) -> float:
    diff = abs(_blown_fraction(ren) - _blown_fraction(ref))
    return max(0.0, 1.0 - diff * 4.0)


def flat_fraction(luma: list[float], size: int, eps: float = 0.02) -> float:
    flat = 0
    total = 0
    for y in range(1, size - 1):
        for x in range(1, size - 1):
            c = luma[y * size + x]
            grad = abs(c - luma[y * size + x - 1]) + abs(c - luma[(y - 1) * size + x])
            total += 1
            if grad < eps:
                flat += 1
    return flat / total if total else 0.0


def tonal_parity(ref: list[float], ren: list[float], bins: int = 16) -> float:
    def hist(xs):
        h = [0] * bins
        for v in xs:
            h[min(bins - 1, int(v * bins))] += 1
        tot = sum(h) or 1
        return [c / tot for c in h]
    ha, hb = hist(ref), hist(ren)
    l1 = sum(abs(ha[i] - hb[i]) for i in range(bins))
    return max(0.0, 1.0 - l1 / 2.0)


# --- pair evaluation ---------------------------------------------------------

def evaluate_pair(path_a: Path, path_b: Path) -> dict[str, Any]:
    """Compare two same-camera renders. Returns signals + attention pointers.
    No verdict field on purpose: report-only (LL-153)."""
    bytes_a = path_a.read_bytes()
    bytes_b = path_b.read_bytes()
    identical = hashlib.sha256(bytes_a).hexdigest() == hashlib.sha256(bytes_b).hexdigest()

    mask_a, diag_a = load_mask(path_a)
    mask_b, diag_b = load_mask(path_b)
    luma_a = load_luma(path_a, LUMA_SIZE)
    luma_b = load_luma(path_b, LUMA_SIZE)
    edge_a = load_luma(path_a, EDGE_SIZE)
    edge_b = load_luma(path_b, EDGE_SIZE)

    iou = silhouette_iou(mask_a, mask_b)
    prop = proportion_delta(bbox_of(mask_a), bbox_of(mask_b))
    sym_a = bilateral_symmetry_error(mask_a)
    sym_b = bilateral_symmetry_error(mask_b)
    sym = max(0.0, 1.0 - abs(sym_b - sym_a) / 0.10)
    flat_a = flat_fraction(luma_a, LUMA_SIZE)
    flat_b = flat_fraction(luma_b, LUMA_SIZE)
    flat = max(0.0, 1.0 - abs(flat_b - flat_a) * 4.0)

    signals = {
        "silhouetteIoU": round(iou, 4),
        "scaleDelta": prop["scale_delta"],
        "aspectRatioDelta": prop["aspect_ratio_delta"],
        "symmetryParity": round(sym, 4),
        "ssim": round(global_ssim(luma_a, luma_b), 4),
        "edgeOverlap": round(edge_overlap(edge_a, edge_b, EDGE_SIZE), 4),
        "blowoutParity": round(blowout_parity(luma_a, luma_b), 4),
        "flatParity": round(flat, 4),
        "tonalParity": round(tonal_parity(luma_a, luma_b), 4),
    }

    moved = [k for k, floor in MOVED_THRESHOLDS.items() if signals[k] < floor]
    moved += [k for k, ceil in MOVED_DELTA_THRESHOLDS.items() if signals[k] > ceil]

    return {
        "identicalImages": identical,
        "signals": signals,
        "movedSignals": sorted(moved),
        "foreground": {"a": diag_a, "b": diag_b},
        "a": str(path_a.resolve()),
        "b": str(path_b.resolve()),
        "note": "report-only change filter (LL-153): moved signals point the eye, "
                "they never pass or fail an iteration. identicalImages=true after an "
                "intended edit means the old scene was re-rendered.",
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image_a", type=Path, help="before / previous-iteration render")
    parser.add_argument("image_b", type=Path, help="after / current-iteration render")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = evaluate_pair(args.image_a.expanduser().resolve(), args.image_b.expanduser().resolve())
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        flag = "IDENTICAL FILES" if result["identicalImages"] else (
            "moved: " + (", ".join(result["movedSignals"]) or "nothing beyond noise"))
        print(flag)
        for key, value in result["signals"].items():
            print(f"  {key:>18} {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
