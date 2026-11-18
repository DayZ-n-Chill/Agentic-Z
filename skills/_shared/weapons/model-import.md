# Importing a weapon mesh

How a weapon mesh made in Blender goes into a DayZ `.p3d` the right way round, and which build to test it with. The `model` path rule is in `weapon-config.md`, "Model path"; mesh assembly, LODs and the general axis and winding rules belong to `dayz-object-builder` (`skills/_shared/models/axes-and-winding.md`); how to measure winding is in `skills/dayz-p3d-audit/references/winding-methodology.md`.

The numbers below were measured in game on one custom 7.62x39 rifle built on a third-party weapon pack, so they are not on `P:\`; a line says so when a second weapon confirmed it. The reference is the vanilla AKM, `model="\dz\weapons\firearms\AKM\AKM.p3d"` (`P:\DZ\weapons\firearms\akm\config.cpp:196`). Its model is binarized on `P:\`, so its numbers come from a readable copy.

## The import transform

- The rifle's Blender frame was long along X (muzzle toward -X), Z up and Y sideways (right is +Y). A pure axis swap, (x, y, z) to (x, z, y), turns Blender's Z up into DayZ's Y up. Its determinant is -1, so it is a reflection.
- Treat normals as pseudovectors under that swap: transform them by the negated swap, and keep the face order (no reversal).
- Binarize reverses the winding of every face and passes normals through unchanged (**tool knowledge**), so all of this holds only for the binarized model.
- The target is the binarized AKM's pattern: about 70% of faces pointing outward, and a dot product of about -0.98 between the stored normal and the geometric normal.
- Pass band: at least 60% of faces outward and a dot product of -0.85 or lower. The rifle's first build that rendered measured 63.2% and -0.88.

Derive the swap again for every weapon from its own Blender file; never copy it. A 9x19 SMG was long along Y with the muzzle toward -Y, so its swap had to be derived again and checked against the same pass band; the rifle's swap would have flipped it the wrong way.

When a change to winding or normals seems to do nothing in game, first check that the game loads the model you measured (`weapon-config.md`, "Model path"). Then measure again against the pass band instead of trying more variants.

## Test the binarized build

- Test the binarized PBO. A build that serves the unbinarized model is not the model the winding rule describes.
- Some third-party weapon packs use script without braces (for example `override typename GetInputType() return X;`). The Diag compiler stops on it while the retail game only warns, so the Diag server stops before it binds. A retail client started with `-filePatching` then crashed on connect with a null read in `CDPInitServer` and `CDPCreateClient`.
- For a mod on such a pack, run the retail server and client without `-filePatching`, with the pack and its dependencies before your mod in `-mod=`. The PBO already holds your change, so file patching is not needed. `/dayz-launch-test` starts the Diag build (Tier 2, `dayz-conventions.md`), so start these two by hand.

## Order of work

1. Assemble the `.p3d` with the swap derived for this weapon and check it against the pass band above.
2. Point `model` at the file's real path in the PBO (`weapon-config.md`, "Model path").
3. Build with `/dayz-build-pbo <ModName>`, which binarizes and empties its temp folder first.
4. Test that build, with the retail game when the weapon pack needs it.
