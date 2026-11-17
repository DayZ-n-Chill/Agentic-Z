# Round-trip caveats

What an extract, edit and rebuild cycle of `/dayz-p3d-inspector` can lose or misread, how to test for it, and what is planned but not built. Read this before any rebuild that will replace a working model.

Tool behaviour measured on mod models, not yet checked on `P:\`. What a selection is, and the vanilla names involved, is in `_shared/models/selections.md`; script reads a selection's position with `GetSelectionPositionLS` (`P:\scripts\3_game\entities\object.c:863`).

## Memory selections can be wiped by a rebuild (SP-002)

**Status: not fixed in the builder.**

A memory selection is a membership set: which points belong to it. The builder's `build_memory_lod()` rebuilds the Memory LOD from `recipe.memory_points[].selections` and `recipe.axes`. On real models the extractor leaves both of those empty; the true membership sits in `recipe.lods[memory].selections`, which the builder ignores. A rebuild can therefore wipe memory selections while their names and the geometry still look right. Measured on a vehicle model with a weapon rig: 79 memory selections and 132 faces lost.

In game the model then loses whatever those selections carried: door, wheel and suspension axes, damage zones, seats, proxies. A backup of the Recipe does not help, since the Recipe is what is incomplete.

**Round-trip test** (run it before a rebuild you mean to keep):

1. Extract the original model to `a.json`.
2. Build `a.json` to a scratch `.p3d`, with `--no-autofix`.
3. Extract the scratch model to `b.json`.
4. For every LOD compare the selection names and, for each name, `vertex_count` and `face_count`. Compare counts, not only names. Any selection that lost members fails the test.
5. Running the cycle twice must change nothing more: for a tool that sorts, merges or normalizes, check that a second pass equals the first, and say which fields are allowed to change on the first pass (LL-109).

**If the test fails**, do not rebuild. Edit the MLOD directly with py3d and write it with py3d; the inspector stays fine for looking.

**After any debinarizing step**, check membership the same way: read the MLOD with py3d and confirm `len(sel.points)` or `len(sel.faces)` is above zero for the memory selections, the `_axis` ones first. A converter can drop it too (`_shared/models/selections.md`, "Membership lost by tools").

## A stale Recipe (SP-022)

A Recipe goes out of date when the `.p3d` is edited by something else (Object Builder, py3d, a converter) and not extracted again. Before reporting anything odd seen in the viewer:

1. Extract again and compare with the Recipe in hand.
2. If they differ, the `.p3d` is right and the Recipe is stale.
3. If they match and the viewer still looks wrong, read the model with py3d directly before calling it a bug.

Find the file that was really edited first, including backup copies that mark where someone intervened, and extract from that one. A bounding box that looks plausible does not prove the file is the right one (LL-177).

## Selection indices: points, not triangle corners (SP-028)

`selections[].vertices` in the Recipe index the LOD's unique points (`0` to `len(lod.points) - 1`). `geometry.positions` is a triangle soup with three entries per face. Using a selection's indices on `positions` gives coordinates that look sensible and are wrong: they land on unrelated geometry and suggest a selection sits on the wrong part of the mesh. One such misreading reported a turret selection as lying on a car's spikes; the model was correct.

Before reporting any selection or structure fault from Recipe data, check it on the py3d objects: take `lod.selections[name].faces`, read each face's corner points, and take the bounding box of those.

## py3d selections are dictionaries

`lod.selections` is an ordered dictionary keyed by selection name; looping over it gives names, not objects. Each selection's `points` and `faces` are dictionaries keyed by the point or face object with its weight as the value, so they cannot be indexed by number. To get indices, build a lookup from `id(object)` to position. An `AttributeError: 'str' object has no attribute 'name'` or a `TypeError: 'Selection' object is not subscriptable` means old code that assumed otherwise. The same note is in `_shared/py3d-mlod-notes.md`.

## Unused bytes in a triangle's face record (SP-229)

An MLOD face record always has room for four corners. A triangle leaves the fourth slot unused, and Object Builder can leave non-zero bytes there after faces are reordered or edited. Those bytes carry no data and binarize discards them (documented by the `p3dtxt` tool's README and source). So a changed file hash after a rewrite does not by itself prove data loss. To compare two versions, compare the parsed fields and ignore the unused fourth slot of triangles, or binarize both and compare the results. Expect byte identity only from a tool that promises to write zeros there. This is separate from the memory selection loss above.

## Before saying a part is missing (LL-010)

List the model's proxies, look at their sizes and open the large ones. The config only shows what is rigged; geometry can live in a proxy model. Split a debinarized model into its connected parts when in doubt.

## Planned, not built

- **Proposal from a raw mesh.** Turning an OBJ, FBX or GLB into a Recipe with guessed memory points and selections is not written; the extractor only reads an existing `.p3d`.
- **Selection painting.** Colouring faces by selection, clicking faces to assign them, showing inverted faces, checking component coverage. The animation pipeline skill already has a selection painter that writes back with py3d; start from that one.
- **Animation preview.** Reading `model.cfg`, sliders for animation phases, switching material states.
