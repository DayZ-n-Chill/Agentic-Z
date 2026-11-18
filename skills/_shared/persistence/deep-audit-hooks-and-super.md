# Engine hooks and the super chain

Checks for code that overrides an engine event or relies on a `modded class` hook: what the event really delivers, whether the caller passes each parameter, and whether every class between the leaf and the modded base calls `super`. Open this in step 1 and when writing the prompts for any angle that touches hooks.

These are audit lessons from third-party mods; the one vanilla fact to keep in mind is that an override only runs its parent when it calls `super`, as `BaseBuildingBase.OnStoreLoad` does (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:434`).

## Engine event semantics and plan completeness

Case: a game mode mod. A respawn wired to the wrong event passed this procedure's entire pass (eight auditors and the cross-actor check) and two external reviews, because everyone verified the hook's signature and no one verified what the event means. In addition, one finding fell out of the remediation plan unclassified (the groups covered 26 of 27 findings).

- **Add to the auditor prompts (every dimension that touches hooks)**: for each engine event override (`OnClient*Event`, `EE*`, `On*`), verifying that the signature exists in vanilla is not enough. Verify the parameter contract. (1) Read the body of the vanilla event handler; how it uses its parameters reveals what it delivers. The canonical example: `OnClientRespawnEvent` kills the unconscious or restrained character that chose to respawn, so its `player` is the old character (`P:\scripts\5_mission\mission\missionserver.c:611-622`); the new one is created in `OnClientNewEvent` (`missionserver.c:549`). (2) Grep prior art across real mods: who hooks that event and for what purpose. If the audited mod uses an event that no prior art uses for that purpose, that is a finding (at least Medium confidence).

- **Vanilla call-sites for each consumed parameter**: the handler body does not tell you what a caller chooses not to pass. For each parameter of an engine hook that the override uses, grep the vanilla call-sites of that method and verify that they actually pass it. A parameter with a default value in the signature is a promise the caller might not keep. If any call-site omits it, the override must derive the data itself (`GetPosition()`, `GetOrientation()`) instead of trusting the argument, or at least detect the default and make no destructive decision with it. **Severity corollary**: when the action on a failed validation is destructive (`ObjectDelete`, deleting a file, dissolving a record), an unreliable parameter turns a gate into a shredder. Gates that delete must fail **closed toward inaction**, not toward destruction. Case: the SimpleGroup mod, where an `OnPlacementComplete` override validated territory with `position`. The vanilla call-site that digs a garden plot calls the hook with only the player (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actiondiggardenplot.c:118`), and the parameter defaults to `"0 0 0"` (`P:\scripts\3_game\entities\entityai.c:613`), so the override received `(0,0,0)` and called `ObjectDelete`.
- **Plan completeness checklist (step 2, when processing findings)**: if the audit produced N findings and the plan sorts them into groups, verify mechanically that the union of the groups has exactly N members (compare lists of IDs, not memory). A finding without a group is a lost finding (the case above lost one of 27).

## Super-chain verification is a full-ancestry walk, not a leaf check

Case: a virtual storage mod. The mod's physical Open/Close failsafe (`modded class ItemBase`) only fires if every class between the leaf and ItemBase calls `super`. A verification pass checked the leaf (`rag_baseitems_container_base.Open()`, which calls `super`) and declared the invariant satisfied. The break was one level up: `RaG_ContainerBase.Open()` and `Close()` (the RaG_Core mod, `RaG_ContainerBase.c:142-154`; third-party source) set state and return without calling `super`, so the failsafe never fires for the entire family. The miss survived two independent verification passes (an earlier session and a search agent) because both stopped at the leaf.

Procedure (mechanical, about five minutes per family):
1. Resolve the full chain, from the leaf through its parents to the vanilla base (`class X : Y` headers; the extracted sources of third-party mods, or a string search of their PBOs).
2. For each class in the chain, grep `override void <Method>`; if it is present, confirm that it calls `super.<Method>()`. One missing link voids the invariant for every descendant.
3. Record the verdict per family (base class), not per leaf class name.
4. If any link is broken, the failsafe does not cover that family, and a dedicated wrapper hook on the family base (with `super` and an explicit notify) is required.

Corollary: a bridge or failsafe decision justified by "handled when the leaf chains super" is unverified until the full walk is on record. Treat such comments as claims to audit, not facts.

## The super-chain walk also goes downward from a modded base

The full-ancestry walk above protects an invariant while moving from a leaf toward its bases. A `modded class <Base>` needs the opposite walk too: inheriting from the base does not execute the modded hook when a descendant overrides that method without chaining `super`.

Procedure:

1. Enumerate every vanilla descendant of `<Base>`; include indirect descendants rather than stopping at the first level.
2. For each method modified on `<Base>`, inspect every descendant override and record whether it calls `super.<Method>()` on every applicable path.
3. Treat an override without that chain as a family-sized coverage hole. Add a dedicated hook at the correct family boundary or document that the invariant does not cover that family.
4. Treat comments such as "X and Y inherit this gate" as claims to audit, not evidence.

Record both directions separately: leaf-to-base proves that a leaf reaches the hook, while base-to-descendants proves that no overriding child bypasses it.
