# Physics pack

Tier 3 reference for how DayZ objects behave physically: mass, collision LODs, dropping, throwing and contact, plus rigid bodies and joints from script, interaction layers and raycasts, surfaces, the damage that follows a contact, the player controller, ragdoll and fall damage, what replicates, scripted triggers and water queries. Written for `dayz-physics-specialist`; any DayZ worker may load one file of it when a task needs it. Tier 1 and Tier 2 still apply on top.

Every game fact here cites the vanilla file on `P:\` it came from. A line marked **model knowledge** comes from the MLOD format or Object Builder, not from a vanilla text file, so check it on the mod's own MLOD model with `/dayz-p3d-audit`. A line marked **measured in game** was seen on a running game and can't be checked on `P:\`; confirm it in game before a design depends on it. Vanilla `.p3d` files under `P:\DZ\` are binarized ODOL and stay closed: never open, convert or audit them.

## Which file to open

| Question | File |
|---|---|
| How heavy is it, and which number does what (config `weight`, body mass, `itemBehaviour`, `physLayer`) | `mass-and-weight.md` |
| Which LOD stops players, items and bullets, and how to probe each one from script | `collision-lods.md` |
| Why an item floats, freezes or falls through the floor when spawned, dropped or thrown | `drop-and-throw.md` |
| Reacting when something hits something: `EOnContact`, impact sounds, players, vehicles, pushing | `contact.md` |
| What happens after a contact deals damage: `ProcessDirectDamage`, the `EEHitBy` chain, damage zones, bleeding, shock, the hit animation | `damage-pipeline.md` |
| Creating, waking, moving and removing a physics body from script (`dBody` calls), the world's gravity and time step, friction and bounce, a script body of your own, the calls that do not exist | `rigid-body-api.md` |
| Tying two bodies together: hinge, slider, ball socket, cone twist, 6DOF and their limits | `joints.md` |
| What script can read about a surface (`SurfaceInfo`, terrain surface queries) and what it cannot | `surfaces.md` |
| Interaction layers, the three ways to switch a collision off, the two families of ray and overlap tests, why the action cursor ignores a physics body | `layers-and-raycasts.md` |
| The player's character controller, riding a moving platform, lifting or walking the player from script | `player-controller.md` |
| The ragdoll calls, a ragdoll on a living player, waking from unconsciousness, the fall damage curve (1.30) | `ragdoll-and-fall-damage.md` |
| What the engine sends to clients about a moving object, which machine simulates it, and what physics work can leave the server | `network-and-authority.md` |
| Trigger volumes from script: `ScriptedEntity` shapes, who is told about entry and exit, the `TriggerEvents` hooks, and the `Trigger` class that calls them | `scripted-triggers.md` |
| What the water queries return over river pieces, ponds and a roadway water face of your own | `water-queries.md` |

Related packs: `skills/_shared/wearables/references/ragdoll.md` (the `.ragdoll` file format and how a survivor binds it), `_shared/vehicles/` (the vehicle script API and vehicle networking), `_shared/enscript/patterns/physics_items.md` (making a spawned item physics active), `dayz-p3d-audit/references/p3d-killers.md` (model faults that break collision with no error) and the LOD resolution table in `_shared/conventions/assets.md`.

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
| Action or cursor does not appear on the object | The action cursor reads View Geometry, not the physics body | `collision-lods.md`, `layers-and-raycasts.md` | dayz-object-builder |
| Player walks through a body created on the server | The body exists only on the server; the player's controller is simulated on the client | `player-controller.md`, `network-and-authority.md` | dayz-script-specialist |
| Rolling or thrown object freezes after a few seconds | The drop physics lifetime ended, or the body went to sleep | `drop-and-throw.md`, `rigid-body-api.md` | dayz-script-specialist |
| Object should hurt players on contact but does nothing | A player's `EOnContact` reacts only to a `Transport` | `contact.md` | dayz-script-specialist |
| Custom unconscious wake buries the player under the terrain | The wake skips vanilla's 2 s and `PhysicsIsFalling` guards | `ragdoll-and-fall-damage.md` | dayz-script-specialist |
| A trigger's enter, stay or leave hooks never run | The class extends `TriggerEvents` or `ScriptedEntity` instead of `Trigger`, or its size was set before `EOnInit` reset it | `scripted-triggers.md` | dayz-script-specialist |
