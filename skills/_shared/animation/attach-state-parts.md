# Showing and hiding parts with attach state

How a host shows or hides a part of its own model when something is attached to a slot, and how an item swaps between two of its own models when it is attached. Both reuse `hide` animations on `user` sources; no new clips. How a held item gets its pose is in `items-in-hands.md`.

## The two calls

- `HideSelection(string selection_name)` and `ShowSelection` are on `EntityAI` (`P:\scripts\3_game\entities\entityai.c:3355`, `:3364`). They are `SetAnimationPhase` calls: 1 hides and 0 shows (`:3359`). The selection needs a `user` source of the same name and a `hide` animation in `model.cfg`.

## A part of the host that follows a slot

A part that is already in the host's `.p3d` appears or disappears with what is attached to a slot. Its visibility is a `hide` animation on a `user` source, set in the attach and detach events.

`config.cpp`:

```cpp
class AnimationSources
{
    class hide_barrel1 { source = "user"; animPeriod = 0.1; initPhase = 1; };   // starts hidden
};
```

`model.cfg`, inside `class Animations`:

```cpp
class hide_barrel1 { type = "hide"; source = "hide_barrel1"; selection = "barrel_1"; minValue = 0; maxValue = 1; hideValue = 0.5; };
```

Script on the host:

```c
override void EEItemAttached(EntityAI item, string slot_name)
{
    super.EEItemAttached(item, slot_name);
    if (slot_name == "MyMod_Barrel1")
        SetAnimationPhase("hide_barrel1", 0);   // 0 shows
}

override void EEItemDetached(EntityAI item, string slot_name)
{
    super.EEItemDetached(item, slot_name);
    if (slot_name == "MyMod_Barrel1")
        SetAnimationPhase("hide_barrel1", 1);   // 1 hides
}
```

- An animation phase of 1 hides and 0 shows. Vanilla says so itself: `HideSelection` is `SetAnimationPhase(selection_name, 1)` with the comment "1 = hide, 0 = unhide!" (`P:\scripts\3_game\entities\entityai.c:3355` to `:3361`). The value where the flip happens is `hideValue`; vanilla barrel lids use 0.6 (`model-cfg-animations.md`), and the 0.5 above works in game on a vehicle mod.
- `EEItemAttached` and `EEItemDetached` are on `EntityAI` (`P:\scripts\3_game\entities\entityai.c:1159`, `:1199`). `EEItemAttached` also fires for items created with `CreateInInventory` (seen in game, not checked on `P:\`), so debug spawned attachments update too.
- The attached item is still a real inventory item; the hide only changes how the host shows it.
- Use it for visible cargo (jerry cans, barrels, spare wheels) and modular parts that would otherwise need many `.p3d` variants. Do not use it when the part changes collision: that needs real model variants.

## Two models in one item: swap by attach state

The item carries two selections, a detailed one for the ground and a lighter one for when it is attached, and shows one of them. The item drives it from its own hooks, not the host. Vanilla does exactly this with the flag:

- Config: two `user` sources named after the selections, `folded` with `initPhase = 0` (shown) and `unfolded` with `initPhase = 1` (hidden) (`P:\DZ\gear\camping\config.cpp:13062` to `:13076`).
- Script: the constructor shows `folded` and hides `unfolded`, `OnWasAttached` swaps them and `OnWasDetached` swaps back (`P:\scripts\4_world\entities\itembase\flag_base.c:7`, `:25`, `:33`).

```c
void MyItem()
{
    ShowSelection("not_attached");
    HideSelection("attached");
}

override void OnWasAttached(EntityAI parent, int slot_id)
{
    super.OnWasAttached(parent, slot_id);
    HideSelection("not_attached");
    ShowSelection("attached");
}

override void OnWasDetached(EntityAI parent, int slot_id)
{
    super.OnWasDetached(parent, slot_id);
    ShowSelection("not_attached");
    HideSelection("attached");
}
```

`ShowSelection` and `HideSelection` are on `EntityAI` (`P:\scripts\3_game\entities\entityai.c:3364`, `:3355`); the `OnWasAttached` and `OnWasDetached` hooks are declared at `:1864` and `:1867`. The `model.cfg` needs its own skeleton with both selections as bones and one `hide` animation per selection, each with the selection's name as its source. `hiddenSelections[]` still lists only the texture selections. Both selections must exist in the visual LODs and the View Geometry, and in the Geometry LOD when the attached model needs collision.

Compared with the host route above, that one hides one selection from the host's attach events; this one swaps two selections from the item's own events.
