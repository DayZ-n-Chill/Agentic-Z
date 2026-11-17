# Visual winding when a generated mesh is written to an MLOD

Which coordinate map, face order and normals to use when an AI-generated mesh that was reworked in Blender is written to an MLOD `.p3d`, and how to read a winding census on the result. Everything here was measured by the source author, in game or offline, on the dates given; none of it can be checked against files on `P:\`, where the vanilla models are binarized (not yet checked on `P:\`). The labels `SP-071`, `Rule 12` and `LL-NNN` are the author's own references; Rule 12 is in the `dayz-model-pipeline` skill.

## The map to use

Every route of the `ai-3d-to-dayz` skill reaches the MLOD as geometry authored in Blender: the generator's mesh (GLB, OBJ or FBX) is imported, retopologized, unwrapped and baked there (pipeline steps 3 and 4). So emit it with the FBX and Blender bullet of `dayz-model-pipeline` Rule 12, whatever format the generator wrote. The mesh is Blender-authored by then, and the separate GLB/glTF case does not apply.

- Apply the det = -1 map `(x,y,z) -> (x,z,y)` to every point and normal of every LOD.
- Keep the faces in their original order. Do not reverse them.
- Negate the shading normals.
- With py3d 1.8.0 or later this is `py3d.blender_to_dayz(model)`, called once, before adding anything built directly in DayZ space (collision boxes made in code, for example), which skips the map.

Winding gates cannot see a mirror, so also check chirality on an asymmetric feature (Rule 12). An MLOD written by another exporter, such as the Arma 3 Object Builder add-on, gets the same checks, winding and normals with `/dayz-p3d-audit` included.

Measured on this skill's own route: LFInfectedBig, an AI-generated GLB that was retopologized and rigged in Blender, read correctly in game with this map, and was mirrored with the det = +1 recipe of reversed faces it first shipped with (the `dayz-characters` skill, `references/character-rigging.md` section 6, 2026-10-02).

## When reversing the visual faces is right

Reverse the vertex order of every visual face only for a source whose own lineage was measured to need it: an in-game A/B against the variant with all visual faces flipped, plus a chirality check. Proxy triangles are exempt, because their winding encodes the proxy frame.

The one calibration behind SP-071 does not qualify. The LFHeli OH-1 (2026-07-19) was an artist's Blender model exported as OBJ and mapped with the det = +1 rotation `x'=x, y'=z, z'=-y`, the map Rule 12 measured in game as a mirror. The reversal made it render solid, and nothing in that verdict checked chirality. Do not carry the reversal over to a vehicle or to a reconstructed source profile either: those keep their own measured lineage.

## Reading a winding census

A census taken before binarizing, of `dot(cross(v1-v0, v2-v0), mean_stored_normal)` with faces where `abs(dot) < 1e-9` left out, tells whether the stored normals agree with the winding. It does not tell which side renders.

The OH-1 thresholds (at least 95% negative reads `SOLID`, mostly positive reads `INVERTED`) belong to that pipeline, which stored the normals outward against an inward winding. A Rule 12 export stores them inward, like the winding.

Measured offline on 2026-10-03, on the MLODs of the Rule 12 in-game test, rebuilt byte for byte by `scripts/tools/py3d/tests/test_s7_blender_to_dayz.py`:

| Export | Census | In game |
|---|---|---|
| Rule 12 (det = -1 map, face order kept, normals negated) | 0% negative, `INVERTED` by the OH-1 thresholds | Rendered solid and read correctly |
| The same export with every face reversed (winding outward) | 100% negative, `SOLID` | Inside out |
| SP-071's own recipe: det = +1 map, faces reversed, normals outward | 100% negative, `SOLID` | A mirror |

Normals stored outward render solid but are lit inverted (`character-rigging.md` section 6).

Read a Rule 12 export with `/dayz-p3d-audit` instead:

- A healthy single-sided MLOD reads about 100% agreement ("Absolute winding check", rule 1).
- The direction comes from the signed volume by winding of each closed shell, even at 100% agreement, never from the sum over the LOD: one shell reversed with its normals negated keeps 100% agreement and a negative sum (Check A in that skill's `references/winding-diagnostics.md`).
- Open sheets and double-sided parts take the visibility checks of "From Check B to fix".
- Isolate a mixed result part by part before any bulk fix (rule 2).

## A profile signal, not a universal gate

Do not compare census ratios across ODOL, MLOD produced from ODOL by an external converter (none is shipped in this repo), raw MLOD from a modeling tool, or vanilla references: the convention for stored normals differs by origin. Enforce a threshold only after an in-game A/B has calibrated that exact source pipeline.

The final verdict stays the in-game A/B between the candidate and a variant with all visual faces flipped. That A/B cannot see a mirror either, since both variants share the map: check chirality too.

## History

Until 2026-10-03 this guidance said the opposite for raw imports: for a Blender, OBJ, glTF or FBX import whose measured axis transform preserves winding, reverse the vertex order of every visual face when emitting the authoring MLOD, keep that step in the generic profile handed to `dayz-model-pipeline`, and read the census as at least 95% negative `SOLID`, mostly positive `INVERTED`, anything between as mixed winding per piece. It was aligned with Rule 12 after Rule 12 was measured in game on 2026-10-01.
