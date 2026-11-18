# Winding and normal gate

What `check_dayz_winding.py` reads in a source `.p3d`, how to read its verdict and fixes, what a PASS does not cover, and the fixtures that pin its behaviour. The script is in `skills\dayz-model-tools\scripts\`, written `<scripts>` below. The winding rule it checks is in `axes-and-winding.md`.

The gate reads the mod's own MLOD file, so apart from the two textures its fixtures use, nothing here is a vanilla fact `P:\` could confirm. The in game results were measured on DayZ 1.29 on fixtures and on a large custom infected character.

## Why it exists

A Blender or Three.js preview is double sided, so it never shows DayZ's single sided culling. A model that is inside out (textures on the interior) shows only in game, and normals stored the wrong way show only as inverted lighting. Run the gate after building the `.p3d` and before every pack.

```cmd
python "<scripts>\check_dayz_winding.py" path\to\model.p3d
python "<scripts>\check_dayz_winding.py" path\to\model.p3d --py3d path\to\py3d
```

It needs the DayZ fork of py3d, 1.6.0 or newer, which it looks for at `--py3d`, then at `scripts/tools/py3d/` in this repo, then among the installed packages. A stock py3d is not the fork (`/dayz-p3d-audit` uses the same `scripts/tools/py3d/` copy); the gate says so and exits 2.

## What it checks

It reads every visual LOD in the MLOD convention of `axes-and-winding.md`, section "The map from Blender to DayZ" (the Blender to DayZ reflection that `py3d.blender_to_dayz()` writes): the vertex order cross product `cross(v1 - v0, v2 - v0)` and the stored shading normals both point away from the side meant to be seen, into the material, inward on a solid.

Winding is read per closed shell. Points are welded by position (5 decimals). A shell is a set of faces joined only through edges that exactly two faces share; `proxy:*` faces are left out. A shell is closed when each of its edges is used by exactly two of its faces. Its signed volume by winding (the sum of `dot(v0, cross(v1, v2)) / 6` over the fan triangles of its faces) must be negative, the same sign the absolute winding check of `/dayz-p3d-audit` uses.

- A positive shell is inside out: call `face.vertices.reverse()` on every face of it, or of the whole LOD when every shell reads positive.
- Never decide on the sum over the whole LOD; it can hide one inverted part.
- A shell whose faces disagree with their neighbours is made coherent first; the gate reads a closed shell's volume only once it is coherent.
- A closed shell meant to be seen from inside (a cavity, a room) reads positive by design; leave it out of the reversal. The gate is not for models seen from inside.

Normals are read per shell, corner by corner, as the reversal leaves them. Each corner normal is compared with its face's vector area (the sum over the fan triangles, which is right on a non convex quad too). A normal within 5 degrees of the face plane has no clear sign and is not read.

- Above 90 % of a shell's corners agree: the shell passes. That is a tolerance, not proof of every corner; smooth shaded exports carry some corners against their face.
- Below 10 % in every shell: the normals are stored outward. Negate the normal pool (`lod.facenormals[j] = (-x, -y, -z)` for every `j`) and keep the faces. Never reverse faces on that reading. The gate counts the corners that agree now and those the pool fix would turn, and it withholds the pool fix when part of the LOD was not read.
- Anything else: the gate lists the shells. Read them part by part, never one corner on its own sign. In a shell that reads cleanly, negate the normals of the faces that read against their winding and keep the rest; leave any other shell as it is for inspection. A corner normal smoothed across a sharp fold can point against a face that is wound right (the README in `scripts/tools/py3d/`, section "Winding: read this before trusting any validator", step 3), and a flat tetrahedron wound right, with one area weighted normal per point, has 6 of its 12 corners against their faces. That is why the fix works shell by shell, not corner by corner.
- py3d's own `_pct_normal_agreement`, the count the absolute check gives, reads only each face's first corner. The gate prints it alongside, over every face of the LOD.

Fix in a fixed order: the winding first with the normals untouched, then the normals against the settled winding.

A model that is coherent inside but inside out as a whole, which is what a silent Blender Z up to Y up export gives, fails on its volume wherever its shells are closed. A gate that also required normals to point outward would fail every correct export, because in this convention shading normals are stored inward.

Open parts (a sheet, an open tube) and flat parts (a face welded to its reversed twin) have no volume sign. Their faces are counted as not scored; check them with the visibility checks of `/dayz-p3d-audit` (`skills/dayz-p3d-audit/references/winding-diagnostics.md`, section "From Check B to fix"). A visual LOD with no closed shell cannot be measured.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | PASS. A PASS that left faces unscored says so on its own line |
| 1 | A model defect: winding or normals |
| 2 | Invalid input, an ODOL file, a py3d that is not the fork, or a LOD that cannot be measured |

## What a PASS does not cover

- A mirror. An export with reversed faces and negated normals under a determinant +1 transform passes too. Check handedness on an asymmetric feature (`_shared/wearables/references/body-export.md`, section "Chiral check in game").
- Open or flat parts, as above.
- Collision LODs. They have their own per component check (`axes-and-winding.md`, section "Collision LODs", and `/dayz-p3d-audit`).
- A debinarized model. The ODOL to MLOD converter's winding handling inverts the comparison, so never run the gate, or any winding comparison, on a debinarized vanilla model.
- Materials and textures. Inverted lighting can also come from the material or the `_nohq` map; the gate reads geometry only.

## Fixtures

`winding_fixtures/` next to the script holds four MLODs of one model: an "F" in relief on a plate, authored in Blender space, four closed boxes, 48 triangles. Its two textures are vanilla (`P:\DZ\data\data\beton1_co.paa` and `P:\DZ\data\data\black_co.paa`). `winding_fixtures/make_fixtures.py` rewrites them with py3d 1.8.0 or newer and refuses to write unless the three files tested in game come out byte for byte.

| File | How it was written | In game | Gate |
|---|---|---|---|
| `mirror_b.p3d` | `py3d.blender_to_dayz()` | Solid, the F reads correctly | PASS |
| `mirror_a.p3d` | `transform(ROT_X_NEG90)`, every face reversed, every normal negated | Solid, the F mirrored | PASS (a gate cannot see a mirror) |
| `mirror_c.p3d` | `transform(ROT_X_NEG90)` alone | Inside out and mirrored | FAIL on its volume (+0.1086): reverse every face, then negate the pool |
| `mirror_b_normals_out.p3d` | `mirror_b` with the normal pool negated | Not tested in game | FAIL: negate the pool, keep the faces |

`test_check_dayz_winding.py` next to the script holds the expected verdict lines for these and for about thirty variants built from them (one inverted box, an incoherent shell, open sheets, welded twins, proxies, a non convex quad, zero normals, ODOL and truncated input).

## Measured on a large character

Three builds of a large custom infected character, checked offline and in game:

- The build exported with `py3d.blender_to_dayz()` passes: 48 closed shells negative; 99.8 % of its 131,278 corner normals with a clear sign agree, 99.5 % in the body, its lowest shell, with 219 against their face and 200 within 5 degrees of it. The open ribcage tubes, 63.5 % of the faces, are not scored. In game it is solid and lit like vanilla.
- The two builds with normals stored outward fail on their normals: 0.2 % of their corners agree, every shell below 10 %. In game they are lit inverted (base shading on a client without textures), and one of them is also mirrored.
- The absolute check of `/dayz-p3d-audit` agrees: 99.3 % and -0.109 on the body for the correct build, 0.7 to 0.8 % for the others. On the fixtures both checks pass the two solid variants and fail the inside out one.
