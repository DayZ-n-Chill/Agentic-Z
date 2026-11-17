# Entity component system (`GenericEntity` / `GenericComponent` / `ScriptComponent`)

Covers the declared Enfusion entity component classes in the vanilla scripts: the `COMPONENT_SYSTEM` guard, the class map, insert and remove, the event order, event masks and the `ScriptComponent` signatures.

Status: checked on `P:\` on 2026-11-17: the four cited files on `P:\scripts` have the SHA-256 values listed under "Reproduce", so every `path:line` below is the same line on `P:\`.

## Scope and build

This note maps the **declared** Enfusion entity component surface in the official DayZ scripts, build `119356`. It is a source map, not a tutorial: every statement below paraphrases the cited declaration or its own comment, with a `path:line` locator; no engine behaviour beyond those comments is claimed, and nothing was measured at runtime. `ScriptedEntity`, triggers, ScriptRPC/networking and persistence streams are out of scope here.

Primary sources, all under `scripts/` in the build `119356` tree: `2_gamelib/components/gamelibcomponents.c` (component classes), `2_gamelib/entities/gamelibentities.c` (entity classes), `1_core/proto/enentity.c` (the `IEntity` constructor declaration) and `staticdefinesdoc.c` (the static-define documentation table).

## The `COMPONENT_SYSTEM` guard

The whole of `gamelibcomponents.c` sits between `#ifdef COMPONENT_SYSTEM` at line 1 and `#endif` at line 276, so the component classes in that file are compiled only when the flag is defined. `GenericEntity` is likewise declared under `#ifdef COMPONENT_SYSTEM` at `P:\scripts\2_gamelib\entities\gamelibentities.c:3` (matching `#endif` at line 141), and the `IEntity` constructor `protected void IEntity(IEntitySource src, IEntity parent)` is declared under the same guard at `P:\scripts\1_core\proto\enentity.c:768-771`. The documentation table describes `COMPONENT_SYSTEM` as the "Enfusion entity component system" and records it as not defined for DayZ builds and defined for Workbench builds (`P:\scripts\staticdefinesdoc.c:15`). Read that narrowly: this note claims compilation conditional on the flag, and what the documentation table records — not that a given shipped DayZ build enables or disables the system at runtime.

## Class map

`GenericComponent : Managed` is the base component class, and its constructor is `protected void GenericComponent(IEntityComponentSource src, IEntity ent)` (`P:\scripts\2_gamelib\components\gamelibcomponents.c:25-68`). `IEntityComponentSource` is declared just above it as a `BaseContainer` with a `typedef int[]` of the same name (`P:\scripts\2_gamelib\components\gamelibcomponents.c:4-7`). `ScriptComponent : GenericComponent` is the parent class for components created in script, and every `ScriptComponent` is created in the entity constructor (`P:\scripts\2_gamelib\components\gamelibcomponents.c:75-86`). `GenericEntity extends IEntity` is the entity side of the pair (`P:\scripts\2_gamelib\entities\gamelibentities.c:4`); the same guarded block declares `GenericWorldEntity`, `GenericTerrainEntity` and `LightEntity` as its subclasses (`P:\scripts\2_gamelib\entities\gamelibentities.c:49-57`). A `GenericComponentClass` with a `DependsOn(typename, TypeID)` stub sits at `P:\scripts\2_gamelib\components\gamelibcomponents.c:70-73`; the cited range shows no further contract for it.

## Insert, remove, delete

`FindComponent(typename typeName)` returns the first occurrence of the corresponding component (`P:\scripts\2_gamelib\entities\gamelibentities.c:9-13`). `InsertComponent(GenericComponent)` calls `OnComponentInsert` on all of the entity's components, calls `EOnInit` on the component if it sets the `EV_INIT` mask, and calls `EOnActivate` if the component is active, which is the default (`P:\scripts\2_gamelib\entities\gamelibentities.c:15-22`). `RemoveComponent(GenericComponent)` removes the component without deleting the entity, calls `EOnDeactivate` on the component, and calls `OnComponentRemove` on all of the entity's components (`P:\scripts\2_gamelib\entities\gamelibentities.c:24-30`). `DeleteComponent(GenericComponent)` does everything `RemoveComponent` does and additionally calls `OnDelete` on the component (`P:\scripts\2_gamelib\entities\gamelibentities.c:32-39`).

## Lifecycle and event order

The `ScriptComponent` class comment declares this order (`P:\scripts\2_gamelib\components\gamelibcomponents.c:77-84`):

1. `OnComponentInsert` on creation (last Workbench event in edit mode).
2. `EOnInit` after all components are inserted, only with `EV_INIT` set.
3. `EOnActivate` if the entity is `TFL_ACTIVE` and the component is active; a component is active by default.
4. The remaining `EOn*` events, per the registered event mask.
5. `EOnDeactivate` on `Deactivate` or removal; must be active to deactivate.
6. `OnComponentRemove` after a component is removed.
7. Deletion notification as the entity is going to be destroyed.

Steps 2, 3, 5 and 6 restate the insert/remove contract above. One naming wrinkle in the source: step 7 of the comment says `EOnDelete`, while the declared method is `OnDelete(IEntity owner)`, whose own comment says it is called when the entity is being destroyed or the component is to be deleted via `Game::DeleteScriptComponent` (`P:\scripts\2_gamelib\components\gamelibcomponents.c:228-232`).

