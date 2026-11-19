# Traps in the clean UV atlas pipeline

Which Blender operators, unwrap settings, overlap and fold checks, smoothing methods and Windows habits silently break the clean UV atlas pipeline of `tools-uv-atlas.md`, each with what was measured and what to do instead. The numbers come from the same quad bike body; nothing here cites vanilla data.

## Blender operators

- `bpy.ops.uv.smart_project` run headless ignores the face selection and unwraps everything. The view chart pipeline never uses it; if you script around it, never rely on the selection.
- As a seam source over a whole mesh, `smart_project` is the right fallback when the topological cut collapses. On four quad bike material groups it gave 0.0 % collapsed and SAT = 0 where tree-cotree gave 3.6 to 78.0 % collapsed. Follow it with `seams_from_islands`.
- Never deduplicate bmesh loop UV wrappers by `id()`. The wrappers are temporary and their ids are reused, so loops get skipped silently. Visit each loop once. `loop.index` is not guaranteed to be set either: key corners by `(face.index, vert.index)`.
- Zero length face normals exist in real meshes. Guard every `Vector.angle()`.

## The unwrap

- Sparse seams make SLIM fail silently. With a tree-cotree cut graph (133 seam edges for 42 shells over 45k triangles), `MINIMUM_STRETCH` returned 78.3 % of the triangles collapsed, a median UV extent per triangle of exactly zero, and no warning. `ANGLE_BASED` on the same seams left 15.8 % collapsed and squeezed the layout into U from 0 to 0.048, which is 18 px/m. On another group both solvers returned a UV layer that was all NaN (109,086 NaN values, 6 per triangle for 18,181 triangles). NaN fails an `area > eps` test, so every triangle was filtered out and the check downstream died in `min()` on an empty list. An `except TypeError` around `bpy.ops.uv.unwrap` only catches a Blender that does not know the enum; check the returned layer for NaN and for collapse instead.
- A pinned SLIM re-solve is a chain of traps. `no_flip` defaults to False, and the default 10 iterations do not converge against pins (1,302 folded pairs measured). With pins, the automatic pack also drops the unpinned islands on top of the pinned ones, which shows as phantom SAT counts before packing. The pipeline uses local smoothing instead of pins; keep it that way.
- `no_flip=True` on a full re-unwrap makes charts that tend to wrap overlap in a spiral instead of flipping (133 leftover pairs on the rip). Flips are what the fold guard looks for, so never suppress them globally.

## Guards and checks

- Monte Carlo overlap has a noise floor. Only SAT = 0 proves zero overlap.
- The fold guard's detector must be the gate's own instrument. A Monte Carlo estimate over a percentage threshold can never clear an exact zero tolerance gate, because whatever sits below the threshold survives every round. With the exact per island SAT check as the detector, the engine group went from 31,481 pairs to 0 and the chassis from 5,839 to 0.
- One fold guard round is a cost rule, not a correctness rule. In the view chart pipeline a second pass chases 1 to 2 % cosmetic folds and multiplies the island count (32 to 84, and 26 to 508 in another run), so one round is right whenever it already leaves the exact check at zero. When it does not, iterate until the check is clean and accept the islands: 200 to 244 and 546 to 1,375 over 3 to 7 rounds, with texel density nearly unchanged. A mesh that still folds cannot ship. Pair counts do not fall steadily across rounds (4, 2, 7, 10, 0), so never stop at the first increase.
- Judge overlap only on the final packed layout, and prefer a rollback over cutting out many faces. More than about 40 offending faces after straightening means the stage hurt the mesh.

## Boundary smoothing

- A plain Laplacian on a closed curve shrinks it: it collapses the boundaries into the island (605k SAT pairs measured). Use Taubin lambda/mu smoothing and cap each corner's movement by the local boundary spacing.

## On Windows

- For a script sent from Windows into WSL, strip the CRLF line endings (`tr -d '\r'`) before running it with `bash`. Never escape quoted Python inline through PowerShell into bash; write a script file.
- Never write or edit `.py` files inside a folder synced by OneDrive; files have come back truncated or with null bytes. Work in a scratch folder and copy the results in, checking the size.
