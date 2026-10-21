# Model and LOD pack

Reference for `dayz-object-builder`: what a DayZ `.p3d` needs inside, LOD by LOD, and the model side of an animated door. Open only the file the task needs. Tier 2 still applies on top: the LOD resolution table lives in `_shared/conventions/assets.md` and is not repeated here.

Vanilla models under `P:\DZ\` are binarized ODOL, which Object Builder and `/dayz-p3d-audit` can't open. The vanilla facts in this pack come from reading the plain text that ODOL files still carry: the LOD resolution list in the file header, and the names of selections, memory points, named properties and proxies. Each fact names the model or the scan it came from. Where a rule is Object Builder or Binarize format knowledge that no vanilla file on `P:\` shows, the file says so.

| Question | Open |
|---|---|
| Which LODs does a model need, in what order, and how are the visual LODs numbered? What are the rules for Geometry, Fire Geometry and View Geometry? | `lods.md` |
| Which memory points does vanilla script look for, and how are axes built? | `memory-points.md` |
| Which named properties does vanilla set, and where does mass go? | `named-properties.md` |
| How is a proxy named and placed? | `proxies.md` |
| What does a door need in the model, and who writes the rest? | `doors.md` |

## Other packs this one leans on

| Topic | Pack |
|---|---|
| Model faults that break a `.p3d` with no engine error | `dayz-p3d-audit/references/p3d-killers.md` |
| Collision faults and probing a LOD from script | `_shared/physics/collision-lods.md` |
| Bones and the `Animations` block in `model.cfg` | `_shared/animation/model-cfg-animations.md` |
| Weapon memory points and selections | `_shared/weapons/model-selections.md` |
| Clothing models and their proxies | `_shared/wearables/references/models-and-proxies.md` |

## After every model change

The user makes the edits in Object Builder and saves the MLOD file. Then run `/dayz-p3d-audit` on that file, with `--model-cfg` and `--config` when the model has them, and read the findings against `dayz-p3d-audit/references/p3d-killers.md`. Fix every CRITICAL finding before the work goes back to the art lead.
