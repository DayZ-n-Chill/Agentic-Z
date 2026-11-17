# Worn clothing binds through the skeleton name `DayzTemporarySkeleton`

Covers the skeleton name a worn clothing model must compile with, the frame a worn mesh has to be built in, the handedness of the usual fix, and the ladder of cheap tests that isolates a worn model that will not follow the body.

How to read the marks: the `P:\` checks were run on the vanilla binarized models (a text search inside the ODOL files; binary files have no line numbers). "ArmorHneck" marks results measured in game by that clothing project on 2026-08-03 and 2026-08-04, which cannot be checked on `P:\`.

## The fact

A worn `.p3d` (the male or female worn model of a clothing item) whose `model.cfg` declares `skeletonName = "OFP2_ManSkeleton"` renders as a rigid block anchored above the player: floating about 1 m up, rotated, not animating. The engine treats it as a model with its own skeleton and never binds it to the wearer (ArmorHneck, in game).

Vanilla worn clothing compiles with the skeleton named `DayzTemporarySkeleton`. The source project read it from the skeleton name inside the binarized `armbend_dynamic_m` and `chainmail_m` models and reports the same 159 bones, hierarchy and order as the community `OFP2_ManSkeleton` definition; only the name differs, a placeholder the engine replaces with the wearer's skeleton.

The fix: rename the `CfgSkeletons` class and every `skeletonName =` in the clothing `model.cfg` to `DayzTemporarySkeleton`, then binarize again. The community 114-bone `OFP2_ManSkeleton` template fails twice for clothing: the wrong bone count and the wrong name.

What `P:\` shows (text search inside the binarized models):

- `P:\DZ\characters\tops\hoodie_m.p3d`, `P:\DZ\characters\tops\chainmail_m.p3d` and `P:\DZ\characters\tops\armbend_dynamic_m.p3d` each contain `DayzTemporarySkeleton` and do not contain `ofp2_manskeleton`.
- So do the bodies: the infected body `P:\DZ\characters\zombies\hermit_above0.p3d` and the survivor body parts model `P:\DZ\characters\bodies\bodyparts_above0.p3d`. Of the 63 models under `P:\DZ\characters\zombies\`, 62 contain `DayzTemporarySkeleton`; the one without is a static prop.
- Of the 897 models under `P:\DZ\characters\`, 584 contain `DayzTemporarySkeleton` and only 4 contain `ofp2_manskeleton`: `P:\DZ\characters\pants\jeans_m_above0.p3d`, `P:\DZ\characters\tops\tshirt_m_above0.p3d` and the two `shirt_*_new_anim_system.p3d` models in `tops`. No vanilla `config.cpp` under `P:\DZ\characters\` names those four.

So the name vanilla ships in character and clothing models is `DayzTemporarySkeleton`. The LFInfectedBig infected body was built with `OFP2_ManSkeleton` as its `model.cfg` skeleton name and did animate in game as an infected (`references/case-log.md`), so a body that is its own entity worked under that name; a worn item did not. When in doubt, use the name vanilla uses.

## The frame a worn mesh must be built in

Measured by ArmorHneck on the debinarized `chainmail_m` and `hoodie_m`, by anatomical components. A histogram of all Z values is too coarse and misses a 180 degree flip.

- -Z is the chest, the front. The hoodie's front drawstrings sit at Z -0.14 to -0.07; the chainmail's pelvis and spine centroids at Z -0.04 and -0.08.
- +X is the anatomical left, +Y is up, and the origin is at the feet.

A mesh built facing +Z breaks into rigid "exploded" pieces when worn, because each plate is transformed by its bone from a flipped frame. The project's fix was a rotation of 180 degrees about Y (determinant +1, so the winding is left alone) plus a swap of every `left*` and `right*` selection pair in every LOD.

## Handedness of that fix

Added 2026-10-01. Leaving the winding alone is right: a rotation of 180 degrees about Y is a rotation. But the swap it needs shows that the received mesh was a mirror: it faced +Z with `left*` on +X.

ArmorHneck's received `.p3d` was the determinant +1 map `(x, z, -y)` of the artist's Blender coordinates, and the shipped one is `(-x, z, y)` of them. Rotation plus swap fixes the binding and keeps the mirror. Symmetric plates hide it; text, logos, buckles and one-sided straps come out reversed.

- With the Blender source: export again with `(x, z, y)`, Rule 12 of the dayz-model-pipeline skill, and no swap.
- With only the `.p3d`, the reflection to apply depends on its state. The received `(x, z, -y)` model takes `z -> -z`. The shipped `(-x, z, y)` one takes `x -> -x` with the left and right swap undone, as "undo the reflection" in `references/canonical-bind.md` (`z -> -z` on it would face +Z again). Either one moves every point, memory points included, reverses every face and reflects the normals the same way.
- Decide on an asymmetric feature in game. The chiral check for clothing is in the dayz-clothing skill (its canonical worn frame section).

## Diagnosis ladder

Each step is cheap in game, and together they isolated the fault in about six cycles on a third-party model.

1. **Cross-matrix bisection.** Build `{armband class + vanilla worn p3d}` against `{vanilla top class + custom p3d}`. One config-only rebuild separates a config fault from a model fault.
2. **Compare the skeleton name inside the binarized model**, custom against vanilla worn. A compliant clothing ODOL says `DayzTemporarySkeleton`. (The text search above is enough to read it.)
3. **Structure parity checklist**, custom against vanilla worn:
   - skeleton of 159 bones;
   - per-vertex weight sums (vanilla stores raw bytes that sum to 255);
   - the sub-skeleton palette;
   - sections: tops use `camomale` alone, and only armbands carry the `camomale_big_a`, `camomale_big_b`, `camomale_small_a` and `camomale_small_b` complexion variants (the same text search finds exactly these names in `P:\DZ\characters\tops\hoodie_m.p3d` and `P:\DZ\characters\tops\armbend_dynamic_m.p3d`);
   - an empty Geometry LOD with `autocenter=0` is the vanilla worn pattern.
4. **The registration gate is a live spawn.** An `unknown_type` result means the config did not load. ArmorHneck also hit this: a `config.bin` made with CfgConvert did not register at all. Pack clothing PBOs with `config.cpp` as text.

The pack rules for worn models, with the `model.cfg` template, are in `skills/_shared/wearables/references/worn-models.md`. Clothing classes, slots and proxies are in the rest of the wearables pack (`skills/_shared/wearables/references/models-and-proxies.md`) and the dayz-clothing skill.
