# The offline winding and normal gate

Covers what `check_dayz_winding.py` reads in a source `.p3d`, how to read its verdict and fixes, what it cannot see, the fixtures that pin its behaviour, and how it came to its current form.

How to read the marks: the gate reads the mod's own MLOD file, so nothing here is a vanilla fact that `P:\` could confirm, apart from the two textures the fixtures name. "In game" results were measured by the source project on the date given (DayZDiag 1.29.163709).

## Why it exists

A Blender or Three.js preview is double-sided, so it never shows DayZ's single-sided culling. A model that is inside-out (textures on the interior) only shows in game, which costs a test cycle, and normals stored the wrong way only show as inverted lighting. Run the gate after building the `.p3d` and before every pack.

```cmd
python "<skill-dir>\check_dayz_winding.py" path\to\model.p3d
python "<skill-dir>\check_dayz_winding.py" path\to\model.p3d --py3d path\to\py3d
```

It needs the py3d DayZ fork (1.6.0 or newer), which it looks for at `--py3d`, then at `scripts/tools/py3d/` in this repo, then among the installed packages. The upstream py3d that `/dayz-p3d-audit` installs is not the fork; the gate says so and exits 2.

## The convention it checks

It reads every visual LOD in the MLOD convention of Rule 12 of the dayz-model-pipeline skill, which `py3d.blender_to_dayz()` writes: the vertex-order cross product `cross(v1 - v0, v2 - v0)` and the stored shading normals both point away from the side meant to be seen, into the material, inward on a solid.

**Winding, per closed shell.** Points are welded by position (5 decimals). A shell is a set of faces linked only through edges that exactly two faces share; `proxy:*` faces are left out. A shell is closed when each of its edges is used by exactly two of its faces. Its signed volume by winding (the sum of `dot(v0, cross(v1, v2)) / 6` over the fan triangles of its faces) must be negative, the production sign of the absolute winding check in dayz-p3d-audit.

- A positive shell is inside-out: call `face.vertices.reverse()` on every face of it, or of the whole LOD when every shell reads positive.
- Never decide on the sum over the LOD. It can hide one inverted part.
- A shell whose faces disagree with their neighbours is made coherent first; the gate reads a closed shell's volume only once it is coherent.
- A closed shell meant to be seen from inside (a cavity, a room) reads positive by design; leave it out of the reversal. The gate is not for models seen from inside.

**Normals, per shell and corner by corner**, read as the reversal leaves them. Each corner normal is compared with its face's vector area (the sum over the fan triangles, which is right on a non-convex quad too). A normal within 5 degrees of the face plane has no clear sign and is not read.

- Above 90 % of a shell's corners: they agree. That is a tolerance, not proof of every corner; smooth-shaded exports carry some corners against their face.
- Below 10 % in every shell: they disagree. With the winding right, that means normals stored outward. Negate the normal pool (`lod.facenormals[j] = (-x, -y, -z)` for every `j`) and keep the faces. Never reverse faces on that reading. The gate counts the corners that agree now and that the pool fix would turn too, and it withholds the pool fix when part of the LOD was not read.
- Anything else: the gate lists the shells. Read them part by part, never a corner on its own sign. In a shell that reads cleanly, negate the normals of the faces that read against their winding and keep the rest; leave any other shell as it is, for inspection. A corner normal smoothed across a sharp fold can point against a face that is wound right (the "Winding" section of the README in `scripts/tools/py3d/`, step 3).
- The count that py3d's own `_pct_normal_agreement` gives (the absolute check's count) reads only each face's first corner. The gate prints it alongside, over every face of the LOD.

The fixes come in a fixed order: the winding first with the normals untouched, then the normals against the settled winding.

**Not scored.** An open part (a sheet, an open tube) or a flat one (a face welded to its reversed twin) has no volume sign. Its faces are counted as not scored; check them with the visibility battery of dayz-p3d-audit (its winding diagnostics reference, section "From Check B to fix", under `skills/dayz-p3d-audit/references/`). A visual LOD with no closed shell is not measurable.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | PASS. A PASS that left faces unscored says so on its own line |
| 1 | A model defect: winding or normals |
| 2 | Invalid input, an ODOL file, a py3d that is not the fork, or a LOD that is not measurable |

## What a PASS does not cover

- **A mirror.** The determinant +1 export with reversed faces and negated normals passes too. Check chirality on an asymmetric feature (the chiral check in `references/character-rigging.md` section 6).
- **Open or flat parts**, as above.
- **Collision LODs.** They have their own per-component check in the dayz-model-pipeline skill (Rule 18) and in `/dayz-p3d-audit`.
- **A debinarized model.** The ODOL to MLOD converter's winding handling inverts the comparison. Do not use the gate, or any winding comparison, on a debinarized vanilla model.
- **Materials and textures.** Inverted lighting can also come from the material or the `_nohq` map; the gate reads geometry only.

