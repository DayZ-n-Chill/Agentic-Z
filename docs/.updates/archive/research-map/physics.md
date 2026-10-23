# Research map: physics specialist

Private research map. Anchors point into vanilla data on `P:\`. Items marked **knowledge** are not verifiable from vanilla files on `P:\`.

| # | Topic | What the specialist needs to know | Verify at |
|---|---|---|---|
| 1 | Rigid body API | `dBodyCreateDynamicEx`, `dBodyIsDynamic`, `dBodyActive`, gravity, damping. | `P:\scripts\1_core\proto\enphysics.c:48`, `:51`, `:64`, `:66`, `:69`, `:70` |
| 2 | Forces and impulses | `dBodyApplyImpulse`, `dBodyApplyImpulseAt`, `dBodyApplyForce`. | `P:\scripts\1_core\proto\enphysics.c:136`, `:141`, `:146` |
| 3 | Mass | `dBodyGetMass`, `dBodySetMass`. | `P:\scripts\1_core\proto\enphysics.c:122`, `:123`; `P:\scripts\2_gamelib\entities\scriptmodel.c:48` |
| 4 | Physics geometry | `PhysicsGeomDef`, static physics creation. | `P:\scripts\1_core\physics\physics.c:176`, `:182`, `:195` |
| 5 | Velocity | `GetVelocity`/`SetVelocity`. | `P:\scripts\1_core\physics\physics.c:86`, `:88` |
| 6 | Dynamic physics on objects | `CreateDynamicPhysics`, `SetDynamicPhysicsLifeTime` (items dropped or knocked). | `P:\scripts\3_game\entities\object.c:456`, `:458`; `P:\scripts\4_world\entities\itembase.c:4532` |
| 7 | Throwing | `ThrowPhysically`; player throwing implementation. | `P:\scripts\3_game\entities\inventoryitem.c:26`; `P:\scripts\3_game\systems\inventory\hand_actions.c:81`; `P:\scripts\4_world\entities\dayzplayerimplementthrowing.c` |
| 8 | Contact events | `EOnContact` with `Contact` data. | `P:\scripts\1_core\proto\enentity.c:213`; `P:\scripts\1_core\physics\contact.c:9`; `P:\scripts\3_game\entities\dayzanimal.c:942` |
| 9 | Interaction layers | `PhxInteractionLayers` masks for raycasts and bodies. | `P:\scripts\3_game\global\dayzphysics.c:1` |
| 10 | Raycasts | `DayZPhysics.RaycastRV`, `RaycastRVProxy` params and results, `RayCastBullet`. | `P:\scripts\3_game\global\dayzphysics.c:47`, `:96`, `:123`, `:211`; usage `P:\scripts\4_world\classes\hologram.c:683` |
| 11 | Bounds | `GetBounds` and collision box. | `P:\scripts\1_core\proto\enentity.c:595` |
| 12 | Placement and clipping | `Hologram` checks collisions, ground, slope; cfggameplay toggles to disable checks. | `P:\scripts\4_world\classes\hologram.c:1`; `P:\scripts\3_game\cfggameplaydatajson.c:242`, `:243`, `:246` |
| 13 | Surfaces | `CfgSurfaces` (liquid, sound environment, friction); `SurfaceInfo`, `SurfaceProperties`, `SurfaceGetType3D`, `SurfaceUnderObject`. | `P:\DZ\surfaces\config.cpp:613`, `:622`, `:625`; `P:\scripts\3_game\surfaceinfo.c:8`; `P:\scripts\1_core\physics\surfaceproperties.c:10`; `P:\scripts\3_game\ammoeffects.c:50`; `P:\scripts\3_game\entities\inventoryitem.c:180` |
| 14 | Hit info | Surface and normal from a projectile hit. | `P:\scripts\3_game\hitinfo.c:7`; `P:\scripts\3_game\dayzgame.c:3606` |
| 15 | Spawn flags affecting physics | `ECE_CREATEPHYSICS`, `ECE_KEEPHEIGHT`, `ECE_TRACE`, `ECE_OBJECT_SWAP`. | `P:\scripts\3_game\ce\centraleconomy.c:7`-`39` |
| 16 | Place on surface | `PlaceOnSurface`, `SetTakeable`. | `P:\scripts\3_game\dayzgame.c:3670`; `P:\scripts\3_game\effects\destructioneffects\destructioneffectbase.c:62` |
| 17 | Vehicle physics | Native simulation module (engine, gearbox, axles, suspension, wheels). See vehicles map. | `P:\DZ\vehicles\wheeled\config.cpp:5236`; `P:\scripts\3_game\vehicles\car.c:272`-`348` |
| 18 | Vehicle obstacle shapes | `ObstacleGenerator`. | `P:\DZ\vehicles\wheeled\config.cpp:6057` |
| 19 | Fall damage | Velocity-driven fall damage. | `P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:18` |
| 20 | Damage system | `DamageSystem` statics, close-combat damage, zone map. | `P:\scripts\3_game\damagesystem.c:20`, `:22`, `:141` |
| 21 | Projectile ballistics | `typicalSpeed`, `DamageApplied` in `CfgAmmo`. | `P:\DZ\weapons\projectiles\config.cpp:1957`, `:1965` |
| 22 | Explosions | `Explode` and explosive bases. | `P:\scripts\3_game\entities\object.c:144`; `P:\scripts\4_world\entities\explosivesbase.c:19` |
| 23 | Navmesh updates | `ECE_UPDATEPATHGRAPH` and obstacle generation for placed objects. | `P:\scripts\3_game\ce\centraleconomy.c:39` |
| 24 | Model LODs | `Geometry` (mass, collision), `PhysX` geometry, `Fire Geometry`, `View Geometry`, `Roadway`, component convexity, `autocenter` property. **knowledge**; check vanilla models with `/dayz-p3d-audit`. | Vanilla p3d under `P:\DZ` |
| 25 | Script models | `ScriptModel` example of a scripted dynamic body. | `P:\scripts\2_gamelib\entities\scriptmodel.c:39`-`49` |
