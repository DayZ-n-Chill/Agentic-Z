# Runtime pitfalls

Which code compiles and then crashes, loses items or slows the server: array element assignment, shaders on a dedicated server, hologram ghosts, merge loops, float time, slow world queries, and the retail replacements for diag-only plugins. Boot-time traps are in `runtime-traps.md`.

## Crashes

- Reported, not checked on `P:\`: assigning a compound expression straight to an array element segfaults, as in `m_IsInside[index] = vector.DistanceSq(a, b) <= distSq;`. Put the result in a local first, then assign the local.
- Reported in a third-party mod, not checked on `P:\`: an `.rvmat` stage with `shader = NormalMapMacro;` crashes a dedicated server when the model loads. Use the `Super` shader.
- Reported, not checked on `P:\`: creating a `ScriptView` inside an RPC handler crashes, because its constructor builds widgets and there is no workspace. Create it in `MissionGameplay.OnInit()` and show or hide it later (`dabs-mvc-advanced.md`).
- Seen in one third-party mod, cause not isolated: a `ref map<Widget, int>` crashed at runtime. `Widget` is a valid key in vanilla: `m_RadialItemCards` is a `map<Widget, float>` (`P:\scripts\3_game\gui\effects\radialmenu.c:17`), and `m_MultiOptionSelectors` (`P:\scripts\5_mission\gui\newui\charactercreation\charactercreationmenu.c:32`) and `m_SpawnButtonsOriginalText` (`P:\scripts\5_mission\gui\scriptconsoleitemstab.c:22`) are keyed by `Widget`. Check first whether the map outlives its widgets; `production-patterns.md` uses one for its hover cache.

## Hologram previews are real entities

The hologram creates a real entity of the `ProjectionBasedOnParent()` class for the preview, on the server and as a local object on the client (`CreateObjectEx` at `P:\scripts\4_world\classes\hologram.c:114` and `:121`; vanilla `PlaceEntity` is at `:1044`). Reported, not checked on `P:\`: without a `PlaceEntity()` override that returns the entity it was given, ghost entities pile up.

```c
override EntityAI PlaceEntity(EntityAI entity_for_placing)
{
    return entity_for_placing;
}
```

Also reported: only one `modded class Hologram` may exist across all loaded files.

## Merge loops can lose items

`ItemBase.CombineItems` empties the donor with `AddQuantity(-used)`, which goes through `SetQuantity`. For items with `varQuantityDestroyOnMin = 1`, such as `Rag`, `SetQuantity` at the minimum calls `this.Delete()` (`P:\scripts\4_world\entities\itembase.c:3333` to `:3338`). `EntityAI.Delete()` only sets `m_PendingDelete` (`P:\scripts\3_game\entities\entityai.c:779` to `:782`), and `Object.Delete()` queues `ObjectDelete` for the next frame (`P:\scripts\3_game\entities\object.c:82` to `:85`). Until then the empty stack is still in cargo with quantity 0, and `CanBeCombined` (`itembase.c:2137` to `:2197`) does not check for a pending delete, so an empty stack counts as a valid target.

A loop that merges several times in one call, such as stack-all or loot consolidation, can then move live quantity into the empty stack, and everything moved there vanishes next frame. With rag stacks of 2, 2 and 5: B merges into A and is left empty, C fills A and keeps 3, then C merges into the empty B, and 9 rags become 6. Read from the vanilla scripts, not reproduced in game.

Before each target and donor, skip entities queued for deletion (`IsSetForDeletion`, `entityai.c:812` to `:814`) and empty ammo piles:

```c
if (!item || item.IsSetForDeletion())
    continue;
Magazine pile = Magazine.Cast(item);
if (pile && pile.GetAmmoCount() <= 0)
    continue;
```

## Time in a float

`GetTime()` returns an `int` of milliseconds (`P:\scripts\3_game\global\game.c:1534`). Stored in a 32-bit `float`, about 7 significant digits, it stops holding every millisecond after 2^24 ms, about 4.66 hours, when the step becomes 2 ms; after about 46 hours the step is 16 ms, and it keeps doubling. Keep time in an `int`.

`int.ToString()` and `float.ToString()` work, but there is no printf-style formatting; write a small helper for fixed decimals.

## Slow world queries

These are `proto native` calls on `CGame`; that they are slow is reported, not measured:

| Call | Declared | Prefer |
|---|---|---|
| `GetObjectsAtPosition`, `GetObjectsAtPosition3D` | `P:\scripts\3_game\global\game.c:923`, `:930` | A static list of instances on your class, a trigger, or the scene queries |
| `SurfaceIsSea`, `SurfaceIsPond` | `:1196`, `:1197` | `g_Game.GetWaterDepth(pos) > 0` (`:1198`) |
| `SurfaceRoadY` | `:1177` | `Vector(x, g_Game.SurfaceY(x, z), z)` for a plain ground point |

Vanilla uses both water checks: `SurfaceIsSea` or `SurfaceIsPond` in the hologram (`P:\scripts\4_world\classes\hologram.c:1128`), and `GetWaterDepth` for transport (`P:\scripts\3_game\vehicles\transport.c:540`) and the player (`P:\scripts\4_world\entities\manbase\playerbase.c:7138`). Over rivers and streams see `_shared/physics/water-queries.md`: on vanilla Chernarus, `SurfaceIsPond` reads false at the centre of most river and stream pieces above 50 m.

Reported, cause not checked on `P:\`: a `foreach` straight over a getter's return value misbehaves. Copy it to a local, or loop over a member directly.

## Retail replacements for `PluginDeveloper`

`PluginDeveloper` registers only under `#ifdef DIAG_DEVELOPER` (`RegisterPluginDiag`, `P:\scripts\4_world\plugins\pluginmanager.c:65`, `:249` to `:254`). On a release server `GetPlugin(PluginDeveloper)` returns null, so a teleport or give built on it (`TeleportAtCursor`, `SpawnEntityInInventory`) compiles, works in diag and does nothing in release. Admin tools such as Community Online Tools use these instead:

- Teleport: `player.SetPosition(pos)`, resolving `GetGame().SurfaceY(x, z)` first when the height is 0.
- A seated player and the vehicle: `HumanCommandVehicle vc = player.GetCommand_Vehicle();` (`P:\scripts\3_game\human.c:1528`), `Transport veh = vc.GetTransport();` (`:716`), then `veh.GetTransform(mat); mat[3] = pos; veh.SetTransform(mat);`. The occupant moves with the vehicle one frame later, so report `veh.GetPosition()`, not the player's.
- Give: `player.GetInventory().CreateInInventory(cls)` or `player.GetHumanInventory().CreateInHands(cls)` (`P:\scripts\3_game\systems\inventory\humaninventory.c:44`), guarding on `player.GetItemInHands()`.
