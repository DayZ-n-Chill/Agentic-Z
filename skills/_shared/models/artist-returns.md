# Artist returns and outside binaries

What to check when a `.p3d`, `.paa` or `.rvmat` comes from outside the repo: a file an artist sends back, a provider delivery, or a corrected binary handed on. These are rules about handling files, measured on mod models, not facts about the vanilla game, so none of them is checked on `P:\`.

Every check runs offline and reads the `.p3d` with py3d (`scripts/tools/py3d`); the API is in `py3d-generation.md`.

## Where the file came from

Before you edit any binary from outside the repo, list the live asset next to the newest outside delivery of it. Compare the SHA-256, the size, the modification date and a structural count (for a mesh, the face count). A newer `_artist_drop/`, `_from_provider/` or `scratch/` folder is something to settle first, not background.

Settle every difference in one of three ways:

- take the outside delivery in now, with a stated budget;
- keep the live asset on purpose, written down with an owner and a review date;
- update the provider's package, when the live asset is the newer one.

"Fix it separately later" with no owner and no date settles nothing.

Licensing is part of it. A packaged README or LICENSE is as old as the package. Check the publisher's current statement; when it and the packaged file disagree, the current statement wins.

## Before you deploy an artist's return

An artist's exporter keeps what is visible and drops the rest. A LOD that came back untouched is suspicious, not safe: the visual shape may have moved while View Geometry, Fire Geometry, `boundingbox_min` and `boundingbox_max` and the `*_axis` points stayed where they were and now lie.

A typical return: a gun rack came back with real visual gains (modelled hinges instead of a 1792 face wire mesh, a cabinet 0.436 m deep instead of 0.268 m), but no Geometry LOD, 7 proxy triangles deleted from the visual LOD, an empty `hideproxy` selection, and `Component01` and the proxy paths in lower case. The untouched collision boxes left the front 0.168 m outside Fire Geometry, and `doors1_axis` sat 198.8 mm behind its own door leaf.

Run these checks against the file you sent, in this order:

1. Count the LODs with `classify_lod_resolution`. Geometry is the first to go missing.
2. Check the proxy selections in the visual LOD, View Geometry and Fire Geometry, all inside their bone. Compare their coordinates with the sent model; if they changed, the in-game alignment is gone.
3. Compare the visual LOD bounding box with the collision boxes and with `boundingbox_min` and `boundingbox_max`. If they differ, rebuild the boxes, not the visual.
4. Measure each `*_axis` against the part it turns. A distance like the 198.8 mm above stands out on its own.
5. Compare the case of `Component01` and of the mod's own paths with the last good file.
6. Look for orphan points and leftovers of replaced geometry. One stray point 0.57 m outside the model poisons any bounding box computed from `lod.points`.

## Taking the return back in

- `#SharpEdges#` entries are point indices. Any filter that renumbers points leaves them pointing at the wrong points without an error, so remap them by hand.
- A py3d round trip of a file from another exporter is not byte identical (py3d rewrites `#UVSet#` and drops an empty `#SharpEdges#`), but it keeps points, faces, selections, properties and hard edges. Check the round trip before editing; only then touch the file with py3d. A `.p3d` written by py3d comes back identical.

## When the artist sends more than one round

- The artist works from an old copy, so every fix made after it comes back undone. Two racks returned on the same day both brought back a 180 degree proxy rotation that had been removed: exactly `R_orig·Ry(180)` with the anchor fixed, on all 10 proxies. A proxy triangle's legs are 1 to 2 mm long, so the turn moves its points about 4 mm and no view shows it. Keep the list of fixes as a script you can run again, run it whole on every return, and compare with the deployed file, not with the last delivery.
- Never write a fix as a change on top of whatever the delivery brought. `doors1` computed as `delivered_value + dz` goes wrong on the next delivery when the memory origin moves. Anchor to geometry in the file (`Z = leaf_midplane + offset`) and check that the formula reproduces the value already deployed.
- A smaller number is not a regression by itself. One return gave back 43 mm of depth because the door moved inside the body, and the useful gap grew from 0.168 to 0.187 m to 0.284 to 0.303 m. Measure what the part does; do not judge the change by its sign.
- Never apply a self-undoing fix (a rotation, mirror or sign change) to a whole batch. It undoes itself on the files that did not need it. Read each proxy frame, class it against the deployed file as `SAME`, `R*Ry(180)` or `OTHER`, fix only the class you measured, and check frame and anchor afterwards.
- When a return keeps the whole non visual part of the model, a rebuild must stop rather than add a second copy. Take selection and material path case from a map read from the deployed file; never invent canonical names. Restore `Component01` exactly when the deployed file has it.
- Reimport checks test what must always hold, not one delivery's topology. For symmetric parts, require both halves to match in component count, face count and material split, plus floors that reject a half that is incomplete. Treat optional parts as warnings. After changing a check, run it on the previous delivery and require the previous output to stay byte identical.

## Three hashes for a corrected binary

Every corrected binary records three SHA-256 values: the deployed file, the repair input and the repair output.

- Require the deployed file to equal the repair input before you deploy. A small change from input to output says nothing about an unseen change from deployed to input.
- Compare each model's PBO size change with untouched models, and stop when the change does not fit the edit you made.
- Pick backups by a stamped name or by hash, never by modification time; copying a file can keep the old timestamp.

## Find a file's source by its content

A file name says what someone meant; a count says what is there. Before you decide anything about a derived file, identify its input by a content fingerprint: face counts per material or per selection, class counts, or a hash of a stable block.

A quad body shows why. Its `obj\body_lod0.obj` did not match the `.p3d`'s LOD0 (82,266 vertices against 22,004), which looked like a stale source. In fact the numbering was off by two: resolution 0 came from `body_lod2.obj` (22,105 vertices against 22,004) and resolution 1 from `body_lod3.obj`, while `lod0` and `lod1` were higher detail versions that never ship. Counting faces per material in each candidate settled it: 11 of 14 materials matched exactly, and the other three were off by a handful, which is the assembler's cleanup.
