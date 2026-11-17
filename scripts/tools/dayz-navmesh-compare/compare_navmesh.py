"""Compare two DayZ navmesh (.nm) files tile by tile, by structure rather than bytes.

NavMeshGenerator does not write the same bytes twice: between two runs almost
every tile's bytes differ while its structure does not. Hashing the files, or
the tiles, reports a change everywhere. This comparison reads both files with
navmesh_tiles.read_navmesh (fail-closed) and counts as structural only a tile
whose polygon count, vertex count or vertical bounds changed.

With --old-terrain and --new-terrain (NPZ files holding a 2-D "heights" array,
the vertex at row r, column c standing at x = c * cell, z = (rows - 1 - r) *
cell) every structural tile is located against the terrain vertices that
changed: a change within --local-m of an edit is local. With --routes, each
route (id;x y z;x y z per line) is widened by 25 m and the structural tiles
under it are listed. numpy is needed for the terrain inputs only.

Status, and exit code:
  PASS_NO_STRUCTURE_DELTA     0  no structural change (and no terrain change, if given)
  PASS_LOCAL_STRUCTURE_DELTA  0  structural changes, all within --local-m of a terrain edit,
                                 none under a route
  REVIEW                      1  anything else; review_reasons says why
  usage error                 2
  refused                     3  an input refused or unreadable, or --out already exists;
                                 nothing written
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
import zipfile
from pathlib import Path


_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from navmesh_tiles import Navmesh, NavmeshFormatError, read_navmesh  # noqa: E402


ROUTE_MARGIN_M = 25.0
DEFAULT_LOCAL_M = 100.0

EXIT_PASS, EXIT_REVIEW, EXIT_REFUSED = 0, 1, 3  # argparse exits 2 on a usage error

LIMITS = [
    "Reads the file header, the offset table and the 100-byte header of every tile; no polygon topology, "
    "link or AI-path claim.",
    "Generator runs rewrite almost every tile's bytes: only polygon and vertex counts and vertical bounds "
    "count as structure.",
    "Unchanged structure along a route is not a locomotion result.",
]


class CompareError(Exception):
    """An input or output the comparison refuses; nothing is written."""


def route_cover(start_xz: tuple[float, float], end_xz: tuple[float, float], tile_m: float,
                margin: float, grid: tuple[int, int] | None = None) -> set[tuple[int, int]]:
    """Tiles meeting the route's rectangle widened by margin; a tile edge on the border counts.

    With grid (tiles along x, tiles along z), only the tiles inside it: a route far off the
    map costs no more than one over it.
    """

    def span(a: float, b: float, count: int | None) -> range:
        low, high = min(a, b) - margin, max(a, b) + margin
        first, last = math.ceil(low / tile_m) - 1, math.floor(high / tile_m)
        if count is not None:
            first, last = max(first, 0), min(last, count - 1)
        return range(first, last + 1)

    count_x, count_z = (None, None) if grid is None else grid
    return {
        (x, z)
        for x in span(start_xz[0], end_xz[0], count_x)
        for z in span(start_xz[1], end_xz[1], count_z)
    }


def read_routes(path: Path) -> dict[str, tuple[tuple[float, float], tuple[float, float]]]:
    """id;x y z;x y z per line, blank lines skipped; returns id -> ((x, z), (x, z))."""
    where = f"--routes {path}"
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        raise CompareError(f"cannot read {where}: {error}") from error
    routes: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {}
    first_line: dict[str, int] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        fields = line.split(";")
        if len(fields) != 3:
            raise CompareError(f"{where}: line {number}: expected id;x y z;x y z, found {len(fields)} fields")
        ident = fields[0].strip()
        if not ident:
            raise CompareError(f"{where}: line {number}: empty route id")
        if ident in routes:
            raise CompareError(
                f"{where}: line {number}: duplicate route id {ident!r}, first on line {first_line[ident]}"
            )
        points = []
        for label, field in (("start", fields[1]), ("end", fields[2])):
            parts = field.split()
            if len(parts) != 3:
                raise CompareError(f"{where}: line {number}: the {label} point needs three numbers x y z")
            try:
                x, y, z = (float(part) for part in parts)
            except ValueError as error:
                raise CompareError(f"{where}: line {number}: the {label} point is not a number: {error}") from error
            if not all(math.isfinite(value) for value in (x, y, z)):
                raise CompareError(f"{where}: line {number}: the {label} point is non-finite")
            points.append((x, z))
        routes[ident] = (points[0], points[1])
        first_line[ident] = number
    if not routes:
        raise CompareError(f"{where}: no routes in the file")
    return routes


def _numpy():
    try:
        import numpy
    except ImportError as error:
        raise CompareError(f"--old-terrain and --new-terrain need numpy, which cannot be imported: {error}") from error
    return numpy


def read_heights(numpy, path: Path):
    """The 2-D, finite, numeric "heights" array of an NPZ file, and the file's SHA-256."""
    try:
        data = path.read_bytes()
    except OSError as error:
        raise CompareError(f"cannot read {path}: {error}") from error
    try:
        loaded = numpy.load(io.BytesIO(data), allow_pickle=False)
    except (OSError, ValueError, EOFError, zipfile.BadZipFile) as error:
        raise CompareError(f"{path}: not a readable NPZ archive: {error}") from error
    if not hasattr(loaded, "files"):
        raise CompareError(f"{path}: a plain array, not an NPZ archive (numpy.savez) holding 'heights'")
    try:
        if "heights" not in loaded.files:
            raise CompareError(f"{path}: no 'heights' array in the NPZ archive (it holds {sorted(loaded.files)})")
        heights = loaded["heights"]
    except (OSError, ValueError, EOFError, zipfile.BadZipFile) as error:
        raise CompareError(f"{path}: cannot read 'heights' from the NPZ archive: {error}") from error
    finally:
        loaded.close()
    if heights.ndim != 2:
        raise CompareError(f"{path}: 'heights' must be a 2-D array, found shape {heights.shape}")
    if heights.size == 0:
        raise CompareError(f"{path}: 'heights' is empty, shape {heights.shape}")
    if heights.dtype.kind not in "biuf":
        raise CompareError(f"{path}: 'heights' must be numeric, found dtype {heights.dtype}")
    if not bool(numpy.isfinite(heights).all()):
        raise CompareError(f"{path}: 'heights' holds non-finite values")
    return heights, hashlib.sha256(data).hexdigest()


