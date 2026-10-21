# Physics pack

Tier 3 reference for how DayZ objects behave physically: mass, collision LODs, dropping, throwing and contact. Written for `dayz-physics-specialist`; any DayZ worker may load one file of it when a task needs it. Tier 1 and Tier 2 still apply on top.

Every game fact here cites the vanilla file on `P:\` it came from. A line marked **model knowledge** comes from the MLOD format or Object Builder, not from a vanilla text file, so check it on the mod's own MLOD model with `/dayz-p3d-audit`. Vanilla `.p3d` files under `P:\DZ\` are binarized ODOL and stay closed: never open, convert or audit them.

## Which file to open

| Question | File |
|---|---|
| How heavy is it, and which number does what (config `weight`, body mass, `itemBehaviour`, `physLayer`) | `mass-and-weight.md` |
| Which LOD stops players, items and bullets, and how to probe each one from script | `collision-lods.md` |
| Why an item floats, freezes or falls through the floor when spawned, dropped or thrown | `drop-and-throw.md` |
| Reacting when something hits something: `EOnContact`, impact sounds, players, vehicles, pushing | `contact.md` |

Related packs: `_shared/enscript/patterns/physics_items.md` (making a spawned item physics active), `dayz-p3d-audit/references/p3d-killers.md` (model faults that break collision with no error) and the LOD resolution table in `_shared/conventions/assets.md`.

## Symptom to cause

| Symptom | Likely cause | Read | Fix goes to |
|---|---|---|---|
| Item or crate falls through the floor | No Geometry LOD, wrong `Component01` name, open mesh, or no mass on the Geometry LOD | `collision-lods.md`, `mass-and-weight.md` | dayz-object-builder |
| Item hangs in the air after a script spawn | Spawned without physics, or the body is static | `drop-and-throw.md` | dayz-script-specialist |
| Placed object sinks into the ground or floats | `autocenter` set on the wrong kind of item | `collision-lods.md` | dayz-object-builder and dayz-config-specialist |
| Bullets pass through a wall or crate | No Fire Geometry LOD, or its faces have no penetration material | `collision-lods.md` | dayz-object-builder |
| Player walks through the object | Geometry LOD missing or broken | `collision-lods.md` | dayz-object-builder |
| Player can't throw the item | The item uses the heavy hand profile, the weapon is raised, or there is no free space in front | `drop-and-throw.md` | expected for heavy items; otherwise dayz-config-specialist (parent class) |
| Item lands with the wrong sound, or none | `soundImpactType` missing, or impact too slow | `contact.md` | dayz-config-specialist |
| Item is far too easy or too hard to push | Geometry mass far from what the item should weigh | `mass-and-weight.md` | dayz-object-builder |
