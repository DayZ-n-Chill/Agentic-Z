# Reference: entity components (`GenericComponent`, `ScriptComponent`, `GenericEntity`)

The Enfusion entity component classes declared in the vanilla scripts: the `COMPONENT_SYSTEM` guard, the classes, insert and remove, the event order and event masks. Every line below was opened on `P:\scripts`. This is a map of declarations and their own comments; nothing was run in game.

## Not in a DayZ game build

All of `P:\scripts\2_gamelib\components\gamelibcomponents.c` sits inside `#ifdef COMPONENT_SYSTEM` (`:1` to `:276`). `GenericEntity` is under the same guard (`P:\scripts\2_gamelib\entities\gamelibentities.c:3` to `:141`), and so is the `IEntity(IEntitySource src, IEntity parent)` constructor (`P:\scripts\1_core\proto\enentity.c:768-771`). The table of static defines records `COMPONENT_SYSTEM` as not defined for DayZ builds and defined for Workbench builds (`P:\scripts\staticdefinesdoc.c:15`). So a DayZ mod's game scripts cannot use these classes; they matter for Workbench tooling. Whether any shipped DayZ build defines the flag is not settled.

## Classes

- `GenericComponent : Managed`, constructor `protected void GenericComponent(IEntityComponentSource src, IEntity ent)` (`P:\scripts\2_gamelib\components\gamelibcomponents.c:25-68`).
- `ScriptComponent : GenericComponent`, the parent of components written in script; each is created in the entity constructor (`:75-86`).
- `GenericEntity extends IEntity` (`P:\scripts\2_gamelib\entities\gamelibentities.c:4`), with `GenericWorldEntity`, `GenericTerrainEntity` and `LightEntity` below it (`:49-57`).
- `BaseSoundComponent : GenericComponent` is a vanilla sound component: event and signal names, `SetSignalValue`, `Play` and `Update` returning a `SoundHandle`, `Terminate`, `IsPlayed` (`P:\scripts\2_gamelib\components\gamelibcomponents.c:248-274`).

## Insert, remove, delete

On `GenericEntity` (`P:\scripts\2_gamelib\entities\gamelibentities.c`):

- `FindComponent(typename)` returns the first component of that type (`:9-13`).
- `InsertComponent` calls `OnComponentInsert` on all the entity's components, `EOnInit` on the new one if it has `EV_INIT` in its mask, and `EOnActivate` if it is active, which is the default (`:15-22`).
- `RemoveComponent` calls `EOnDeactivate` on it and `OnComponentRemove` on all components; the entity is not deleted (`:24-30`).
- `DeleteComponent` does the same and also calls `OnDelete` (`:32-39`).

## Event order

From the `ScriptComponent` comment (`P:\scripts\2_gamelib\components\gamelibcomponents.c:77-84`):

1. `OnComponentInsert` on creation.
2. `EOnInit` after all components are inserted, only with `EV_INIT` set.
3. `EOnActivate` when the entity is active and the component is active.
4. The other `EOn*` events, as the event mask allows.
5. `EOnDeactivate` on `Deactivate` or removal.
6. `OnComponentRemove` after a component is removed.
7. Deletion: the comment says `EOnDelete`, the declared method is `OnDelete(IEntity owner)` (`:228-232`).

The declared `protected void` events on `ScriptComponent` (`:95-232`) also include `EOnFrame`, `EOnPostFrame`, `EOnVisible`, `EOnNotVisible`, `EOnSimulate`, `EOnPostSimulate`, `EOnTouch`, `EOnContact`, `EOnPhysicsMove`, `EOnJointBreak`, `EOnAnimEvent`, `EOnSoundEvent` and `EOnExtra`. `TouchEvent` has `ON_ENTER`, `ON_STAY` and `ON_EXIT` (`:9-15`).

## Event masks

`GenericComponent` has `GetEventMask`, `SetEventMask`, `ClearEventMask`, `Activate`, `Deactivate` and `IsActive` (`P:\scripts\2_gamelib\components\gamelibcomponents.c:31-64`). `SetEventMask` ORs bits into the mask, and a component gets only the events whose bits are set (`:33-40`). The comment warns that calling `SetEventMask` in the component constructor does not set the mask on the parent entity properly; call it in `OnComponentInsert` (`:36`). The values of `EV_INIT` and the other event bits are not declared in these files.
