# Unconfirmed model faults

Which Binarize and proxy faults are reported by modders but not confirmed, what to do when an audit meets one, and a third party Object Builder replacement for Maya. None of the faults is checked on `P:\` or reproduced here. Treat them as warning signs in a model audit, name them as unconfirmed in the report, and never present them as settled behaviour.

| Fault | Status | Suspect it when |
|---|---|---|
| Binarize moves meshes tagged `personality` | Open, unresolved | Clothing or an accessory lines up in Object Builder and shifts after binarizing |
| Proxies of binarized models vanish inside an unbinarized parent | Open fault or engine limit | A mod model has missing parts and uses a binarized vanilla model as a proxy |

## Binarize moves meshes tagged personality

Reported on a bracelet in the glove slot:

- The mesh is attached to the glove slot and marked `personality` in the `.p3d`'s named selections.
- Unbinarized, in Object Builder and Buldozer, it looks right.
- After DayZ Tools binarize it, the mesh no longer lines up with the arm: it is moved or turned against its unbinarized position.
- The `model.cfg` extracted from the binarized `.p3d` matches the original, so the fault lies after `model.cfg`, in the binarizer itself.

Suspected causes: a regression in the DayZ 1.29 Tools binarizer, or bone weight or pivot data recomputed wrongly during binarizing.

When auditing a misaligned clothing or accessory mod:

1. Open the binarized `.p3d` through an outside ODOL to MLOD converter and compare the bone weights with the source. Agentic-Z ships no debinarizer.
2. Try packing with an older DayZ Tools build. The experimental patch of 14 August is the one reported to try first; that detail is uncertain.
3. Repack with Addon Builder (`/dayz-build-pbo`) if the mod was packed with another packer such as pboProject.

## Proxies of binarized models vanish

Reported on a car part armour system:

- The car door `.p3d` is binarized, as vanilla ships it.
- A custom armour `.p3d`, unbinarized, uses the binarized car door as a proxy.
- In game the proxy is missing: only the armour draws, and the door has no physics.

What did not fix it: a `proxy:` selection in the unbinarized model, or the door `.p3d` as a proxy placed by hand. What worked, with a cost: using the car door's attachment slot and declaring the armour as an attachment. The armour then carries none of the door's physics or collision; it behaves as a cosmetic attachment. How to bake a proxy into a new `.p3d` without an attachment slot is unknown.

The suspected cause is an engine limit on proxies that point at binarized models from an unbinarized parent, perhaps because the binarized child cannot rebuild its bounding and collision data inside that parent.

Every model vanilla ships is binarized: a scan of all 8,256 `.p3d` files under `P:\DZ\` finds the `ODOL` signature in each one (for example `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`). Any proxy that points at a vanilla model therefore points at a binarized one, so flag this fault whenever a mod with missing visual parts uses vanilla models as proxies.

## Object Builder replacement for Maya

An open source Object Builder replacement exists for Autodesk Maya 2027, with a PySide 6 interface. It is in alpha and may not handle every vanilla LOD case. Agentic-Z does not ship or drive it. It suits a modeler whose main tool is Maya and who wants to skip the Blender add-on and Object Builder round trip.

- Memory points are Maya Locators, converted to MLOD memory points on export; Maya has no native equivalent.
- Named selections map to bones through Maya groups, one group per selection.
- The `.p3d` export does not need Workbench.