## Fixtures and measured results

`winding_fixtures/` next to the script holds four MLODs of one model: an "F" in relief on a plate, authored in Blender space, four closed boxes, 48 triangles. Its two textures are vanilla (`P:\DZ\data\data\beton1_co.paa` and `P:\DZ\data\data\black_co.paa`). `winding_fixtures/make_fixtures.py` rewrites them with py3d 1.8.0 or newer and refuses to write unless the three in-game files come out byte for byte.

| File | How it was written | In game (2026-10-01) | Gate |
|---|---|---|---|
| `mirror_b.p3d` | `py3d.blender_to_dayz()`, Rule 12 | Solid, the F reads correctly | PASS |
| `mirror_a.p3d` | `transform(ROT_X_NEG90)`, every face reversed, every normal negated (the old determinant +1 recipe) | Solid, the F mirrored | PASS (a gate cannot see a mirror) |
| `mirror_c.p3d` | `transform(ROT_X_NEG90)` alone | Inside-out and mirrored | FAIL: reverse every face, then negate the pool |
| `mirror_b_normals_out.p3d` | `mirror_b` with the normal pool negated | Not taken into the game | FAIL: negate the pool, keep the faces |

`test_check_dayz_winding.py` next to the script holds the expected verdict lines for these and for about thirty variants built from them (one inverted box, an incoherent shell, open sheets, welded twins, proxies, a non-convex quad, zero normals, ODOL and truncated input).

Measured offline on 2026-10-02 on three builds of the LFInfectedBig character:

- The Rule 12 build passes: 48 closed shells negative; 99.8 % of its 131,278 corner normals with a clear sign agree, 99.5 % in the body, its lowest shell, with 219 against their face and 200 within 5 degrees of it. The open ribcage tubes, 63.5 % of the faces, are not scored.
- The two builds with outward normals fail on their normals: 0.2 % of their corners agree, every shell below 10 %.
- In game the same day: the Rule 12 build is solid and lit like vanilla. The builds with normals stored outward, which the gate passed before its rewrite, are lit inverted (base shading on a client without textures), and the shipped one is also mirrored. (claim id CLAIM-CHAR-NORMALS-INWARD-SKILL)
- The absolute check of dayz-p3d-audit agrees: the Rule 12 build 99.3 % and -0.109 on the body, the others 0.7 to 0.8 %. On the static fixture both gates pass the two solid variants and fail the inside-out one.

## History

- **2026-06-25.** First version, written after the first LFInfectedBig build rendered inside-out. It encoded that build's determinant +1 recipe: normals stored outward and `cross . normal < 0`.
- **2026-08-17 (review item SP-290).** Measured: exit 0 was not "safe to ship". The gate failed only on relative winding. It measured global inversion (it printed `normals_outward[info]=0.00` and a note that the normals look inward) but did not fail for it. Three fixtures made from one nine-LOD crate model showed it: intact, exit 0; winding inverted on 784 faces, exit 1; winding and stored normals both inverted (784 faces, 488 normals), exit 0 `PASS`. That third state is coherent inside and inside-out as a whole, the silent Blender Z-up to Y-up export (seen on a wall lamp and a wooden crate model). The third fixture inverted the stored normals to reach that state; it did not reproduce byte for byte an exporter that also mirrors coordinates. The review asked for three things: fail on that state; three exit codes instead of two, because an ODOL file raised a bare `AssertionError` and exited 1 like a defect; and fixtures kept next to the check.
- **2026-10-01.** A first fix failed any model whose normals did not point outward (`NORMALS_OUTWARD_MIN = 0.35`). It contradicted the MLOD convention measured since (shading normals stored inward: the engine verdict of 2026-09-07 behind the absolute check, and Rule 12 in game on 2026-10-01), and it failed every correct Rule 12 export. The gate exited 1 on all three MLODs of the Rule 12 in-game probe, including the one that renders solid and reads correctly (`cross.normal_positive=1.00`, `normals_outward=0.00`), with fix hints that would turn it inside-out.
- **2026-10-02.** Rewritten to the form above: direction from the signed volume of each closed shell, stored normals failed when they disagree with the winding, exit 2 for invalid input and ODOL. The both-inverted state now fails on its volume wherever its shells are closed (`mirror_c.p3d`: +0.1086). The fixtures next to the check are the Rule 12 probe's; the crate fixtures of the review were not carried over.
- **2026-10-03.** The fix for mixed shells changed. It used to read "negate the normal of each corner that points against its face"; a flat tetrahedron wound right, with one area-weighted normal per point, has 6 of its 12 corners against their faces, so the fix now reads shell by shell.
