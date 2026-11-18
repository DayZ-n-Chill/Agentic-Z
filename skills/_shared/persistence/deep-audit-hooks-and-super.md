# Engine hooks and the super chain

What to check when code overrides an engine event or relies on a `modded class` hook: what the event really delivers, whether each caller passes the parameters the override uses, and whether every class between the leaf and the modded base calls `super`. Use it in step 1 of `deep-audit.md` and in every review angle that touches hooks.

An override runs its parent only when it calls `super`, as `BaseBuildingBase.OnStoreLoad` does (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:434`). The cases below come from third-party mods; the vanilla lines they rest on are cited.

## Check what the event means, not only its signature

A game mode mod wired its respawn to the wrong event and passed the whole deep audit and two outside reviews, because every reviewer checked that the hook's signature exists in vanilla and none checked what the event means. For every engine event override (`OnClient*Event`, `EE*`, `On*`):

- Read the body of the vanilla handler; how it uses its parameters shows what they are. `OnClientRespawnEvent` kills the unconscious or restrained character that chose to respawn, so its `player` is the old character (`P:\scripts\5_mission\mission\missionserver.c:611` to `:622`). The new one is created in `OnClientNewEvent` (`missionserver.c:549`).
- Search real mods for who hooks that event and why. A mod that uses an event for a purpose no other mod uses it for is a finding, at medium confidence at least.

## Check that callers pass each parameter

The handler body does not show what a caller leaves out. For each parameter of an engine hook the override reads, find the vanilla call sites of that method and check that they pass it. A parameter with a default value is a promise the caller may not keep. When a call site leaves it out, the override works the value out itself (`GetPosition()`, `GetOrientation()`), or at least spots the default and makes no destructive decision with it.

The SimpleGroup mod's `OnPlacementComplete` override checked territory with `position` and called `ObjectDelete` when the check failed. Digging a garden plot calls the hook with only the player (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actiondiggardenplot.c:118`), and the parameter defaults to `"0 0 0"` (`P:\scripts\3_game\entities\entityai.c:613`), so the override got the map origin and deleted the plot. When a failed check deletes something (`ObjectDelete`, a file, a record), an unreliable parameter turns the check into a shredder. A check that deletes fails toward doing nothing.

When the findings are sorted into groups for a fix plan, compare the lists of IDs: the groups together must hold exactly the number of findings. One finding of 27 dropped out of a plan that way and was never fixed.

## Walk up the chain from the leaf

A failsafe in `modded class ItemBase` fires only when every class between the leaf and `ItemBase` calls `super`. In a virtual storage mod the leaf container's `Open()` called `super`, so a check declared the failsafe working. One level up, `RaG_ContainerBase` from the RaG_Core mod (its own `RaG_ContainerBase.c:142` to `:154`, not vanilla) set its state and returned from `Open()` and `Close()` without calling `super`, so the failsafe never fired for the whole family. Two separate checks missed it because both stopped at the leaf.

The walk takes about five minutes per family:

1. Resolve the whole chain from the leaf to the vanilla base by reading the `class X : Y` headers, in the unpacked sources of third-party mods or by searching their PBOs for strings.
2. In each class, search for `override void <Method>`. Where it exists, confirm it calls `super.<Method>()`. One missing link breaks the invariant for every class below it.
3. Record the verdict per family (the base class), not per leaf.
4. Where a link is broken, the failsafe does not cover that family. Add a hook on the family base that calls `super` and notifies explicitly.

A comment such as "handled because the leaf calls super" is a claim to check, not a fact, until the whole walk is on record.

## Walk down from a modded base

A `modded class <Base>` needs the opposite walk too. Inheriting from the base does not run the modded hook when a child overrides the method without calling `super`.

1. List every vanilla class below `<Base>`, the indirect ones too.
2. For each method the mod changes on `<Base>`, read every child override and note whether it calls `super.<Method>()` on every path.
3. A child override without that call leaves its whole family uncovered. Add a hook at that family's base, or write down that the invariant does not cover it.
4. Treat a comment such as "X and Y inherit this gate" as a claim to check.

Record the two walks separately: walking up proves a leaf reaches the hook, walking down proves no child skips it.
