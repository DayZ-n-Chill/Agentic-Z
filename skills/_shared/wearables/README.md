# Wearables pack

Reference for clothing, gear and survivor characters: which vanilla class to inherit, slots and cargo, protection and insulation, color variants, the models and proxies behind them, the worn models that bind to the player, and the rigging of a new body. It is written for `dayz-wearables-specialist`, and any DayZ worker may open one file of it when a task needs it.

Every fact cites the vanilla file on `P:\` it came from. Line numbers are from the copy on `P:\` when the pack was written; if a line has moved, Grep the class or key name in the same file. A note marked **engine** describes behavior that no vanilla file shows, so treat it as a rule of thumb and confirm it in game. A fact marked **Measured**, or tied to a named test build, was measured in game, in Blender or on built models and is not checked on `P:\`.

## Which file to open

| Question | File |
|---|---|
| Which vanilla class do I inherit, and which addon goes in `requiredAddons[]`? | `references/classes-and-parents.md` |
| Which slot does it use, how much does it hold, what can attach to it, what blocks it? | `references/slots-and-cargo.md` |
| How warm is it, how wet does it get, how much does it protect, how is it repaired? | `references/protection-and-insulation.md` |
| How do I make one model carry several colors, and why is my item invisible? | `references/color-variants.md` |
| Which models does a wearable need, how do proxies work, what goes to Object Builder? | `references/models-and-proxies.md` |
| What must the worn models look like (skeleton name, frame, weights, `model.cfg`), how do I build and check them, and why does my worn item float, explode or stay rigid? | `references/worn-models.md` |
| The worn item binds but plates sit off the body: how do I fit it in the alignment viewer or hand it to an artist as FBX? | `references/fitting-worn-models.md` |
| Can a script fit a new garment on the official rig and take its weights from the rig's body, and what did that fail on? | `references/autofit-on-official-rig.md` |
| What did DayZ 1.30 change for clothing and gear, and how do I move a 1.29 mod over? | `references/changes-in-1-30.md` |
| How do I add a new survivor character, and what does every survivor inherit from `SurvivorBase` (animation binding, skinning, surrender, sandstorm protection)? | `references/characters.md` |
| How do I rig a new body mesh to the vanilla skeleton in Blender and export it with weights? Why does it explode, face backward or render inside-out? | `references/body-rigging.md` |
| Why does a body that looks fine at rest deform under animation? What does an infected bind to? Is my mesh mirrored? | `references/canonical-bind.md` |
| How do I unwrap and bake normal and AO maps for a rigged body without noise, black blotches or dark AO? | `references/body-uv-bake.md` |
| How is the 1.30 survivor ragdoll bound, and what is in `human.ragdoll`? | `references/ragdoll.md` |
| Which LODs does a new body need, how do I model a hole one can see through, and why can size not come from a scale call? | `references/body-lods.md` |

The scripts these files name (the alignment viewer, the FBX export, the `model.cfg.template` and the offline winding gate `check_dayz_winding.py`) ship with the model tools in `skills/dayz-model-tools/`, whose `SKILL.md` says how to run each one; `/dayz-clothing` and `/dayz-characters` run the clothing and winding scripts from there. Infected behaviour, mind states and a custom infected's class are in `_shared/ai/custom-infected.md` and `_shared/ai/creatures.md`. On Linux, the build and tool changes are in `_shared/linux-proton.md`.

Related packs: `_shared/container-base.md` for an item with cargo that is not clothing (a vest pouch is one), and `_shared/enscript/references/item_api.md` for `ItemBase` script calls.
