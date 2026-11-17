# Painting selections for action raycasts

A tooling pattern for named selections whose surface must be exact enough for the game's action raycasts: a seat that can be aimed at from both sides of a vehicle (`dual-entry-action-pattern.md`), a handlebar grip, a door handle, a hood latch, a tank cap. The numbers were measured on one quad model and nothing here is a vanilla fact.

## When a bounds filter is not enough

The simple way to build a selection is a script that takes every face whose centre lies inside a box. That works for flat topped shapes and leaks on real vehicle geometry:

- A wedge shaped seat with sloped sides: the box takes the top and misses the side panels a player outside aims at.
- A fender that wraps round the seat: the box either takes the wheel arch too or leaves a bare stripe between seat and fender.
- A handlebar with mirrors and levers: the box takes the mirror housings.

Worse, when it fails you only know that the action sometimes misses, not which face leaked.

## The painter

Build a Three.js page that:

1. Loads the model's geometry, ideally from the data block of a viewer that already exists (see "Reuse a baked viewer" below).
2. Draws one mesh per material, so face indices map cleanly to the model's groups.
3. On mouse down raycasts against the mesh and toggles the hit face (`intersection.faceIndex`) in the current brush.
4. Offers two or three brushes, one per selection being painted, with the active one clearly coloured.
5. Removes a face with Shift and click; switches brush with right click, so the user does not move the mouse away.
6. Exports JSON: one array per brush of `{material_index, face_index}`, or plain face indices for a single material model.

What building one showed:

- **Seed each brush with a rough guess**, so the user refines instead of painting from nothing.
- **Draw painted faces with `MeshBasicMaterial`**, not `MeshStandardMaterial`. Lighting and an environment map dim an overlay until a yellow brush on chrome is invisible.
- **Push painted faces 5 mm out along their normals**, or the overlay flickers against the base as the camera moves.
- **The page runs from `file://`**, because the user opens it from disk. Use a UMD build of Three.js (r147 or earlier, because r148 removed the UMD add-ons in `examples/js` such as OrbitControls and the loaders) and no ES module imports.

## The refiner: grow along shared edges, capped by distance

The painter's export is exact where the user clicked, but a selection wants full coverage and painting every face of a seat takes ten minutes. A second step grows each brush:

```
input:  painter export (face indices per brush)
        mesh geometry (positions, indices)
        cap: 6 cm for small parts (grips), 10 cm for large surfaces (seat)
        optional height, depth or radius filters per brush

for each brush:
    seeds = the painted faces
    repeat N times (1 for a handlebar, 2 for a seat):
        for each face in the brush, for each neighbour sharing an edge:
            skip it if it is already in the brush
            skip it if it is further than the cap from EVERY seed
            skip it if it fails the brush's filters
            otherwise add it

output: the grown face set per brush
```

- **The cap is measured from the seeds, not from the growing edge.** Measuring from the edge lets a brush leak across a thin neck, such as the joint between seat and frame.
- **Filters are per brush.** A handlebar brush needs "above the steering column"; a seat brush needs none. One global filter would either let the handlebar leak down or block the seat.

The quad's numbers: handlebar, 1 step, cap 6 cm, height above 0.83 m and within 0.40 m of the pivot, 2383 faces; driver seat, 2 steps, cap 10 cm, no filter, 170 faces; passenger seat, the same settings, 36 faces.

## Reuse a baked viewer

Parsing a `.p3d` of 10 MB or more with py3d took about 30 seconds when measured, enough to hit a command time limit. An HTML viewer already built for the same model (by the dayz-3d-viewer or dayz-p3d-inspector skills) holds the geometry in a JSON literal: a dayz-3d-viewer page writes `const M={...}`, with positions, normals, UVs and indices as base64 strings inside the JSON; a dayz-p3d-inspector page writes `const R={...}` as plain JSON with no base64. Read that literal, parse it and decode any base64 arrays (about a second) and build the painter on it: the geometry is already in the right frame with materials separated. Parse the `.p3d` again only when no viewer exists or the geometry changed. Say this to a user who asks for a new viewer of a model that already has one.

## Overlays in any lit viewer

The two overlay rules above apply to every overlay in a Three.js scene with physically based lighting: anchor markers, axis lines, debug arrows. Use an unlit material, push the overlay 5 mm along the normals, and use saturated bright colours (yellow `0xffe000`, green `0x00ff66`, blue `0x33bbff`).

## From problem to game

1. Decide which selections are missing or wrong: the action misses from some angle, a hit zone is too small, a turning part pivots wrong.
2. Find an existing viewer that has the geometry baked in.
3. Build the painter on that data. The first one takes about a day; later ones are copies.
4. The user opens it, corrects the seeded brushes and exports JSON.
5. Run the refiner with caps and filters for this model.
6. Write the result into the `.p3d` with the dayz-p3d-inspector skill or a project script. That script must follow the rules in `py3d-1.0.0-quirks.md`.
7. Look at the selection in Object Builder or reopen the viewer.
8. Test in game: start the action from every angle a player would. Adjust caps and filters if coverage is wrong.

## What it does not do

- It does not change geometry. A seat with the wrong shape needs the model fixed first.
- It does not add memory points or change an animation axis (`handlebar-and-steering-config.md`).
- It does not prove the action works. Coverage is necessary; the raycast still has to reach one of the faces from where the player stands.
