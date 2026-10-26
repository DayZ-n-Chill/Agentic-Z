# Device particle integration patterns

Complete code examples for integrating particles into modded devices. Every
class here overrides only vanilla methods or methods defined in this file, so
each snippet compiles as pasted once `MyMod_DeviceBase` (Pattern A) is in the
same mod. Enforce Script has no ternary operator, so the code uses if/else
(`skills/_shared/enscript/patterns/language_workarounds.md`).

Place the classes in `scripts/4_World/` of your mod: they extend `ItemBase`,
which is a 4_World class.

## Contents

- [Pattern A: MyMod_DeviceBase with FireplaceBase-style helpers](#pattern-a-mymod_devicebase-with-fireplacebase-style-helpers)
- [Pattern B: SyncVar-driven toggle (Sprinkler example)](#pattern-b-syncvar-driven-toggle-sprinkler-example)
- [Pattern C: Overload sparks (one-shot on state change)](#pattern-c-overload-sparks-one-shot-on-state-change)
- [Pattern D: Generator/Furnace smoke (SEffectManager approach)](#pattern-d-generatorfurnace-smoke-seffectmanager-approach)
- [Pattern E: Parameter tuning at runtime](#pattern-e-parameter-tuning-at-runtime)
- [Cleanup checklist (apply to every device with particles)](#cleanup-checklist-apply-to-every-device-with-particles)
- [Vanilla particles for placed devices](#vanilla-particles-for-placed-devices)

---

## Pattern A: MyMod_DeviceBase with FireplaceBase-style helpers

Vanilla `FireplaceBase` has the cleanest particle lifecycle: a `PlayParticle`
helper (`P:\scripts\4_world\entities\itembase\fireplacebase.c:1110`) and a
`StopParticle` helper (`P:\scripts\4_world\entities\itembase\fireplacebase.c:1130`)
that take the member as an `out Particle`. Put the same pair on one small base
class that every device in your mod extends. Patterns B to E build on it.

```
// The shared base for this mod's devices. Patterns B to E extend it.
class MyMod_DeviceBase extends ItemBase
{
    // Returns true if a particle started; false if one already exists, on a server, or with no pool.
    protected bool MyMod_PlayParticle(out Particle particle, int particleType, vector localPos)
    {
        if (particle)
            return false;

        if (GetGame().IsHeadlessOrDedicatedServer())
            return false;

        ParticleManager pm = ParticleManager.GetInstance();
        if (!pm)
            return false;

        particle = pm.PlayOnObject(particleType, this, localPos);
        if (!particle)
            return false;

        return true;
    }

    // Returns true if a particle stopped, false if there was nothing to stop.
    protected bool MyMod_StopParticle(out Particle particle)
    {
        if (!particle)
            return false;

        if (GetGame().IsHeadlessOrDedicatedServer())
            return false;

        particle.Stop();
        particle = null;
        return true;
    }
};
```

**Why `out Particle particle`?** Setting it to null in the stop method prevents
double-stop bugs. The caller's member is cleared automatically, exactly as
vanilla `StopParticle` does.

---

## Pattern B: SyncVar-driven toggle (Sprinkler example)

The server decides the active state; clients react in the vanilla
`OnVariablesSynchronized()` (`P:\scripts\3_game\entities\entityai.c:3069`).
The state is a net-synced bool registered in the constructor with
`RegisterNetSyncVariableBool` (`P:\scripts\3_game\entities\entityai.c:2832`)
and pushed with `SetSynchDirty()` (`P:\scripts\3_game\entities\entityai.c:3064`).

The device needs an `EnergyManager` class in its `config.cpp` so the energy
manager calls `OnWorkStart()` (`P:\scripts\3_game\entities\entityai.c:3428`)
and `OnWorkStop()` (`P:\scripts\3_game\entities\entityai.c:3434`). The manager
calls `OnWorkStop` once when the device stops being powered, which covers both
switching off and cut wires
(`P:\scripts\3_game\tools\component\componentenergymanager.c:1841`).

```
class MyMod_Sprinkler extends MyMod_DeviceBase
{
    // ---- SyncVar (set on the server, read on clients) ----
    protected bool m_SprinklerActive;

    // ---- Client-only particle ----
    protected Particle m_SprayEffect;

    void MyMod_Sprinkler()
    {
        m_SprinklerActive = false;
        RegisterNetSyncVariableBool("m_SprinklerActive");
    }

    // ---- Particle position relative to the device model ----
    protected vector MyMod_GetSprayPosition()
    {
        vector pos = "0 0.15 0";
        return pos;
    }

    // ---- Server: power on and power off (switch, cut wires, no energy) ----
    override void OnWorkStart()
    {
        super.OnWorkStart();
        MyMod_SetActive(true);
    }

    override void OnWorkStop()
    {
        super.OnWorkStop();
        MyMod_SetActive(false);
    }

    protected void MyMod_SetActive(bool active)
    {
        if (!GetGame().IsServer())
            return;

        if (m_SprinklerActive != active)
        {
            m_SprinklerActive = active;
            SetSynchDirty();
        }
    }

    // ---- Client: toggle the particle when the SyncVar changes ----
    override void OnVariablesSynchronized()
    {
        super.OnVariablesSynchronized();

        if (GetGame().IsHeadlessOrDedicatedServer())
            return;

        if (m_SprinklerActive && !m_SprayEffect)
        {
            // Option A: vanilla water jet as a placeholder
            int waterJet = ParticleList.WATER_JET_WEAK;
            vector sprayPos = MyMod_GetSprayPosition();
            MyMod_PlayParticle(m_SprayEffect, waterJet, sprayPos);

            // Option B: your own registered particle (once its .ptc exists)
            // int sprayId = ParticleList.MYMOD_WATER_SPRAY;
            // MyMod_PlayParticle(m_SprayEffect, sprayId, sprayPos);
        }
        if (!m_SprinklerActive && m_SprayEffect)
        {
            MyMod_StopParticle(m_SprayEffect);
        }
    }

    // ---- Cleanup: device removed from the world ----
    override void EEDelete(EntityAI parent)
    {
        // MyMod_StopParticle is a no-op on a dedicated server.
        MyMod_StopParticle(m_SprayEffect);

        super.EEDelete(parent);
    }
};
```

`ItemBase` already overrides `EEDelete` (`P:\scripts\4_world\entities\itembase.c:1268`)
and `OnVariablesSynchronized` (`P:\scripts\4_world\entities\itembase.c:3254`),
so always call `super`.

---

## Pattern C: Overload sparks (one-shot on state change)

When a device enters overload, fire a brief spark effect. Sparks are
non-looping (`Repeat 0` at `P:\graphics\particles\electro_shortc2.ptc:51`):
they play once and delete themselves, so there is nothing to store or clean
up. Vanilla barbed wire plays them the same way
(`P:\scripts\4_world\entities\itembase\barbedwire.c:260`).

```
class MyMod_OverloadDevice extends MyMod_DeviceBase
{
    // SyncVar: the server sets it, clients detect the false-to-true change.
    protected bool m_Overloaded;
    protected bool m_OverloadedPrev;

    void MyMod_OverloadDevice()
    {
        m_Overloaded = false;
        m_OverloadedPrev = false;
        RegisterNetSyncVariableBool("m_Overloaded");
    }

    // Server: call this from your overload logic.
    void MyMod_SetOverloaded(bool overloaded)
    {
        if (!GetGame().IsServer())
            return;

        if (m_Overloaded != overloaded)
        {
            m_Overloaded = overloaded;
            SetSynchDirty();
        }
    }

    override void OnVariablesSynchronized()
    {
        super.OnVariablesSynchronized();

        if (GetGame().IsHeadlessOrDedicatedServer())
            return;

        if (m_Overloaded && !m_OverloadedPrev)
        {
            ParticleManager pm = ParticleManager.GetInstance();
            if (pm)
            {
                // BARBED_WIRE_SPARKS is non-looping and deletes itself.
                int sparkId = ParticleList.BARBED_WIRE_SPARKS;
                vector sparkPos = "0 0.2 0";
                pm.PlayOnObject(sparkId, this, sparkPos);
            }
        }
        m_OverloadedPrev = m_Overloaded;
    }
};
```

**Note**: only looping particles need a stored reference, `Stop()` and a
null. One-shots (sparks, explosions) clean themselves up.

---

## Pattern D: Generator/Furnace smoke (SEffectManager approach)

This follows vanilla `PowerGeneratorBase`: an `EffectParticle` subclass that
sets its particle ID (`P:\scripts\3_game\effects\effectparticle\generatorsmoke.c:5`,
`EffGeneratorSmoke`), started with `SEffectManager.PlayOnObject`
(`P:\scripts\4_world\entities\itembase\powergenerator.c:99`), destroyed in
`OnWorkStop` with `SEffectManager.DestroyEffect` (`P:\scripts\4_world\entities\itembase\powergenerator.c:203`)
and again in the destructor (`P:\scripts\4_world\entities\itembase\powergenerator.c:38`).
The energy manager runs `OnWorkStart`/`OnWorkStop` on clients too, so vanilla
plays the smoke there behind `g_Game.IsClient() || !g_Game.IsMultiplayer()`
(`P:\scripts\4_world\entities\itembase\powergenerator.c:196`). This pattern
keeps the vanilla structure but uses the same
`GetGame().IsHeadlessOrDedicatedServer()` gate as Patterns A to C and vanilla
`ParticleManager.GetInstance()`
(`P:\scripts\3_game\particles\particlemanager\particlemanager.c:65`), so one
client-only check covers every pattern. Use this when
you want the `Effect` wrapper (particle plus sound in one object). Like
Pattern B, the device needs an `EnergyManager` class in `config.cpp`.

```
// A small Effect subclass (can be shared across devices). Place it in 3_Game or 4_World.
class EffMyModSmoke : EffectParticle
{
    void EffMyModSmoke()
    {
        SetParticleID(ParticleList.POWER_GENERATOR_SMOKE);
    }
};

class MyMod_Furnace extends MyMod_DeviceBase
{
    protected ref Effect m_SmokeEffect;

    void ~MyMod_Furnace()
    {
        SEffectManager.DestroyEffect(m_SmokeEffect);
    }

    // Smoke position and orientation relative to the model
    protected vector MyMod_GetSmokePosition()
    {
        vector pos = "0.1 0.4 0.1";
        return pos;
    }

    protected vector MyMod_GetSmokeOrientation()
    {
        vector ori = "0 0 0";
        return ori;
    }

    override void OnWorkStart()
    {
        super.OnWorkStart();

        if (GetGame().IsHeadlessOrDedicatedServer())
            return;

        if (!m_SmokeEffect)
        {
            m_SmokeEffect = new EffMyModSmoke();
            vector smokePos = MyMod_GetSmokePosition();
            vector smokeOri = MyMod_GetSmokeOrientation();
            SEffectManager.PlayOnObject(m_SmokeEffect, this, smokePos, smokeOri);
        }
    }

    override void OnWorkStop()
    {
        super.OnWorkStop();

        if (GetGame().IsHeadlessOrDedicatedServer())
            return;

        SEffectManager.DestroyEffect(m_SmokeEffect);
        m_SmokeEffect = null;
    }
};
```

**IMPORTANT**: clean up with `SEffectManager.DestroyEffect()`, not
`delete m_SmokeEffect`. It deletes the effect only when `CanDestroy()` allows
and otherwise sets it to destroy itself when done
(`P:\scripts\3_game\effectmanager.c:280`). Setting the member to null
afterwards lets the next `OnWorkStart` create a fresh effect.

---

## Pattern E: Parameter tuning at runtime

Adjust particle properties after creation, for example smoke height from the
room ceiling or spark intensity from overload severity. Vanilla tunes the
fireplace's small smoke this way:
`m_ParticleSmallSmoke.SetParameter(-1, EmitorParam.AIR_RESISTANCE, air_resistance)`
(`P:\scripts\4_world\entities\itembase\fireplacebase.c:1209`).

```
class MyMod_Chimney extends MyMod_DeviceBase
{
    protected Particle m_SmokeParticle;

    // Client: start the smoke and tune it for a low ceiling.
    protected void MyMod_StartLowSmoke()
    {
        vector smokePos = "0 0.5 0";
        MyMod_PlayParticle(m_SmokeParticle, ParticleList.CAMP_SMALL_SMOKE, smokePos);
        if (!m_SmokeParticle)
            return;

        // -1 = all emitters; more air resistance = shorter smoke column
        float airRes = 3.0;
        int emitterAll = -1;
        m_SmokeParticle.SetParameter(emitterAll, EmitorParam.AIR_RESISTANCE, airRes);

        // Scale particle size relative to the original .ptc values
        float sizeScale = 0.5;
        m_SmokeParticle.ScaleParticleParamFromOriginal(EmitorParam.SIZE, sizeScale);
    }

    override void EEDelete(EntityAI parent)
    {
        MyMod_StopParticle(m_SmokeParticle);
        super.EEDelete(parent);
    }
};
```

---

## Cleanup checklist (apply to every device with particles)

1. **OnVariablesSynchronized** (client): stop the particle when the synced state turns off.
2. **EEDelete**: stop the particle when the device leaves the world.
3. **OnWorkStop**: power is gone (switched off, wires cut, out of energy). The server clears the SyncVar (Pattern B), or the client destroys the effect directly (Pattern D).
4. **Destructor**: safety net for `SEffectManager` effects.
5. **One cleanup helper** when a device has several effects, like vanilla `StopAllParticlesAndSounds` (`P:\scripts\4_world\entities\itembase\fireplacebase.c:1039`).

### Template for multi-effect cleanup

Vanilla stops a looping sound with `StopSoundSet` (`P:\scripts\3_game\entities\object.c:1314`),
as the fireplace does in `StopAllParticlesAndSounds`.

```
class MyMod_MultiFXDevice extends MyMod_DeviceBase
{
    protected Particle m_EffectA;
    protected Particle m_EffectB;
    protected ref Effect m_EffectC;
    protected EffectSound m_LoopSound;

    protected void MyMod_CleanupClientFX()
    {
        if (GetGame().IsHeadlessOrDedicatedServer())
            return;

        MyMod_StopParticle(m_EffectA);
        MyMod_StopParticle(m_EffectB);

        // SEffectManager effect
        SEffectManager.DestroyEffect(m_EffectC);
        m_EffectC = null;

        // Looping sound
        if (m_LoopSound)
            StopSoundSet(m_LoopSound);
    }

    override void EEDelete(EntityAI parent)
    {
        MyMod_CleanupClientFX();
        super.EEDelete(parent);
    }
};
```

---

## Vanilla particles for placed devices

Every constant below is registered in `P:\scripts\3_game\particles\particlelist.c`
and points at a real `.ptc` under `P:\graphics\particles\`. Avoid
`CAMP_STEAM_EXTINGUISH_START`: it registers the placeholder `default_01`
(`P:\scripts\3_game\particles\particlelist.c:35`), not a steam effect.

"Stop it" means the effect keeps running until you stop it. Where the `.ptc`
has no `Repeat` line, the evidence is that vanilla stops it explicitly.

| Device | Particle | Constant | Stop it? |
|---|---|---|---|
| Sprinkler | Water jet (weak) | `WATER_JET_WEAK` | Yes. Vanilla stops it (`land_underground_waterreservoir.c:1168`) |
| Sprinkler alt | Water spilling | `WATER_SPILLING` | Yes. Vanilla stops it (`land_underground_waterreservoir.c:1132`) |
| Furnace | Generator smoke | `POWER_GENERATOR_SMOKE` | Yes. Vanilla destroys it in `OnWorkStop` (`powergenerator.c:203`) |
| Furnace alt | Small camp smoke | `CAMP_SMALL_SMOKE` | Yes. Vanilla stops it (`fireplacebase.c:1049`) |
| Overload | Barbed wire sparks | `BARBED_WIRE_SPARKS` | No. `Repeat 0`, deletes itself |
| Overload alt | Easter egg activate | `EASTER_EGG_ACTIVATE` | No. `Repeat 0`, deletes itself |
| Stove burner | Small stove fire | `CAMP_STOVE_FIRE` | Yes. `Repeat 1` |
| Steam vent | Smoking barrel steam | `SMOKING_BARREL_STEAM` | Yes. `Repeat 1` |
| Small steam vent | Smoking barrel steam (small) | `SMOKING_BARREL_STEAM_SMALL` | Yes. `Repeat 1` |
| Hot spring | Water vapor | `HOTPSRING_WATERVAPOR` | Yes. `Repeat 1` |
| Geyser | Geyser normal | `GEYSER_NORMAL` | Yes. `Repeat 1` |
| Menu evaporation | Main-menu evaporation | `EVAPORATION` | No. `Repeat 0`; vanilla plays it only in the menu |

Sources, one per row with a `Repeat` claim:

- `SMOKING_BARREL_STEAM` registers `smoking_barrel_steam` (`P:\scripts\3_game\particles\particlelist.c:203`), which loops (`Repeat 1` at `P:\graphics\particles\smoking_barrel_steam.ptc:47`).
- `SMOKING_BARREL_STEAM_SMALL` registers `smoking_barrel_steam_small` (`P:\scripts\3_game\particles\particlelist.c:204`), which loops (`Repeat 1` at `P:\graphics\particles\smoking_barrel_steam_small.ptc:49`).
- `CAMP_STOVE_FIRE` loops (`Repeat 1` at `P:\graphics\particles\fire_small_stove_01.ptc:51`).
- `HOTPSRING_WATERVAPOR` loops (`Repeat 1` at `P:\graphics\particles\hotspring_watervapor.ptc:107`).
- `GEYSER_NORMAL` loops (`Repeat 1` at `P:\graphics\particles\geyser_normal.ptc:31`).
- `BARBED_WIRE_SPARKS` is one-shot (`Repeat 0` at `P:\graphics\particles\electro_shortc2.ptc:51`).
- `EASTER_EGG_ACTIVATE` is one-shot (`Repeat 0` at `P:\graphics\particles\easter_egg_activate.ptc:53`).
- `EVAPORATION` is one-shot (`Repeat 0` at `P:\graphics\particles\menu_evaporation.ptc:41`) and vanilla uses it for `MenuEvaporation` (`P:\scripts\3_game\effects\effectparticle\menuevaporation.c:5`).
- `WATER_JET_WEAK` is stopped with `StopParticle` (`P:\scripts\4_world\entities\building\underground\water\land_underground_waterreservoir.c:1168`).
- `WATER_SPILLING` is stopped with `StopParticle` (`P:\scripts\4_world\entities\building\underground\water\land_underground_waterreservoir.c:1132`).
- `CAMP_SMALL_SMOKE` is stopped with `StopParticle` (`P:\scripts\4_world\entities\itembase\fireplacebase.c:1049`).
