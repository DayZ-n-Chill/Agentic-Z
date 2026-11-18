# Selections for action raycasts

How to build named selections exact enough for the game's action raycasts (a seat aimed at from both sides of a vehicle, a handlebar grip, a door handle, a hood latch, a tank cap) with a face painter and a refiner. The side test for seats is in `get-in-sides.md`. This is a tooling pattern; the numbers were measured on one test quad and none is a vanilla fact.

## Why a box filter is not enough

The quick way to build a selection is a script that takes every face whose centre lies in a box. It works on flat topped shapes and leaks on real vehicle geometry:

- A wedge shaped seat with sloped sides: the box takes the top and misses the side panels a player outside aims at.
- A fender that wraps round the seat: the box takes the wheel arch too, or leaves a bare stripe between seat and fender.
- A handlebar with mirrors and levers: the box takes the mirror housings.

When it fails, all you see is an action that sometimes misses, not which face leaked.

## The painter

A Three.js page that:

1. Loads the model's geometry, best from the data block of a viewer that already exists (see "Reusing a baked viewer").
2. Draws one mesh per material, so face indices map cleanly to the model's groups.
3. On mouse down raycasts against the mesh and toggles the hit face (`intersection.faceIndex`) in the current brush.
4. Offers two or three brushes, one per selection, with the active one clearly coloured.
5. Removes a face on Shift and click and switches brush on right click, so the user keeps the mouse in place.
6. Exports JSON: one array per brush of `{material_index, face_index}`, or plain face indices for a one material model.

Seed each brush with a rough guess, so the user refines instead of starting from nothing. The page runs from `file://` because the user opens it from disk, so use a UMD build of Three.js, r147 or earlier (r148 removed the UMD add-ons in `examples/js` such as OrbitControls and the loaders), with no ES module imports.

## Overlays in a lit viewer

Draw painted faces, and any overlay in a Three.js scene with physically based lighting (anchor markers, axis lines, debug arrows), with `MeshBasicMaterial`, not `MeshStandardMaterial`; lighting and an environment map dim an overlay until a yellow brush on chrome disappears. Push overlays 5 mm out along their normals, or they flicker against the base as the camera moves. Use saturated colours: yellow `0xffe000`, green `0x00ff66`, blue `0x33bbff`.

## The refiner

The painter is exact where the user clicked, but a selection needs full coverage, and painting every face of a seat takes ten minutes. The refiner grows each brush along shared edges, capped by distance:

```text
input:  painter export (face indices per brush)
        mesh geometry (positions, indices)
        cap: 6 cm for small parts (grips), 10 cm for large surfaces (seat)
        optional height, depth or radius filters per brush

for each brush:
    seeds = the painted faces
    repeat N times (1 for a handlebar, 2 for a seat):
        for each face in the brush, for each neighbour sharing an edge:
            skip it if it is already in the brush
            skip it if it is further than the cap from every seed
            skip it if it fails the brush's filters
            otherwise add it

output: the grown face set per brush
```

- Measure the cap from the seeds, not from the growing edge. From the edge, a brush leaks across a thin neck such as the joint between seat and frame.
- Give each brush its own filters. A handlebar brush needs "above the steering column"; a seat brush needs none. One global filter either lets the handlebar leak down or blocks the seat.

On the test quad: handlebar, 1 step, cap 6 cm, above 0.83 m and within 0.40 m of the pivot, 2383 faces; driver seat, 2 steps, cap 10 cm, no filter, 170 faces; passenger seat, the same settings, 36 faces.

## Reusing a baked viewer

Parsing a `.p3d` of 10 MB or more with py3d took about 30 seconds, enough to hit a command time limit. An HTML viewer already built for the model holds the geometry in a JSON literal: a page from the 3D viewer tool (`_shared/models/tools-3d-viewer.md`) writes `const M={...}` with positions, normals, UVs and indices as base64 strings inside the JSON; a page from the model tools' `.p3d` inspector writes `const R={...}` as plain JSON. Read the literal, decode any base64 arrays (about a second) and build the painter on it; the geometry is already in the right frame with materials apart. Parse the `.p3d` again only when no viewer exists or the geometry changed, and tell a user who asks for a new viewer of a model that already has one.

## From problem to game

1. Name the selections that are missing or wrong: the action misses from some angle, a hit zone is too small, a turning part pivots wrong.
2. Find an existing viewer with the geometry baked in.
3. Build the painter on that data. The first takes about a day; later ones are copies.
4. The user opens it, corrects the seeded brushes and exports JSON.
5. Run the refiner with caps and filters for this model.
6. Write the result into the `.p3d` with the model tools' `.p3d` inspector or a project script that follows `_shared/py3d-mlod-notes.md`, "Writing a `.p3d` from a script".
7. Look at the selection in Object Builder or reopen the viewer.
8. Test in game: start the action from every angle a player would, and adjust caps and filters if coverage is wrong.

The painter does not change geometry (a seat with the wrong shape needs the model fixed first), does not add memory points or change an animation axis (`handlebar-and-steering.md`), and does not prove the action works: the raycast still has to reach one of the faces from where the player stands.
