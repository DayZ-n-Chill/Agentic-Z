# PlayOnObject with the client check: a community pattern checked against vanilla

The usual way to attach a looping particle to a placed object, as posted in a community thread, compared with the vanilla wrecks it copies. The thread is from the DayZ Modders Discord, read through AnswerOverflow on 2026-05-17 (https://www.answeroverflow.com/m/1504612151212511303). The class in it, `Land_Wreck_C130J`, is the poster's own and is not on `P:\`.

## Contents

- [The pattern](#the-pattern)
- [What vanilla does](#what-vanilla-does)
- [Key points](#key-points)
- [How much the thread adds](#how-much-the-thread-adds)

---

## The pattern

A wreck that smokes: the constructor plays a looping particle on the object and stores it in the `m_ParticleEfx` member that `CrashBase` declares (`P:\scripts\4_world\entities\building\crashbase.c:3`).

```
class Land_Wreck_C130J extends CrashBase
{
    void Land_Wreck_C130J()
    {
        if (!g_Game.IsHeadlessOrDedicatedServer())
        {
            m_ParticleEfx = ParticleManager.GetInstance().PlayOnObject(
                ParticleList.SMOKING_HELI_WRECK,
                this,
                Vector(-3.51846, -2.09741, -5.57666)   // offset from the object's origin, in its local space
            );
        }
    }
}
```

The thread's snippet tested `!g_Game.IsDedicatedServer()`. That was the vanilla check up to 1.29 (1.29, not yet checked on `P:\`). The code above uses the 1.30 check, which is what the vanilla wrecks on `P:\` use now. Keep the old form in mind only when reading 1.29 code.

## What vanilla does

The thread's pattern is the vanilla one. `ParticleManager.GetInstance().PlayOnObject` is called this way in 23 vanilla script files, among them:

- The crashed Mi-8, with `Vector(2, 0, -5)` as the offset (`P:\scripts\4_world\entities\building\wrecks\wreck_mi8.c:8`).
- The UH-1Y wreck, with `Vector(-0.5, 0, -1.0)` (`P:\scripts\4_world\entities\building\wrecks\wreck_uh1y.c:7`).
- The Chinook wreck, which takes the offset from a memory point, `GetMemoryPointPos("emitter")`, and forces world rotation so the smoke rises straight up (`P:\scripts\4_world\entities\building\wrecks\wreck_chinook.c:8`).

The 1.30 client check sits in front of each of them:

- `IsHeadlessOrDedicatedServer` in the Mi-8 constructor (`P:\scripts\4_world\entities\building\wrecks\wreck_mi8.c:6`).
- `IsHeadlessOrDedicatedServer` in the UH-1Y constructor (`P:\scripts\4_world\entities\building\wrecks\wreck_uh1y.c:5`).
- `IsHeadlessOrDedicatedServer` in the `PlayParticle` helper of the fireplace (`P:\scripts\4_world\entities\itembase\fireplacebase.c:1112`).
- `IsHeadlessOrDedicatedServer` in the boat's effect code (`P:\scripts\4_world\entities\vehicles\boatscript.c:382`). An older note cited `boatscript.c:38` for this; that line is not the check.

## Key points

- Particles are client only. The server must never call `PlayOnObject`: it draws nothing there, and on a headless client it would still take objects from the particle pool. Do not use `IsClient()` for this check; it is not valid during load, while the dedicated server checks are (`skills/_shared/conventions/scripts.md`, "Client and server ownership").
- Use the named constants of `ParticleList`, never a bare number. `SMOKING_HELI_WRECK` is registered at `P:\scripts\3_game\particles\particlelist.c:288`. The thread also named `ParticleList.FIRE_SMALL_CAMP`, which does not exist; the campfire constant is `CAMP_SMALL_FIRE` (`P:\scripts\3_game\particles\particlelist.c:29`).
- The offset vector is in the parent object's local space.
- Keep what `PlayOnObject` returns. `CrashBase` stops it in `EEDelete` with `m_ParticleEfx.Stop()`, behind the same client check (`P:\scripts\4_world\entities\building\crashbase.c:51`). A class that does not extend `CrashBase` needs its own member and its own stop.

## How much the thread adds

The Discord search found four particle threads, most of them repeating vanilla patterns. This one confirms what `script-api-reference.md` and `integration-patterns.md` already say; its value is a full, working example from outside vanilla.
