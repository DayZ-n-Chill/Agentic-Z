# Engine hooks and the super chain

Checks for code that overrides an engine event or relies on a `modded class` hook: what the event really delivers, whether the caller passes each parameter, and whether every class between the leaf and the modded base calls `super`. Open this in step 1 and when writing the prompts for any angle that touches hooks.

These are audit lessons from third-party mods; the one vanilla fact to keep in mind is that an override only runs its parent when it calls `super`, as `BaseBuildingBase.OnStoreLoad` does (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:434`).

## Engine event semantics and plan completeness

Case: the LFGungame mod, a respawn wiring on the wrong event passed this skill's entire pass (8 auditors + cross-actor) and 2 external reviews because everyone verified the hook's SIGNATURE and no one its SEMANTICS. And one finding fell out of the remediation plan unclassified (groups covered 26/27 findings).

- **Add to auditor prompts (all dimensions touching hooks)**: for each engine event override (`OnClient*Event`, `EE*`, `On*`), verifying that the signature exists in vanilla is NOT enough. Verify parameter CONTRACT: (1) read the body of vanilla event handler, its internal usage reveals what it delivers (canonical example: `OnClientRespawnEvent` kills the unconscious or restrained character that chose to respawn, so its `player` is the OLD character, `P:\scripts\5_mission\mission\missionserver.c:611-622`; the new one is born in `OnClientNewEvent`, `missionserver.c:549`); (2) grep prior art across real tree mods: who hooks that event and for what purpose. If the audited mod uses an event that no prior art uses for that purpose, it is a finding (Medium confidence minimum).

- **Vanilla call-sites for each consumed parameter**: the handler body does not tell what caller chooses not to pass. For each parameter of an engine hook that override CONSUMES, grep vanilla call-sites of that method and verify they actually pass it. A parameter with a default value in signature is a promise caller might not keep. If any call-site omits it, override must derive the data on its own (`GetPosition()`, `GetOrientation()`) instead of trusting the argument, or at least detect default and not make destructive decisions with it. **Severity corollary**: when action upon validation failure is destructive (`ObjectDelete`, deleting a file, dissolving a record), an unreliable parameter turns a gate into a shredder. Gates that delete must fail **closed toward inaction**, not toward destruction. Case: the SimpleGroup mod, an `OnPlacementComplete` override validated territory with `position`; the vanilla call-site that digs a garden plot calls the hook with only the player (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actiondiggardenplot.c:118`), and the parameter defaults to `"0 0 0"` (`P:\scripts\3_game\entities\entityai.c:613`), so the override received `(0,0,0)` and called `ObjectDelete`.
- **Plan completeness checklist (step 2, when processing findings)**: if audit produced N findings and plan classifies them into groups, mechanically verify that |union of groups| == N (list of IDs, not from memory). A finding without group = lost finding (the case above lost one of 27).

## Super-chain verification is a full-ancestry walk, not a leaf check

Case: the LF_VStorage mod. The mod's physical Open/Close failsafe (`modded class ItemBase`) only fires if every class between the leaf and ItemBase chains `super`. A verification pass checked the leaf (`rag_baseitems_container_base.Open()`, chains super) and declared the invariant satisfied. The break was one level up: `RaG_ContainerBase.Open()/Close()` (the RaG_Core mod, `RaG_ContainerBase.c:142-154`; third-party source) set state and return WITHOUT `super`, the failsafe never fires for the entire family. The miss survived TWO independent verification passes (a prior session and a search agent) because both stopped at the leaf.

Procedure (mechanical, ~5 min per family):
1. Resolve the full chain, from the leaf through its parents to the vanilla base (`class X : Y` headers; third-party mods' extracted sources or PBO string-grep).
2. For EACH class in the chain, grep `override void <Method>`, if present, confirm it calls `super.<Method>()`. One missing link voids the invariant for every descendant.
3. Record the verdict per FAMILY (base class), not per leaf classname.
4. If any link is broken: the failsafe does not cover that family, a dedicated wrapper hook on the family base (with super + explicit notify) is required.

Corollary: a bridge/failsafe decision justified by "handled when the leaf chains super" is UNVERIFIED until the full walk is on record. Treat such comments as claims to audit, not facts.

## The super-chain walk also goes downward from a modded base

The full-ancestry walk above protects an invariant while moving from a leaf toward its bases. A `modded class <Base>` needs the opposite walk too: inheriting from the base does not execute the modded hook when a descendant overrides that method without chaining `super`.

Procedure:

1. Enumerate every vanilla descendant of `<Base>`; include indirect descendants rather than stopping at the first level.
2. For each method modified on `<Base>`, inspect every descendant override and record whether it calls `super.<Method>()` on every applicable path.
3. Treat an override without that chain as a family-sized coverage hole. Add a dedicated hook at the correct family boundary or document that the invariant does not cover that family.
4. Treat comments such as "X and Y inherit this gate" as claims to audit, not evidence.

Record both directions separately: leaf-to-base proves that a leaf reaches the hook, while base-to-descendants proves that no overriding child bypasses it.