## Event masks

`GenericComponent` exposes `GetEventMask()`, `SetEventMask(IEntity owner, int mask)`, `ClearEventMask(IEntity owner, int mask)`, `Activate(IEntity owner)`, `Deactivate(IEntity owner)` and `IsActive()` (`P:\scripts\2_gamelib\components\gamelibcomponents.c:31-64`). `SetEventMask` ORs the given bits into the existing mask, and a component accepts only events whose bits are set in its mask (`P:\scripts\2_gamelib\components\gamelibcomponents.c:33-40`). The constructor caveat is declared in that same comment: calling `SetEventMask` in the component constructor does not properly set the event mask on the parent entity, and the comment recommends `OnComponentInsert` instead (`P:\scripts\2_gamelib\components\gamelibcomponents.c:36`). `ClearEventMask` clears only the bits set in its argument (`P:\scripts\2_gamelib\components\gamelibcomponents.c:42-48`).

## Declared `ScriptComponent` signatures

All of the following are `protected void` declarations on `ScriptComponent` (`P:\scripts\2_gamelib\components\gamelibcomponents.c:95-232`).

Lifecycle and component membership: `EOnInit(IEntity owner, int extra)` (after all of the entity's components have received `OnComponentInsert`), `EOnActivate(IEntity owner)`, `EOnDeactivate(IEntity owner)`, `OnComponentInsert(IEntity owner, ScriptComponent other)`, `OnComponentRemove(IEntity owner, ScriptComponent other)` and `OnDelete(IEntity owner)`.

Frame, visibility and simulation: `EOnFrame(IEntity owner, float timeSlice)`, `EOnPostFrame(IEntity owner, int extra)`, `EOnVisible(IEntity owner, int extra)`, `EOnNotVisible(IEntity owner, int extra)`, `EOnSimulate(IEntity owner, float timeslice)` and `EOnPostSimulate(IEntity owner, float timeslice)`.

Touch, physics and miscellaneous: `EOnTouch(IEntity owner, int extra)`, `EOnContact(IEntity owner, Contact extra)`, `EOnPhysicsMove(IEntity owner, int extra)`, `EOnJointBreak(IEntity owner, int extra)`, `EOnAnimEvent(IEntity owner, AnimEvent extra)`, `EOnSoundEvent(IEntity owner, SoundEvent extra)` and `EOnExtra(IEntity owner, int extra)` — an extension event; the comment notes a Trigger uses it when an insider is leaving.

The `TouchEvent` enum declares `ON_ENTER`, `ON_STAY` and `ON_EXIT` (`P:\scripts\2_gamelib\components\gamelibcomponents.c:9-15`).

## `BaseSoundComponent`: a vanilla example

`BaseSoundComponent : GenericComponent` is a vanilla script-side component for sound, declared at `P:\scripts\2_gamelib\components\gamelibcomponents.c:248-274`. Its declared native surface lists event and signal names (`GetEventNames`, `GetSignalNames`, `GetSignalIndex`), sets signal values by name or index (`SetSignalValueName`, `SetSignalValue`), plays and updates sounds returning a `SoundHandle` (`Play`, `Update`), terminates a sound (`Terminate`, `void`), queries it (`IsPlayed`, `IsHandleValid`, `bool`), and declares `SetTransform(vector[])` and `SetDebug(bool)` (`P:\scripts\2_gamelib\components\gamelibcomponents.c:248-274`).

## What is not claimed

- No runtime behaviour: nothing was spawned, inserted or removed in a running build.
- No enablement claim beyond the guard and the table cited above.
- No config-registration tutorial: the cited ranges do not show how a mod registers a component type in config, so this note does not describe one.
- No definition of `EV_INIT`, `TFL_ACTIVE` or `enf::EntityEvents`: the comments reference them; their declarations are outside the cited ranges.

## Reproduce

From the build `119356` script tree (paths relative to `scripts/`):

```sh
sed -n '1,276p' 2_gamelib/components/gamelibcomponents.c
sed -n '1,141p'  2_gamelib/entities/gamelibentities.c
sed -n '768,771p' 1_core/proto/enentity.c
sed -n '15p' staticdefinesdoc.c
sha256sum 2_gamelib/components/gamelibcomponents.c \
  2_gamelib/entities/gamelibentities.c \
  1_core/proto/enentity.c staticdefinesdoc.c
```

Expected SHA-256 — `gamelibcomponents.c`: `5ffaed4be8ceab6aea526118e9be61247dfb72a652ba3a71c12889af136deae9`; `gamelibentities.c`: `defbc4011bc1d3ed310f22fad7bf1c90015a0c4d29764c8245b8805f47b835ab`; `enentity.c`: `8c54e810605c758c852713cca6ea4cc4e3a81311f22601bce101231e05ea246a`; `staticdefinesdoc.c`: `59e509055a4c06306871b7f41a2904e567c4ce2186878742e0ce2158b49437ac`.

## Limits and open questions

- The mask values (`EV_INIT`, the rest of `enf::EntityEvents`) and `TFL_ACTIVE` are referenced, not defined, in the cited ranges.
- Whether any shipped DayZ build defines `COMPONENT_SYSTEM` for game code is not settled here; the table records Workbench only.
- `GenericComponentClass.DependsOn` is an empty stub in the cited range; whether the engine consumes it is not claimed.
- Cross-component event order on one entity is not described in the cited comments and is not claimed.
