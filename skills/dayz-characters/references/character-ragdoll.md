# Character ragdoll (DayZ 1.30)

Covers the data-driven ragdoll that 1.30 binds on survivors: where it is bound, the format of `human.ragdoll`, the vanilla bone masses, and what a custom survivor body must keep.

How to read the marks: every `P:\` line below was opened and checked. Statements about versions before 1.30 and about Workbench come from Bohemia's 1.30 experimental modding changelog and cannot be checked on `P:\`, which holds 1.30.

Up to 1.29, player death and unconscious physics was a native ragdoll that script only switched on and off; the call is still declared as `PhysicsSetRagdoll(bool pEnable)` (`P:\scripts\3_game\human.c:1451`). Since 1.30, survivor death physics is data: `SurvivorBase` points its `enfAnimSys` block at a `.ragdoll` file, and Workbench ships a ragdoll editor for those files (changelog).

**Who this is for:** anyone authoring a custom survivor or human NPC body, or replacing the `SurvivorBase` mesh or skeleton. The infected block (`enfanimsys` in `ZombieBase`, `P:\DZ\characters\zombies\config.cpp:71` to `:78`) sets no `ragdoll` path. Whether a custom `.ragdoll` for a body that is not human is picked up by name is unverified; vanilla script has no call that loads a ragdoll file.

## Binding on SurvivorBase

| What | Where |
|---|---|
| `class SurvivorBase: Man` | `P:\DZ\characters\data\config.cpp:122` |
| `class enfAnimSys` inside it | `P:\DZ\characters\data\config.cpp:153` |
| `ragdoll="DZ/characters/bodies/human.ragdoll";` | `P:\DZ\characters\data\config.cpp:160` |

If you replace a survivor body, keep that `ragdoll` line, or point it at your own `.ragdoll` whose bone names match your `.xob`. Design note: a mesh or skeleton that does not match the ragdoll's bone set will look like a broken corpse (capsules on the wrong limbs), not like a bind pose deformation at idle.

## Format (`RagdollDef`)

`P:\DZ\characters\bodies\human.ragdoll` is about 200 lines of Enfusion config. The root `RagdollDef` binds an Enfusion `.xob`, then nests `RagdollBone` blocks; the nesting is the hierarchy. Each bone has `Mass`, `Offset`, `Geometries` (`PhysicsCapsuleGeometry` or `PhysicsSphereGeometry`) and joint limits.

The file opens like this (`P:\DZ\characters\bodies\human.ragdoll:1` onward):

```
RagdollDef {
 Object "{D470A4E7581CCE23}DZ/anims/workspaces/player/Models/player_m_editorpreview.xob"
 {
  RagdollBone pelvis {
   Mass 17
   Offset -0.008 -0.011 0
   Geometries {
    PhysicsCapsuleGeometry Spine1 {
     SurfaceProperties "DZ/data/data/penetration/flesh.bisurf"
     Offset 0 0.914 0.015
     Orientation 0 0 90
     Radius 0.1
     Height 0.2
    }
    PhysicsCapsuleGeometry Spine2 {
     Offset 0 1.061 0
     Radius 0.1
     Height 0.1
    }
   }
   {
    RagdollBone spine3 {
     Mass 15
```

The head uses a sphere, not a capsule: `PhysicsSphereGeometry` named `Head` at `P:\DZ\characters\bodies\human.ragdoll:42`. The surface on the flesh capsules is `DZ/data/data/penetration/flesh.bisurf`.

## The eleven `RagdollBone` masses (vanilla human)

All in `P:\DZ\characters\bodies\human.ragdoll`; the line is the bone's `Mass` line.

| Bone | Mass | Line |
|---|---|---|
| pelvis | 17 | `P:\DZ\characters\bodies\human.ragdoll:5` |
| spine3 | 15 | `P:\DZ\characters\bodies\human.ragdoll:23` |
| head | 6.1 | `P:\DZ\characters\bodies\human.ragdoll:39` |
| leftarm | 2.1 | `P:\DZ\characters\bodies\human.ragdoll:54` |
| leftforearm | 1.7 | `P:\DZ\characters\bodies\human.ragdoll:69` |
| rightarm | 2.1 | `P:\DZ\characters\bodies\human.ragdoll:85` |
| rightforearm | 1.7 | `P:\DZ\characters\bodies\human.ragdoll:100` |
| leftupleg | 7.5 | `P:\DZ\characters\bodies\human.ragdoll:118` |
| leftleg | 6.6 | `P:\DZ\characters\bodies\human.ragdoll:134` |
| rightupleg | 7.5 | `P:\DZ\characters\bodies\human.ragdoll:159` |
| rightleg | 6.6 | `P:\DZ\characters\bodies\human.ragdoll:175` |

Joint fields used: `JointMinLimits`, `JointMaxLimits`, `JointStiffness` (0.8 on spine3 and head) and `JointDamper` (0.4 on spine3, 0.3 on head and the legs). Not every bone sets a stiffness.

Design note: do not scale these masses with a character mesh baked oversize. The ragdoll is a separate physics asset. If you bake a body at 1.2 times, the capsules sit wrong unless you author a matching `.ragdoll`.

## Authoring checklist

1. Bone names in the `.ragdoll` must exist on the bound `.xob`. Vanilla binds `player_m_editorpreview.xob`, GUID `{D470A4E7581CCE23}`; the file is at `P:\DZ\anims\workspaces\player\Models\player_m_editorpreview.xob`.
2. Keep `ragdoll = ...` on any class that inherits or replaces the `enfAnimSys` block of `SurvivorBase`.
3. Edit the `.ragdoll` in Workbench's ragdoll editor. Treat that file as the source of truth for corpse capsules, not `model.cfg`.
4. Custom infected still use the 95-bone `hermit_newbindpose.xob` bind for animation (`references/canonical-bind.md`); that is a different layer from this survivor ragdoll.
