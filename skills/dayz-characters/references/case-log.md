# Case log

Covers the real character imports this skill's rules were learned on, one entry per import, session by session, so a worker can see which rule came from which failure. Append one entry per real import.

How to read the marks: everything here was measured on a test build, in Blender or in game, on the date given. None of it can be checked on `P:\`.

## The giant infected build: a giant infected with a see-through torso hole (2026-06-23 onward)

The first character imported. An infected at about 1.2 times, with a chest hole one can see through (ribs and spine inside), as a reskin of `ZombieMaleBase`.

**Mesh.** Generated: Rodin v2.5 multi-view with its `TAPose` option, which gets an A-pose out of references with the arms down. A scripted ribcage cavity was added, then a 14,000-face manifold retopology with the hole open. The 1,000,000-face high-poly was kept for the bake. Multi-view input and an A-pose or T-pose help the rig later.

**Rig (2026-06-24).** Automatic weights from the Bohemia DayZ-Misc rig FBX. The armature scale trap cost one failed attempt (all weights on `Pelvis`) before it was caught. The arms were 28 and 34 degrees narrower than canonical and were conformed by a weight-masked rotation. Cleanup to at most 4 influences and no vertex without a weight. The Blender pose test passed (6,961 of 7,000 sampled vertices move, smoothly, the cavity follows the torso), which later turned out to prove little.

**UV and bake (2026-06-25).** Smart UV plus a rotating pack: uniform density, 96.8 % of the bounding box filled, triangulated at 14,000 faces. The normal map was baked from the 1,000,000-face high onto a proxy in the pose from before the conform, because the conform had opened the arms about 8 cm and low and high no longer matched. The rainbow noise, black blotches and dark AO seen on the way all traced to four causes: alignment, a normal recalculation that flipped the generated high-poly's shells, misses cleared to black, and the high-poly occluding the AO. All are fixed in `references/character-uv-bake.md`. The ribcage was decimated from 95,000 to 15,800 faces and weighted by height along the spine, because bone-heat failed on the thin geometry; its pose test measured a dot product of 0.823. The armature ships with `pose_position` at rest, which is the bind; set `'POSE'` for a pose test.

**Export, texture, LODs, config and PBO (2026-06-25).** Export by direct py3d write: fractional per-vertex bone weight selections in lowercase, checked against a debinarized vanilla infected for selection names, the Y-up frame and the character LOD anatomy. The coordinate map used then was `(x, z, -y)`, determinant +1, derived from the armature matrix; that derivation missed the handedness change, and the right map is `(x, z, y)` (`references/character-rigging.md` section 6, corrected 2026-10-01). The colour map was baked high to proxy onto the new UV. The material was a Super shader `.rvmat`, with its `Stage4` ambient shadow stage set to `uvSource="tex"`. Six LODs: a Geometry hull with `class = "man"` (not skinned); Fire Geometry skinned to the bones with `dmgzone_spine` and the vanilla `meatbones.rvmat`; View Geometry; LandContact; Memory with points from the bone positions. The `model.cfg` held the full character skeleton hierarchy, self-contained. Binarize, CfgConvert and AddonBuilder gave a 6.4 MB PBO, all verified offline.

**Inside-out winding fix (2026-06-25).** The first in-game build rendered inside-out, with textures on the interior. The fix at the time was to reverse every visual face, and the first version of `check_dayz_winding.py` was written and wired in before every pack so this never costs an in-game cycle again. Correction of 2026-10-03: the inside-out render came from the determinant +1 map, not from the source mesh's winding. From Blender, any determinant +1 map mirrors the mesh, and reversing every visual face then hides the mirror. In game on 2026-10-02 the shipped build (determinant +1 with reversed faces) read its chiral marker mirrored and was lit inverted; the Rule 12 build (`(x, z, y)`, faces in their order, normals negated) read it correctly and was lit like a vanilla infected. The gate, rewritten for Rule 12 the same day, passes the Rule 12 build and fails the shipped one on its normals.

**Scale and orientation fixed, proportions left (in game, 2026-06-25).** A deep offline investigation diagnosed the first in-game breakage.

- The "camo" texture was a corrupt high to low bake: the noise was in the colour texture, not the normal map, and the body UV was clean. It was replaced with a clean procedural flesh texture.
- The deformation had two systemic causes, both confirmed in game. Scale: the 2.277 m (1.27 times) mesh fought the canonical bind of about 1.8 m; fixed by a uniform rescale by 0.7901. Orientation: the `(x, z, -y)` map was 180 degrees about the vertical, so the character faced and walked backward; fixed then with `(-x, z, y)`, which is also determinant +1, so it fixed the facing and kept the mirror found later.
- Both landed: it faces forward, is vanilla sized, and the camo is gone. py3d carried the weights fine; Object Builder was not needed.
- A later texture fault on the same build (green, grey and brown patches that survived six replacements of the colour texture and the removal of the normal map) was fixed in the `.rvmat`, not in the texture. See the triage table in `SKILL.md` for what that does and does not prove.

**New rig attempt and the false gate wall (2026-06-25; deformation still broken in game).** An attempt to fix the proportion deformation offline.

- Diagnosis of the shipped deformation: asymmetric automatic weights (`LeftUpLeg` 37 vertices against `RightUpLeg` 166), 19 % of weight across the midline, and the cross-side cleanup had amplified it to 21 to 34 times stretch (it keeps the dominant side per vertex; on bled, asymmetric weights it reassigns whole regions to the opposite limb).
- The bind was replaced by **envelope weighting**: distance to the bone segment, a fade by side, and a column from pelvis to crotch. It is robust for a see-through cavity; a data transfer from a solid `Male_body` weighted the tunnel interior wrong and gave 100 times spikes.
- A thin-plate-spline proportion conform to bone midpoint targets flattened the mesh to 2D, because the targets were nearly coplanar in depth. It was fixed with a conform in X and Z only that preserves Y.
- The Blender edge stretch fell from 34 times to 6 times over three rebuilds, and all three in-game builds deformed the same, at idle and when animating. That is the false gate in `references/canonical-bind.md`. The root cause was then narrowed to a bind or skeleton mismatch (`model.cfg` skeleton or authored rest pose not equal to vanilla).
- Still good in game after this: scale, orientation, winding, 3D volume. Reusable: envelope weighting and the conform diagnostics.

**Mirror found (2026-06-25).** With the `model.cfg` skeleton matched to a debinarized vanilla infected, the legs walked and the arms still flung: the mesh was mirrored against the skeleton. Swapping the left and right selection names made it animate. See "The mesh can be left and right mirrored" in `references/canonical-bind.md`.

**Decision taken with the user.** Stop iterating against the rig FBX. Debinarize a vanilla infected, copy its `model.cfg` skeleton and match its bind and selection structure, author the custom mesh against that, and gate only in game or in Buldozer.

**Proportion diagnosis and the vanilla body route (2026-06-28).** All 42 weighted bones were inside the infected's 95-bone bind, so the remaining deformation was proportion (bone heads 0.10 to 0.22 m off the anatomy). Conform and new weights cut it by 30 to 45 % and no further. The way out is to rebuild on the `Male_body` of the rig FBX and graft the distinctive parts (`references/canonical-bind.md`, "When conform and new weights stall").

**Rule 12 check on the character (in game, 2026-10-02).** Three builds from one dump with an "F" marker on the chest; the Rule 12 build is solid, reads correctly, is lit like vanilla, walks and attacks with its limbs in place. Full result in `references/character-rigging.md` section 6.

## The worn armour build: worn armour that floated above the player (2026-08-03)

A worn armour model that rendered as a rigid block above the player. About six in-game cycles and research on debinarized vanilla clothing isolated the cause: the skeleton name. The result, the worn frame and the diagnosis ladder are in `references/worn-clothing-skeleton.md`.