def _tile_distance(numpy, vertex_x, vertex_z, x: int, z: int, tile_m: float) -> float:
    x0, z0 = x * tile_m, z * tile_m
    dx = numpy.maximum(numpy.maximum(x0 - vertex_x, 0.0), vertex_x - (x0 + tile_m))
    dz = numpy.maximum(numpy.maximum(z0 - vertex_z, 0.0), vertex_z - (z0 + tile_m))
    return float(numpy.hypot(dx, dz).min())


def compare(old: Navmesh, new: Navmesh, *, terrain=None, routes=None) -> dict:
    """The report. terrain: None or a dict with old/new paths, heights and hashes, cell_m and local_m."""
    if old.layout != new.layout:
        raise CompareError(
            f"tile layouts differ: {old.path} is {old.layout.tiles_x} x {old.layout.tiles_z} tiles of "
            f"{old.layout.tile_m} m, {new.path} is {new.layout.tiles_x} x {new.layout.tiles_z} of {new.layout.tile_m} m"
        )
    layout = new.layout
    tile_m = layout.tile_m
    changed = [index for index, tile in enumerate(new.tiles) if tile.sha256 != old.tiles[index].sha256]
    structural = sorted(
        (new.tiles[index].x, new.tiles[index].z)
        for index in changed
        if new.tiles[index].structure() != old.tiles[index].structure()
    )

    distances: dict[tuple[int, int], float | None] = {key: None for key in structural}
    changed_vertices = None
    if terrain is not None:
        numpy = terrain["numpy"]
        old_h, new_h = terrain["old_heights"], terrain["new_heights"]
        rows, cols = numpy.nonzero(old_h != new_h)
        changed_vertices = int(rows.size)
        if changed_vertices:
            vertex_x = cols.astype("float64") * terrain["cell_m"]
            vertex_z = (old_h.shape[0] - 1 - rows).astype("float64") * terrain["cell_m"]
            for key in structural:
                distances[key] = _tile_distance(numpy, vertex_x, vertex_z, key[0], key[1], tile_m)

    hits = None
    if routes is not None:
        structural_set = set(structural)
        grid = (layout.tiles_x, layout.tiles_z)
        hits = {
            ident: [
                list(key)
                for key in sorted(route_cover(start, end, tile_m, ROUTE_MARGIN_M, grid) & structural_set)
            ]
            for ident, (start, end) in routes.items()
        }

    reasons = []
    measured = [value for value in distances.values() if value is not None]
    max_distance = max(measured) if measured else None
    if structural and terrain is None:
        reasons.append("structure_changed_without_terrain_inputs")
    if structural and terrain is not None and (max_distance is None or max_distance > terrain["local_m"]):
        reasons.append("structure_farther_than_local_m")
    if not structural and changed_vertices:
        reasons.append("terrain_changed_without_structure_change")
    if hits and any(hits.values()):
        reasons.append("route_tile_changed")
    if reasons:
        status = "REVIEW"
    else:
        status = "PASS_LOCAL_STRUCTURE_DELTA" if structural else "PASS_NO_STRUCTURE_DELTA"

    limits = list(LIMITS)
    if not layout.inside_verified_envelope:
        limits.append(
            "Layout outside the verified envelope (one 12 288 m world in 12.5, 25 or 50 m tiles): read with "
            "the same checks, never measured against a real file of this layout."
        )
    if terrain is not None:
        limits.append(
            "Terrain vertex (row, column) taken at x = column * cell_m, z = (rows - 1 - row) * cell_m; "
            "a structural tile with no changed vertex has no distance and counts as farther than local_threshold_m."
        )
    if routes is None:
        limits.append("No --routes given: no route was checked.")

    def tile_entry(key):
        distance = distances[key]
        return {
            "tile": list(key),
            "distance_m": None if distance is None else round(distance, 1),
            "old": old.tile(*key).to_json(),
            "new": new.tile(*key).to_json(),
        }

    rows_cols = None if terrain is None else terrain["old_heights"].shape
    return {
        "status": status,
        "review_reasons": reasons,
        "old_nm": str(old.path),
        "old_nm_sha256": old.sha256,
        "new_nm": str(new.path),
        "new_nm_sha256": new.sha256,
        "old_terrain": None if terrain is None else str(terrain["old_path"]),
        "old_terrain_sha256": None if terrain is None else terrain["old_sha256"],
        "new_terrain": None if terrain is None else str(terrain["new_path"]),
        "new_terrain_sha256": None if terrain is None else terrain["new_sha256"],
        "layout": layout.to_json(),
        "tile_m": tile_m,
        "tiles": len(new.tiles),
        "serialized_changed_tiles": len(changed),
        "structural_changes": len(structural),
        "changed_terrain_vertices": changed_vertices,
        "cell_m": None if terrain is None else terrain["cell_m"],
        "terrain_extent_m": None if terrain is None else [rows_cols[1] * terrain["cell_m"], rows_cols[0] * terrain["cell_m"]],
        "max_structural_tile_distance_m": max_distance,
        "local_threshold_m": None if terrain is None else terrain["local_m"],
        "route_margin_m": None if routes is None else ROUTE_MARGIN_M,
        "structural": [tile_entry(key) for key in structural],
        "route_tiles_changed": hits,
        "limits": limits,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compare_navmesh.py",
        description="Compare two DayZ .nm navmeshes tile by tile: structure, not bytes.",
    )
    parser.add_argument("--old-nm", type=Path, required=True, help="the accepted navmesh")
    parser.add_argument("--new-nm", type=Path, required=True, help="the navmesh to judge")
    parser.add_argument("--out", type=Path, required=True, help="the JSON report to create; must not exist")
    parser.add_argument("--old-terrain", type=Path, help="NPZ with the 'heights' the old mesh was built from")
    parser.add_argument("--new-terrain", type=Path, help="NPZ with the 'heights' the new mesh was built from")
    parser.add_argument("--cell-m", type=float, help="terrain cell size in metres (required with the terrain inputs)")
    parser.add_argument(
        "--local-m",
        type=float,
        help=f"largest distance from a terrain edit that counts as local (default {DEFAULT_LOCAL_M:g}; terrain inputs only)",
    )
    parser.add_argument("--routes", type=Path, help="route file, one id;x y z;x y z per line")
    return parser


