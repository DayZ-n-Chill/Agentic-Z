# dayz-navmesh-compare

Compare two DayZ navmesh (`.nm`) files tile by tile, by structure rather than
bytes, and say whether the structural changes stay near a terrain edit and
away from the routes you care about. Read-only: the one file written is the
new `--out` report.

## Why not a hash

NavMeshGenerator does not write the same bytes twice. On one custom 12 km
terrain, two meshes generated over terrains that differ in 126 height vertices
hold 966 289 tiles each (983 x 983, the 12.5 m layout below). 966 286 of those
tiles changed bytes; 138 changed structure (polygon count, vertex count or
vertical bounds), all of them within 14.1 m of a changed vertex. Hashing the two
files, or their tiles, says that everything changed. Measured on files, not in
game.

## Verified envelope

Files written by DayZ Tools' NavMeshGenerator for one 12 km world, 12 288 m on
a side, with a TESM version 6 file header and DNAV version 11 tiles, in three
layouts: 12.5, 25 or 50 m tiles, 983, 491 or 245 tiles on a side. The
measurement above is on the 12.5 m one. Any other layout is read with the same
checks and is unverified: the report says which
(`layout.inside_verified_envelope`, and a line in `limits`).

Any other format version is refused. The vanilla `navmesh.nm` files unpacked on
`P:\DZ\worlds\` (Chernarus+, Livonia, Sakhal and Nasdara) carry TESM version 9
and DNAV version 12, so this tool refuses them at the file header.

## Run

Python 3.10 or newer, no install. Without terrain inputs it is stdlib only;
`--old-terrain` and `--new-terrain` need numpy.

```powershell
python scripts/tools/dayz-navmesh-compare/compare_navmesh.py --old-nm <accepted.nm> --new-nm <new.nm> --out <report.json>
python scripts/tools/dayz-navmesh-compare/compare_navmesh.py --old-nm <accepted.nm> --new-nm <new.nm> --out <report.json> --old-terrain <old.npz> --new-terrain <new.npz> --cell-m 6 --local-m 100 --routes <routes.txt>
```

| Status | Exit | When |
|---|---:|---|
| `PASS_NO_STRUCTURE_DELTA` | `0` | No tile changed structure, and the terrain inputs, if given, did not change |
| `PASS_LOCAL_STRUCTURE_DELTA` | `0` | Tiles changed structure, every one within `--local-m` of a changed terrain vertex, none under a route |
| `REVIEW` | `1` | Anything else; `review_reasons` says why |
| usage error | `2` | A flag missing, out of range or without the flags it needs |
| refused | `3` | An input refused or unreadable, the two mesh layouts or terrain shapes differ, numpy missing for terrain inputs, or `--out` already exists; nothing written, `error: <reason>` on stderr |

`review_reasons`, in this order:

| Reason | Meaning |
|---|---|
| `structure_changed_without_terrain_inputs` | Tiles changed structure and no terrain inputs locate them |
| `structure_farther_than_local_m` | A structural change lies farther than `--local-m` from every changed vertex, or no vertex changed at all |
| `terrain_changed_without_structure_change` | The terrain changed and no tile did: a stale mesh looks like this, and so does an edit too small to matter |
| `route_tile_changed` | A structural change lies under a route |

## Inputs

- **Meshes.** Both must have the same layout (tiles along x and z, tile width).
- **Routes**, one per line: `id;x y z;x y z`, the start and end points in
  metres (`y` is read and not used). Blank lines are skipped; UTF-8 with or
  without a byte order mark. Ids are unique. A malformed line is refused with
  its line number, and so is a file with no route. A route covers the rectangle
  between its two points widened by 25 m on every side, and every tile that
  rectangle meets, a tile touching its border included.
- **Terrain**: two NPZ files (`numpy.savez`), each holding a 2-D, finite,
  numeric array named `heights`, of one shape. The vertex at row `r`, column `c`
  stands at x = `c * cell_m`, z = `(rows - 1 - r) * cell_m`: row 0 is the
  largest z. Check that your export writes rows that way. `--cell-m` is required
  with them; `--local-m` defaults to 100.

## Report

`status`, `review_reasons`; `old_nm`, `new_nm`, `old_terrain`, `new_terrain`
and the SHA-256 of each file read; `layout` (tiles along x and z, `tile_m`,
`tiles`, `covered_x_m`, `covered_z_m`, the format versions and
`inside_verified_envelope`); `tile_m`, `tiles`; `serialized_changed_tiles`
(tiles whose bytes differ), `structural_changes` (tiles whose structure
differs); `changed_terrain_vertices`, `cell_m`, `terrain_extent_m`
(`[columns * cell_m, rows * cell_m]`), `max_structural_tile_distance_m`,
`local_threshold_m`; `route_margin_m` (25); `structural`, one item per structural
tile in `(x, z)` order with its `distance_m` to the nearest changed vertex
(0.1 m, `null` without one) and both tiles' `bytes`, `sha256`, `polygons`,
`vertices` and `y_bounds`; `route_tiles_changed`, route id to the structural
tiles under it; `limits`. Without terrain inputs their keys are `null`, and
without `--routes` the route keys. stdout carries the same report without
`structural`.

## What the reader checks

`navmesh_tiles.py` reads the 48-byte file header (magic `TESM`, version, tile
count, tiles along x and z; origin, tile width and depth), the offset table and
the 100-byte header that follows a 16-byte prefix in every tile, laid out as
Detour's `dtMeshHeader` (magic `VAND` on disk, version, tile x and z, polygon
and vertex counts, bounds). The uint32 at byte 8 of that prefix is the size of
the tile after the prefix and is checked against the bytes to the next tile or
the end of the file; the uint64 at byte 0 and the uint32 at byte 12 are not
interpreted. That size field matched on two 12.5 m `.nm` files of 966 289 tiles
each and two 50 m `.nm` files of 60 025 tiles each, all of one custom 12 km
terrain, and on the four vanilla DayZ 1.30 `navmesh.nm` files of Chernarus+,
Livonia, Sakhal and Nasdara (94 249, 65 536, 94 249 and 106 929 tiles, read with
the two version checks set to their 9 and 12): 2 413 591 tiles. It
refuses, naming the file and the check: a wrong magic or version in the file or
in any tile; a tile count other than tiles x times tiles z; an origin other than
(0, 0, 0); tiles that are not one finite, positive square; an offset table that
does not start at 0, is not strictly increasing or runs past the end of the
file; a tile past the end of the file or with no data after its header; a prefix
size that does not match the bytes to the next tile; a tile
outside the grid or present twice; non-finite bounds; horizontal bounds more
than 1 mm off the tile's cell. A tile's hash covers its header and data, not
the 16 bytes before the header.

## Limits

- No polygon topology, links or AI paths are read, and unchanged structure
  along a route is not a locomotion result.
- Both files are read whole into memory, with one small record per tile. A
  synthetic pair of 983 x 983 meshes of 120 MB each compared in 15 s with under
  0.8 GB of memory in one measured run.
- Locating costs structural tiles times changed vertices. It is meant for local
  edits; meshes over unrelated terrains can take very long.

## Design decisions

- The tile width and the grid come from the file header, not from the command
  line, and any layout that passes the checks is read, not only the three
  above. An offset table or tile past the end of the file is refused with a
  message rather than an exception, and non-finite bounds are refused (a NaN
  would pass a bounds check written as `abs(a - b) > tolerance`).
- Terrain inputs are optional, and numpy is imported only for them. The terrain
  grid is not fixed: it is `--cell-m` and the array's shape. `--routes` has no
  default.
- **Status when no tile changed structure.** It passes, unless the terrain
  inputs show changed vertices, which is reviewed
  (`terrain_changed_without_structure_change`). Without terrain inputs, any
  structural change is reviewed.
- A structural tile with no changed vertex has no distance (`null`), not
  `Infinity`, which is not JSON.
- A route covers the exact widened rectangle. Sampling points one tile apart
  along it could add a row or column past it and leave out a tile that only
  touches it.
- File hashes come from the bytes read: no `hashlib.file_digest`, which needs
  Python 3.11. Refusals exit `3` and write nothing; an existing `--out` is
  refused rather than asserted.

## Tests

```powershell
python -m pytest scripts/tools/dayz-navmesh-compare/tests -q
```

Meshes, route files and terrain NPZ files are synthetic, written by the tests.
The terrain cases need numpy and skip without it; the rest is stdlib only.
