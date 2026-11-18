# Hiding attachment proxies and gating seats

How to hide a proxy baked into a model while its slot is empty, which two config halves `HideSelection` needs, and how to make a seat unusable while something is attached. Both are read in the vanilla scripts and in mods that work in game; neither is tested in game here.

## `HideSelection` needs an animation source

A cargo or attachment proxy baked into the `.p3d` is drawn whether or not its slot holds an item. `HideSelection(name)` looks like the fix and does nothing on its own (`P:\scripts\3_game\entities\entityai.c:3355`):

```c
void HideSelection( string selection_name )
{
    if ( !ToDelete() )
        SetAnimationPhase ( selection_name, 1 );
}
```

`SetAnimationPhase` addresses an animation source, not a bare selection. The vanilla comment says so: "Sets all animation values to 1, making them INVISIBLE if they are configured in models.cfg in such way. These selections must also be defined in the entity's config class in 'AnimationSources'" (`entityai.c:1430`). Without both halves every call does nothing, and it looks like a timing race, so retries with `CallLater` never help.

## Which name the call takes

The string passed to `SetAnimationPhase` or `HideSelection` is the class name in `AnimationSources`, which is also the animation's `source` in `model.cfg`. It is not the animation's class name, and not always the selection name. Read in two mods that work in game:

| Piece | File | Example |
|---|---|---|
| Source | `config.cpp`, `AnimationSources` | `class rotor_static_hide { source="user"; animPeriod=0.001; initPhase=0; };` |
| Animation | `model.cfg`, `Animations` | `class main_rotor_static_hide { type="hide"; source="rotor_static_hide"; selection="main_rotor"; minValue=0; maxValue=1; hideValue=0.5; };` |
| Call | Script | `SetAnimationPhase("rotor_static_hide", staticHide)` |

Giving all three the same name also works (a storage mod and a gun rack mod use `hideproxy` for all three), which is why the rule is easy to get wrong by accident: a mod that uses one name everywhere shows nothing about which name the engine reads.

- `initPhase = 1` hides at spawn and `initPhase = 0` shows, checked in game in the gun rack mod and matching the vanilla comment. For a cargo slot that starts empty, use `1`.
- `hideValue = 0.01` with `animPeriod = 0.01` gives the near-instant swap the storage mod's unbinarized model uses.
- Both mods also make the hidden selection a skeleton bone. That is not shown to be needed, but a hide the engine ignores looks exactly like the unfixed fault, so copy them unless you have a reason not to.
- Set the phase again in `DeferredInit` and `AfterStoreLoad`, which vanilla describes as "Called when entity is being loaded from DB or Storage (after all children loaded)" (`entityai.c:1418`), and in `EEItemAttached` and `EEItemDetached`.

## Blocking a seat while something is attached

To make a seat unusable while a part is mounted, override the check `ActionGetInTransport` already makes rather than adding a parallel one. `CrewCanGetThrough` is on `Transport` (`P:\scripts\3_game\vehicles\transport.c:724`), and the get-in action checks it (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:54`):

```c
if (!transport.CrewCanGetThrough(crewIndex) || !transport.IsAreaAtDoorFreeDiag(crewIndex))
    return false;
```

Vanilla uses it for doors (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:226`). For an attachment:

```c
override bool CrewCanGetThrough(int posIdx)
{
    switch (posIdx)
    {
        case 0: return true;
        case 1: return FindAttachmentBySlotName("MyMod_Backpack") == null;
    }
    return false;
}
```

The null check is vanilla's own idiom: `return FindAttachmentBySlotName(slotName) != null;` (`P:\scripts\4_world\entities\explosivesbase\improvisedexplosive.c:215`).
