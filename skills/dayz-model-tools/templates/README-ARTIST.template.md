# <Garment> worn models for fine-tuning

What this package holds, what is already fixed in it, and the fit work left for you: <areas still to fit, for example arms, legs, abdominal protector>. The garment already binds and moves with the player in DayZ <version>.

Fill in every `<...>` value before sending this file. The examples in brackets are for a suit of body armor; replace them with the garment's own.

## Contents

- `<garment>_m.fbx` and `<garment>_f.fbx`: the files to work on in Blender, Max or Maya, with the geometry, the UVs and the skin weights as vertex groups on an armature.
- `<garment>_co.png`: the diffuse texture the FBX files point to.
- `<garment>_m.p3d` and `<garment>_f.p3d`: the same models as MLOD, for anyone who prefers Object Builder.
- `model.cfg`: the file these models are binarized with.

## How the FBX is set up

- Axes are Blender's own, Z up. The character faces -Y (Blender's Front view) with its anatomical left at +X, the same frame as the official DayZ rig. Units are meters and the origin is at the character's feet.
- The armature (<N> bones) only carries the weights. Each bone sits at the middle of its region so the FBX keeps the vertex groups; it is not the game rig and is not for animating. The groups are what count: <group list, lowercase; for example leftarm, rightarm, leftforearm, rightforearm, leftupleg, rightupleg, neck, pelvis, spine, spine3>.
- Move, rotate or sculpt vertices to fit the plates to the body. Never rename a vertex group or empty one, because the model is rebuilt from those names. You may re-weight for better deformation (see "Optional improvement") as long as each vertex still sums to 1.0.
- Keep the topology (the same vertex count and order) and the model goes back into the mod as it is. If you retopologize, still send the FBX with its groups and we rebuild it.

## Already fixed, do not undo

- Orientation. The models sit in the DayZ clothing frame: in the `.p3d`, -Z is the front, +X the anatomical left, Y up and the origin at the feet; the FBX holds the same frame in Blender axes. Exporting again from an older source without turning it brings back a garment that faces backwards.
- Skeleton. `model.cfg` names the skeleton `DayzTemporarySkeleton`, 159 bones in the vanilla hierarchy, the name vanilla worn clothing is compiled with. Under the name `OFP2_ManSkeleton` the engine never binds the garment to the player, and it renders as a rigid block floating above them. Always binarize with the `model.cfg` in this package.
- Weights. Every vertex is weighted and each one sums to 1.0.

## What to fit

Fit the plates to the body in the DayZ A-pose:

- <Area 1, for example arms>: <what is off; for example: the pauldrons and forearm plates stand away from the arm and sag, because the DayZ bind pose holds the arms more level than this model>. For where clothing should sit, compare with the vanilla chainmail worn model, `dz\characters\tops\chainmail_m.p3d`.
- <Area 2, for example legs and abdominal protector>: <what is off; for example: small fit corrections>.

## Optional improvement

Each plate is skinned rigidly today: <percent> % of the vertices follow one bone, and the transition bones (shoulder, roll, extra, spine1, spine2) are unused. It works, but the joints move stiffly. Blending the weights at the joints over 2 to 4 bones, as vanilla clothing does, makes the deformation much better.

## Return workflow

Send back the changed FBX, or the `.blend`. We turn it into a `.p3d` with the same axis map that made this FBX (the map is its own inverse), rebuild the selections from the vertex group weights, and binarize with the included `model.cfg`. Do not mirror the model or flip its normals: the garment should look in game as it looks in Blender, text and logos included.
