# PlayOnObject with the client check: a custom wreck checked against vanilla

The usual way to attach a looping particle to a placed object, shown on a custom wreck and compared with the vanilla wrecks it follows. The class in the example, `Land_Wreck_C130J`, is a mod's own class and is not on `P:\`.

## Contents

- [The pattern](#the-pattern)
- [What vanilla does](#what-vanilla-does)
- [Key points](#key-points)

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

Older mod code tests `!g_Game.IsDedicatedServer()` here. That was the vanilla check up to 1.29 (1.29, not yet checked on `P:\`). The code above uses the 1.30 check, which is what the vanilla wrecks on `P:\` use now. Keep the old form in mind only when reading 1.29 code.

## What vanilla does

The pattern is the vanilla one. `ParticleManager.GetInstance().PlayOnObject` is called this way in 23 vanilla script files, among them:

- The crashed Mi-8, with `Vector(2, 0, -5)` as the offset (`P:\scripts\4_world\entities\building\wrecks\wreck_mi8.c:8`).
- The UH-1Y wreck, with `Vector(-0.5, 0, -1.0)` (`P:\scripts\4_world\entities\building\wrecks\wreck_uh1y.c:7`).
- The Chinook wreck, which takes the offset from a memory point, `GetMemoryPointPos("emitter")`, and forces world rotation so the smoke rises straight up (`P:\scripts\4_world\entities\building\wrecks\wreck_chinook.c:8`).

Most vanilla particle code switched to the 1.30 client check:

- `IsHeadlessOrDedicatedServer` in the Mi-8 constructor (`P:\scripts\4_world\entities\building\wrecks\wreck_mi8.c:6`).
- `IsHeadlessOrDedicatedServer` in the UH-1Y constructor (`P:\scripts\4_world\entities\building\wrecks\wreck_uh1y.c:5`).
- `IsHeadlessOrDedicatedServer` in the `PlayParticle` helper of the fireplace (`P:\scripts\4_world\entities\itembase\fireplacebase.c:1112`).
- `IsHeadlessOrDedicatedServer` in the boat's effect code (`P:\scripts\4_world\entities\vehicles\boatscript.c:382`).

The Chinook and Mi-24 wrecks still use the dedicated server check alone, `!g_Game.IsDedicatedServer()` (`P:\scripts\4_world\entities\building\wrecks\wreck_chinook.c:6` and `P:\scripts\4_world\entities\building\wrecks\wreck_mi24_tk.c:5`). For particle code use `IsHeadlessOrDedicatedServer()` instead. It includes the dedicated server check that the general client-only rule in `skills/_shared/conventions/scripts.md` names, and also skips headless clients.

## Key points

- Particles are client only. The server must never call `PlayOnObject`: it draws nothing there, and on a dedicated server or a headless client `ParticleManager.GetInstance()` returns null (`P:\scripts\3_game\particles\particlemanager\particlemanager.c:65`), so the call fails on a null reference. Do not use `IsClient()` for this check: vanilla notes that `IsDedicatedServer()` is valid much sooner during load than `IsMultiplayer()`, `IsClient()` and `IsServer()` (`P:\scripts\3_game\global\game.c:1118-1125`). `IsHeadlessOrDedicatedServer()` combines `IsDedicatedServer()` with `IsHeadless()` (`P:\scripts\3_game\global\game.c:1132-1136`), so it also skips headless clients; vanilla gives no load-time note for it.
- Use the named constants of `ParticleList`, never a bare number. `SMOKING_HELI_WRECK` is registered at `P:\scripts\3_game\particles\particlelist.c:288`. There is no `ParticleList.FIRE_SMALL_CAMP`; the campfire constant is `CAMP_SMALL_FIRE` (`P:\scripts\3_game\particles\particlelist.c:29`).
- The offset vector is in the parent object's local space.
- Keep what `PlayOnObject` returns. `CrashBase` stops it in `EEDelete` with `m_ParticleEfx.Stop()`, behind the same client check (`P:\scripts\4_world\entities\building\crashbase.c:51`). A class that does not extend `CrashBase` needs its own member and its own stop.
- `script-api-reference.md` has the signatures used here, and `integration-patterns.md` has the same lifecycle for a powered device.
