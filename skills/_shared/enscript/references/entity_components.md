# Entity components

What the vanilla scripts declare for Enfusion entity components (`GenericComponent`, `ScriptComponent`, `GenericEntity`): the `COMPONENT_SYSTEM` guard, the classes, inserting and removing a component, the event order and event masks. This is a map of declarations and their own comments; none of it is tested in game.

## Not in a DayZ game build

All of `P:\scripts\2_gamelib\components\gamelibcomponents.c` sits inside `#ifdef COMPONENT_SYSTEM` (`:1` to `:276`). `GenericEntity` is under the same guard (`P:\scripts\2_gamelib\entities\gamelibentities.c:3` to `:140`), and so is the `IEntity(IEntitySource src, IEntity parent)` constructor (`P:\scripts\1_core\proto\enentity.c:768` to `:771`). The table of static defines lists `COMPONENT_SYSTEM` as not defined for DayZ builds and defined for Workbench builds (`P:\scripts\staticdefinesdoc.c:15`).

So a mod's game scripts can't use these classes; they matter for Workbench tooling. Whether any shipped DayZ build defines the flag is unverified.

## The classes

| Class | What it is | Source |
|---|---|---|
| `GenericComponent : Managed` | The base, with constructor `protected void GenericComponent(IEntityComponentSource src, IEntity ent)` | `P:\scripts\2_gamelib\components\gamelibcomponents.c:25` to `:68` |
| `ScriptComponent : GenericComponent` | The parent of components written in script; each is created in the entity constructor | `gamelibcomponents.c:75` to `:86` |
| `GenericEntity extends IEntity` | The entity that holds components; `GenericWorldEntity`, `GenericTerrainEntity` and `LightEntity` derive from it (`:49` to `:57`) | `P:\scripts\2_gamelib\entities\gamelibentities.c:4` |
| `BaseSoundComponent : GenericComponent` | A sound component: event and signal names, `SetSignalValue`, `Play` and `Update` returning a `SoundHandle`, `Terminate`, `IsPlayed` | `gamelibcomponents.c:248` to `:274` |

## Inserting and removing

On `GenericEntity` (`P:\scripts\2_gamelib\entities\gamelibentities.c`):

| Call | What it does | Line |
|---|---|---|
| `FindComponent(typename)` | Returns the first component of that type | `:9` to `:13` |
| `InsertComponent` | Calls `OnComponentInsert` on all the entity's components, `EOnInit` on the new one if its mask has `EV_INIT`, and `EOnActivate` if it is active, which is the default | `:15` to `:22` |
| `RemoveComponent` | Calls `EOnDeactivate` on it and `OnComponentRemove` on all components; the entity is not deleted | `:24` to `:30` |
| `DeleteComponent` | The same as remove, then `OnDelete` | `:32` to `:39` |

## Event order

From the `ScriptComponent` comment (`P:\scripts\2_gamelib\components\gamelibcomponents.c:77` to `:84`):

1. `OnComponentInsert` on creation.
2. `EOnInit` after all components are inserted, only with `EV_INIT` set.
3. `EOnActivate` when both the entity and the component are active.
4. The other `EOn*` events, as the event mask allows.
5. `EOnDeactivate` on `Deactivate` or removal.
6. `OnComponentRemove` after a component is removed.
7. Deletion. The comment says `EOnDelete`; the declared method is `OnDelete(IEntity owner)` (`:228` to `:232`).

The other `protected void` events declared on `ScriptComponent` (`:95` to `:232`) are `EOnFrame`, `EOnPostFrame`, `EOnVisible`, `EOnNotVisible`, `EOnSimulate`, `EOnPostSimulate`, `EOnTouch`, `EOnContact`, `EOnPhysicsMove`, `EOnJointBreak`, `EOnAnimEvent`, `EOnSoundEvent` and `EOnExtra`. `TouchEvent` has `ON_ENTER`, `ON_STAY` and `ON_EXIT` (`:9` to `:15`).

## Event masks

`GenericComponent` has `GetEventMask`, `SetEventMask`, `ClearEventMask`, `Activate`, `Deactivate` and `IsActive` (`P:\scripts\2_gamelib\components\gamelibcomponents.c:31` to `:64`). `SetEventMask` ORs bits into the mask, and a component gets only the events whose bits are set (`:33` to `:40`).

Call `SetEventMask` in `OnComponentInsert`, not in the component constructor. The vanilla comment warns that the constructor call doesn't set the mask on the parent entity properly (`:36`). The values of `EV_INIT` and the other event bits are not declared in these files.
