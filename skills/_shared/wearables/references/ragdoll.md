# Survivor ragdoll

Covers the ragdoll that DayZ 1.30 binds on survivors as data: where it is bound, the format of `human.ragdoll`, the vanilla bone masses, and what a custom survivor or human NPC body must keep. The ragdoll calls and behaviour in play are in `_shared/physics/ragdoll-and-fall-damage.md` and `_shared/physics/player-controller.md`.

Statements about versions before 1.30 and about Workbench come from Bohemia's 1.30 modding changelog and are not checked on `P:\`, which holds 1.30.

Up to 1.29 death and unconscious physics was a native ragdoll that script only switched on and off; the call is still declared as `PhysicsSetRagdoll(bool pEnable)` (`P:\scripts\3_game\human.c:1451`). Since 1.30 survivor death physics is data: `SurvivorBase` points its `enfAnimSys` block at a `.ragdoll` file, and Workbench has a ragdoll editor for those files (changelog).

The infected block (`enfanimsys` in `ZombieBase`, `P:\DZ\characters\zombies\config.cpp:71` to `:78`) sets no `ragdoll` path. Whether the engine picks up a custom `.ragdoll` for a body that is not human is unknown; no vanilla script loads a ragdoll file.

## Where it is bound

| What | Where |
|---|---|
| `class SurvivorBase: Man` | `P:\DZ\characters\data\config.cpp:122` |
| `class enfAnimSys` inside it | `:153` |
| `ragdoll="DZ/characters/bodies/human.ragdoll";` | `:160` |

If you replace a survivor body, keep that `ragdoll` line, or point it at your own `.ragdoll` whose bone names match your `.xob`. A mesh or skeleton that does not match the ragdoll's bones shows as a broken corpse with capsules on the wrong limbs, not as a bind pose fault at idle (unverified, not tested in game).

## The `.ragdoll` format

`P:\DZ\characters\bodies\human.ragdoll` is about 200 lines of Enfusion config. The root `RagdollDef` binds an Enfusion `.xob`, then nests `RagdollBone` blocks, and the nesting is the hierarchy. Each bone has `Mass`, `Offset`, `Geometries` (`PhysicsCapsuleGeometry` or `PhysicsSphereGeometry`) and joint limits.

How the file opens (`P:\DZ\characters\bodies\human.ragdoll:1` onward):

```cpp
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

The head is a sphere, not a capsule: a `PhysicsSphereGeometry` named `Head` (`:42`). The flesh capsules use the surface `DZ/data/data/penetration/flesh.bisurf`.

## Bone masses

All in `P:\DZ\characters\bodies\human.ragdoll`; the line is the bone's `Mass` line.

| Bone | Mass | Line |
|---|---|---|
| `pelvis` | 17 | `:5` |
| `spine3` | 15 | `:23` |
| `head` | 6.1 | `:39` |
| `leftarm` | 2.1 | `:54` |
| `leftforearm` | 1.7 | `:69` |
| `rightarm` | 2.1 | `:85` |
| `rightforearm` | 1.7 | `:100` |
| `leftupleg` | 7.5 | `:118` |
| `leftleg` | 6.6 | `:134` |
| `rightupleg` | 7.5 | `:159` |
| `rightleg` | 6.6 | `:175` |

The joint fields are `JointMinLimits`, `JointMaxLimits`, `JointStiffness` (0.8 on `spine3` and `head`) and `JointDamper` (0.4 on `spine3`, 0.3 on `head` and the legs). Not every bone sets a stiffness.

The ragdoll is a separate physics asset, so never just scale these masses for a body baked oversize. A body baked at 1.2 times has its capsules in the wrong place unless you author a matching `.ragdoll`.

## Authoring a custom ragdoll

1. Every bone name in the `.ragdoll` must exist on the bound `.xob`. Vanilla binds `player_m_editorpreview.xob`, GUID `{D470A4E7581CCE23}`, at `P:\DZ\anims\workspaces\player\Models\player_m_editorpreview.xob`.
2. Keep `ragdoll = ...` on any class that inherits or replaces the `enfAnimSys` block of `SurvivorBase`.
3. Edit the `.ragdoll` in Workbench's ragdoll editor, and treat it as the source of truth for corpse capsules, not `model.cfg`.
4. A custom infected binds the 95 bone `hermit_newbindpose.xob` for animation (`canonical-bind.md`); that is a different layer from this survivor ragdoll.
