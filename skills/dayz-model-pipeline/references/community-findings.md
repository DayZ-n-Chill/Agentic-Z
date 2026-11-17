# Community findings: model pipeline

Three reports from the DayZ Modders Discord, read through AnswerOverflow on 2026-05-17. They are community reports of medium confidence, not checked on `P:\` and not reproduced here. Use them as red flags during a model audit and say so in the report; do not present them as settled behavior.

| Finding | Status | Use it when |
|---|---|---|
| MDL-1: Binarize misaligns meshes tagged `personality` | Open bug, unresolved | Clothing or an accessory lines up in Object Builder and shifts after binarizing |
| MDL-2: Nested proxies on binarized models can disappear | Open bug or engine limit | A mod model has missing parts and uses a binarized vanilla model as a proxy |
| MDL-3: Maya Object Builder alternative | Community tool, alpha | The user models in Maya and wants to skip Object Builder |

---

## MDL-1. Binarize misaligns p3d meshes tagged as `personality`

**Open bug, community reported, unresolved.**

Symptom (reported by Zen, a bracelet in the glove slot):

- The mesh is attached to the glove slot and marked as `personality` in the p3d's named selections.
- It looks correct unbinarized (in Object Builder and Buldozer).
- After DayZ Tools binarize the mesh no longer lines up with the arm: it is translated or rotated relative to its unbinarized position.
- The `model.cfg` extracted from the binarized p3d matches the original, so the fault is downstream of `model.cfg`, in the binarizer itself.

Likely candidates:

- A regression in the 1.29 DayZ Tools binarizer (the same mining run recorded a separate finding about Mikero's tools for the PBO build side).
- Bone weight or pivot data recomputed wrongly during binarization.

**What to do when auditing a misaligned clothing or accessory mod:**

1. Open the binarized `.p3d` through an external ODOL to MLOD converter and compare bone weights against the source. Agentic-Z ships no debinarizer.
2. Try packing with an older DayZ Tools build. The community baseline named in the thread was the 14 August experimental patch; that detail is low confidence.
3. Repack with Addon Builder (`/dayz-build-pbo`) rather than Mikero's tools.

Source: Zen, https://www.answeroverflow.com/m/1498490570996322315

---

## MDL-2. Nested proxies on binarized models can disappear in game

**Open bug or engine limitation, community reported.**

KOPYkAT's case, a modded car part armor system:

- The car door `.p3d` is binarized (shipped by vanilla).
- A custom armor `.p3d` (unbinarized) declares the binarized car door as a proxy.
- In game the proxy disappears: only the armor renders, and the door has no physics.

Workarounds tried that did not fix it:

- Using a `proxy:` declaration in the unbinarized model.
- Attaching the door `.p3d` as a proxy with manual placement.

Workaround that did work, with caveats:

- Use the car door's attachment slot system and declare the armor as an attachment.
- This does not carry over the physics or collision of the original door; the armor behaves as a cosmetic attachment.

**Open question** in the thread: how to bake a proxy into a new `.p3d` without an attachment slot. No resolution.

**Hypothesis:** the engine restricts nested proxies that reference binarized roots, likely because the binarized child cannot rebuild its bounding and collision data when wrapped in an unbinarized parent.

**What to do when auditing:** if a mod has missing visual parts and uses proxies on binarized vanilla models, flag this issue. Every model vanilla ships is binarized: a scan of all 8,256 `.p3d` files under `P:\DZ\` found the `ODOL` signature in each one (for example `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`), so any proxy that points at a vanilla model points at a binarized one.

Sources:

- KOPYkAT, https://www.answeroverflow.com/m/1502157615390658560
- KOPYkAT (earlier question), https://www.answeroverflow.com/m/1498549372726677646

---

## MDL-3. Maya Object Builder alternative (community plugin)

**Community tool for Maya 2027.**

targaryen built an Object Builder replacement for Autodesk Maya 2027, open sourced at https://github.com/SXDIST/Maya-ObjectBuilder, with a PySide 6 interface. It is useful for modelers who already work in Maya and want to skip the Object Builder round trip.

Key design choices, taken from targaryen's notes:

- **Memory points** are Maya Locators, converted to MLOD Memory points on export. Maya has no native equivalent of Object Builder memory points.
- **Named selection to bone assignment** goes through Maya groups, one group per selection.
- **No Workbench dependency** for the p3d export step.

Status as of 2026-05: alpha, with bugs being fixed. It may not handle every vanilla LOD edge case yet.

Useful when:

- The user's main 3D software is Maya (for example modelers coming from the game industry).
- The user wants to avoid the Blender add-on and Object Builder round trip.

Source: targaryen, https://www.answeroverflow.com/m/1502200911387431075

---

## About the mining run

- Server: DayZ Modders (id 452035973786632194), 14,498 members at the time.
- The two open bug findings (MDL-1, MDL-2) are red flags during a p3d audit: if a user reports misalignment after binarize, or missing proxies on binarized models, point them at these threads.
- One low confidence finding from the same run (DayZ Tools build stability: 14 August against 31 October against 1 December) was left out on the owner's instruction to keep only high and medium confidence findings.
