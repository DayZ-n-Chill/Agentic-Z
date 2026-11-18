# Rip textures and materials

How to texture a car ripped from a racing game: which UV channel the swatches use, where the factory paint colour is stored, how to give every mesh the right material type, and how glass, interior and two-sided surfaces behave in DayZ.

Measured in game and offline on cars built from rips (`rip-import.md`). The vanilla glass cited below was read on `P:\`.

## What the rip ships for textures

- There is no single paint atlas. Body paint is a constant colour, and the rip's own renders are clay, with procedural library materials, so there is no painted bitmap to copy. The DayZ target is a solid colour per piece plus ambient occlusion.
- The per-part swatch PNGs named `..._AO_AO_*` are packed tangent-space normals in RGB plus ambient occlusion in alpha, not greyscale AO: 512 pixels square, about 40% island coverage, and only on relief parts (bumpers, fenders, skirts, wings, hood). The main shell has none; flat paint is right for a smooth panel. Build `_co` as `paint × (AO_MIN + (1 - AO_MIN) × AO)` with `AO_MIN` about 0.55 and full paint off the islands, and `_nohq` from the swatch RGB with flat `(128,128,255)` off the islands. Whether the green channel needs flipping can only be checked in game.
- Livery masks are nearly empty on a stock colour car (1 to 11% coverage on one car). Check coverage before planning a livery bake; with empty masks the body is just glossy paint.

## The swatch UV channel

The importer reads five UV layers, `TEXCOORD0` to `TEXCOORD4`. `TEXCOORD2` is the per-part `[0,1]` swatch space; 0, 1 and 4 are wide tiling channels (values up to about 30). Read `bm.loops.layers.uv.get("TEXCOORD2")`, not the active layer.

The importer's `use_materials=True`, which would give the true texture to channel binding, fails on most parts without the game database. So apply each swatch through `TEXCOORD2` in Blender as unlit emission and check by eye that the normal detail lands on the panel edges and curves. An overlap score between UVs and swatch coverage is confused by mirrored islands and partial coverage (0.28 to 0.81 even when aligned).

Some faces do not follow that rule. Bezel labels, decals and shifter graphics sample their atlas from `TEXCOORD0` without a V flip. Tiled patterns use `TEXCOORD1` multiplied by the material's tiling factors. DayZ materials add no UV transform by default, so bake the tiling into the face UVs and rely on sampler wrapping. Check an overlay of UVs on the atlas before accepting either.

## The factory paint colour

The exact paint is in the rip's `ManufacturerColors.bin`. Each entry holds selection names (Body, Hood, Mirror, Wing and so on), three float32 sRGB values and a library material path; entry 0 is the default colour. For each `Game:\Media...materialbin` path, the three floats are the 12 bytes ending one byte before the path's `Game`. Decode the whole table as a check: white reads about 0.99, black about 0.08. One car's default decoded to (0.0157, 0.290, 0.639), `#044AA3`; a guessed value was wrong.

- Use a flat solid `_co` for body paint, not the swatch. On a solid `_co` the arbitrary chunk UVs do not matter. A per-part swatch `_co` must fill off-island space with the paint colour, never black. The swatch's DXT1 blocks read as pixelated on the paint.
- Pearl and metallic paint (flake and clear coat) cannot be reproduced in the Super shader. Approximate it with the source colour and the Super stages (specular, fresnel, environment). Raising `specularPower` from 180 to 300 with a brighter specular map improved the reflection, but high specular magnifies any normal map fault (green flip, DXT1 banding) into speckle. Keep specular low (about 0.28) so the shader does not wash the colour out, and push the colour a little more vivid than the raw value to make up for the missing flake, or darken it a touch if it reads light.
- Convert linear values to sRGB for a `_co` PNG; the procedural `#(argb)color()` placeholders are already linear.

Black panels plus see-through areas are winding, not texture. Decode the deployed `_co.paa` and measure how much is dark before touching textures; on one car every `_co` was solid colour with no dark pixels, so the black panels were back faces.

## Material by type, from the source