def _check_usage(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if (args.old_terrain is None) != (args.new_terrain is None):
        parser.error("--old-terrain and --new-terrain go together")
    if args.old_terrain is None:
        for flag, value in (("--cell-m", args.cell_m), ("--local-m", args.local_m)):
            if value is not None:
                parser.error(f"{flag} needs --old-terrain and --new-terrain")
        return
    if args.cell_m is None:
        parser.error("--old-terrain and --new-terrain need --cell-m")
    if not (math.isfinite(args.cell_m) and args.cell_m > 0.0):
        parser.error("--cell-m must be a finite number of metres above 0")
    if args.local_m is not None and not (math.isfinite(args.local_m) and args.local_m >= 0.0):
        parser.error("--local-m must be a finite number of metres, 0 or more")


def _write_new(out: Path, text: str) -> None:
    try:
        with out.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except FileExistsError as error:
        raise CompareError(f"--out already exists, refusing to overwrite it: {out}") from error
    except OSError as error:
        raise CompareError(f"cannot write --out {out}: {error}") from error


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    _check_usage(parser, args)
    try:
        if args.out.exists() or args.out.is_symlink():
            raise CompareError(f"--out already exists, refusing to overwrite it: {args.out}")
        routes = None if args.routes is None else read_routes(args.routes)
        terrain = None
        if args.old_terrain is not None:
            numpy = _numpy()
            old_h, old_sha = read_heights(numpy, args.old_terrain)
            new_h, new_sha = read_heights(numpy, args.new_terrain)
            if old_h.shape != new_h.shape:
                raise CompareError(
                    f"terrain shapes differ: {old_h.shape} in {args.old_terrain}, {new_h.shape} in {args.new_terrain}"
                )
            terrain = {
                "numpy": numpy,
                "old_path": args.old_terrain,
                "new_path": args.new_terrain,
                "old_heights": old_h,
                "new_heights": new_h,
                "old_sha256": old_sha,
                "new_sha256": new_sha,
                "cell_m": args.cell_m,
                "local_m": DEFAULT_LOCAL_M if args.local_m is None else args.local_m,
            }
        meshes = []
        for path in (args.old_nm, args.new_nm):
            try:
                meshes.append(read_navmesh(path))
            except OSError as error:
                raise CompareError(f"cannot read {path}: {error}") from error
        report = compare(meshes[0], meshes[1], terrain=terrain, routes=routes)
        try:
            text = json.dumps(report, indent=1, allow_nan=False) + "\n"
        except ValueError as error:  # a cell size so large that a distance overflows
            raise CompareError(f"the report holds a non-finite number: {error}") from error
        _write_new(args.out, text)
    except (CompareError, NavmeshFormatError) as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_REFUSED
    print(json.dumps({key: value for key, value in report.items() if key != "structural"}, indent=1))
    return EXIT_PASS if report["status"].startswith("PASS") else EXIT_REVIEW


if __name__ == "__main__":
    raise SystemExit(main())