Assigning paint, metal and glass by eye is the largest per-car time sink, and the source already knows. Each mesh embeds its material path, and the folder in that path (`_library\materials\_fmnext\<TYPE>\`) gives its type: paint, metal, chrome, glass, plastic, interior (leather or fabric), rubber, light, carbon, mirror, black (glass edge, black frame), plate, badge.

- Classify by the path folder, not the instance name, which lies: roll cage meshes named like leather or plastic resolve to a steel metal material. A `specialcase` folder is keyed by file name (black frame and black hole are black, `mirror_*` mirror, undercarriage metal). A painted metal path is paint, wings included.
- Classify per mesh, not per part: 50 of 84 parts on one car used several materials. The importer already splits meshes, naming each Blender object `"<mesh.name> <material.name>"`, so each face can be tagged with its type by object name without changing geometry.
- Map each type to a DayZ `.rvmat` once: paint to car paint with the colour, metal to gunmetal or steel, chrome and mirror to chrome, glass to glass, black to opaque dark, plastic and rubber to matte black, interior to leather or fabric, light to emissive, carbon to carbon. Only paint on a paintable selection (Body, Hood, Mirror, Wing, as listed in `ManufacturerColors.bin`) gets the body colour.
- Repaint only metal, chrome, mirror, black and carbon. Never repaint plastic: widebody flares are plastic in the source but painted body colour (54% of one car's faces), and turning them black wrecks the car. Paint, glass and interior keep their shared materials.
- Apply it to the deployed `.p3d` without rebuilding geometry: build a map from face centroid in DayZ space to type, match each visual face by rounded centroid (100% matched, worst distance 6 µm on one car), and change only `face.material` and `face.texture`. Rebuilding would lose the wheel proxies, exterior winding, View Geometry and crew. Pack with `-Build -PackOnly` so the per-face materials survive. Confirmed in game on the exterior.

Per-piece materials (wipers plastic, bumper metal) must come from the source part map, never from bounding boxes, which catch neighbouring pieces.

## Glass

Clone the vanilla sedan glass, `P:\DZ\vehicles\wheeled\civiliansedan\data\glass.rvmat`: ambient and diffuse alpha 0.75, `renderFlags[]` with `"noZwrite"`, the Super shader, `gazglass_nohq.paa` in `Stage1`. Its textures ship in `DZ_Vehicles_Wheeled`, which a car already requires. It is translucent and does not depend on UVs, which also cures "missing parts" that were just untextured windows. Building glass uses the Super shader too (`P:\DZ\structures\data\alpha\glass_int_new.rvmat`); the `Glass` pixel shader appears only in `P:\DZ\data\data\glass_enviro.rvmat` and `chrome_enviro.rvmat`, which nothing vanilla references. One test car used alpha 0.22 to 0.32, a value tuned for that mod.

Keep car glass one sided with the raw glTF winding. A rip's inner glass panes are the cabin side of a two-sided pair, not a doubled pane fighting for depth. Doubling glass faces blends the alpha twice and makes it too opaque. If glass is invisible from outside, fix winding, not alpha.

## Interiors and two-sided surfaces

MLOD per-face `flags` do nothing in DayZ, because binarize drops the field. Three MLODs that differed only in `face.flags` on 2092 faces (`0`, `0x00000020`, `0x00020000`) binarized to byte-identical models, while moving one point by 1 cm or clearing those faces' texture did change the output. So no flag value makes a face two sided; measured offline.

To show a surface from both sides, duplicate it: add a reversed twin of each face with the source's negated per-vertex smooth normal, deduplicated in the normal pool. A flat per-face normal on the twin breaks vertex sharing and blows up the resolved count (22k became 103k flat, against 44k with smooth negated normals). The 65535 ceiling is a binarize limit; pack only MLOD tolerated an 82k View Pilot, but stay under it.

The first-person view of a rip interior is best fixed by orientation, not by doubling: keep the raw winding and put the interior in its own proxy, like vanilla `prox_int` (`rip-wheels-and-doors.md`). Double siding is a fallback that costs about twice the vertices.

The source's interior materials are nearly black (diffuse 0.015, 0.13 and 0.095 on one car), so a solid cabin reads as a void in DayZ light. Raise them (to 0.04, 0.20 and 0.16 there). A black material shared with exterior trim greys the trim slightly too. A grey looking interior needs proper colours, not geometry work.

## Duplicate faces

Speckle all over the body was the source assembly emitting every body face twice: coincident, same winding, different UV channel, before any decimation. Count coincident faces by point set and winding, and by identical positions (clean meshes score about 0, duplicated ones 10 to 70%). Keep one face per position set and normal direction, keep deliberate opposite-winding pairs, and never touch a `proxy:` face. One car lost 20320 faces this way, confirmed in game. Add the pass to the importer; the full entry is in `visual-gates-and-winding.md`.
