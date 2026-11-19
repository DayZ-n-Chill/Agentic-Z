# Device particle integration patterns

How to start, stop and clean up particles on a modded device: a shared base class, toggles driven by the energy manager or a synced variable, one-shot sparks, and the cleanup every device needs. Which vanilla particle to pick, tuning a particle at runtime and updating older device code are in `device-particle-choices.md`.

Every class here overrides only vanilla methods or methods defined in this file, so each snippet compiles as pasted once `MyMod_DeviceBase` (Pattern A) is in the same mod. Enforce Script has no ternary operator, so the code uses if/else (`skills/_shared/enscript/patterns/language_workarounds.md`). Place the classes in `scripts/4_World/` of your mod: they extend `ItemBase`, which is a 4_World class.

## Contents

- [Pattern A: MyMod_DeviceBase with FireplaceBase-style helpers](#pattern-a-mymod_devicebase-with-fireplacebase-style-helpers)
- [Pattern B: SyncVar-driven toggle (Sprinkler example)](#pattern-b-syncvar-driven-toggle-sprinkler-example)
- [Pattern C: Overload sparks (one-shot on state change)](#pattern-c-overload-sparks-one-shot-on-state-change)
- [Pattern D: Generator/Furnace smoke (SEffectManager approach)](#pattern-d-generatorfurnace-smoke-seffectmanager-approach)
- [Pattern D with a synced bool instead of the energy manager](#pattern-d-with-a-synced-bool-instead-of-the-energy-manager)
- [Cleanup checklist (apply to every device with particles)](#cleanup-checklist-apply-to-every-device-with-particles)

## Pattern A: MyMod_DeviceBase with FireplaceBase-style helpers

Vanilla `FireplaceBase` has the cleanest particle lifecycle: a `PlayParticle` helper (`P:\scripts\4_world\entities\itembase\fireplacebase.c:1110`) and a `StopParticle` helper (`:1130`) that take the member as an `out Particle`. Put the same pair on one small base class that every device in your mod extends. Patterns B to D build on it.

```c
// The shared base for this mod's devices. Patterns B to D extend it.
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

The helpers take `out Particle particle` so that setting it to null in the stop method clears the caller's member, exactly as vanilla `StopParticle` does. That prevents double-stop bugs.

## Pattern B: SyncVar-driven toggle (Sprinkler example)

The server decides the active state; clients react in the vanilla `OnVariablesSynchronized()` (`P:\scripts\3_game\entities\entityai.c:3069`). The state is a net-synced bool registered in the constructor with `RegisterNetSyncVariableBool` (`:2832`) and pushed with `SetSynchDirty()` (`:3064`).

The device needs an `EnergyManager` class in its `config.cpp` so the energy manager calls `OnWorkStart()` (`entityai.c:3428`) and `OnWorkStop()` (`:3434`). The manager calls `OnWorkStop` once when the device stops being powered, which covers both switching off and cut wires (`P:\scripts\3_game\tools\component\componentenergymanager.c:1841`).

```c
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

`ItemBase` already overrides `EEDelete` (`P:\scripts\4_world\entities\itembase.c:1268`) and `OnVariablesSynchronized` (`:3258`), so always call `super`.

## Pattern C: Overload sparks (one-shot on state change)

When a device enters overload, fire a brief spark effect. Sparks are non-looping (`Repeat 0` at `P:\graphics\particles\electro_shortc2.ptc:51`): they play once and delete themselves, so there is nothing to store or clean up. Vanilla barbed wire plays them the same way, with `PlayOnObject` (`P:\scripts\4_world\entities\itembase\barbedwire.c:260`).

```c
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

Only looping particles need a stored reference, `Stop()` and a null. One-shots (sparks, explosions) clean themselves up.

## Pattern D: Generator/Furnace smoke (SEffectManager approach)

This follows vanilla `PowerGeneratorBase`: an `EffectParticle` subclass that sets its particle ID (`EffGeneratorSmoke`, `P:\scripts\3_game\effects\effectparticle\generatorsmoke.c:5`), started with `SEffectManager.PlayOnObject` (`P:\scripts\4_world\entities\itembase\powergenerator.c:99`), destroyed in `OnWorkStop` with `SEffectManager.DestroyEffect` (`:203`) and again in the destructor (`:38`). Use it when you want the `Effect` wrapper, a particle and a sound in one object. Like Pattern B, the device needs an `EnergyManager` class in `config.cpp`.

The energy manager runs `OnWorkStart` and `OnWorkStop` on clients too, so vanilla plays the smoke there behind `g_Game.IsClient() || !g_Game.IsMultiplayer()` (`powergenerator.c:196`). This pattern keeps the vanilla structure but uses the same `GetGame().IsHeadlessOrDedicatedServer()` gate as Patterns A to C and vanilla `ParticleManager.GetInstance()` (`P:\scripts\3_game\particles\particlemanager\particlemanager.c:65`), so one client-only check covers every pattern.

```c
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

Clean up with `SEffectManager.DestroyEffect()`, not `delete m_SmokeEffect`: it deletes the effect only when `CanDestroy()` allows and otherwise sets it to destroy itself when done (`P:\scripts\3_game\effectmanager.c:280`). Setting the member to null afterwards lets the next `OnWorkStart` create a fresh effect.

## Pattern D with a synced bool instead of the energy manager

Pattern D starts and stops its smoke in `OnWorkStart` and `OnWorkStop`, which needs an `EnergyManager` class in config. A device that is switched by its own server logic can drive the same `SEffectManager` effect from a synced bool, the way Pattern B drives a plain particle. `EffMyModSmoke` is the class defined in Pattern D.

```c
class MyMod_SyncedFurnace extends MyMod_DeviceBase
{
    // SyncVar: the server sets it, clients create or destroy the smoke.
    protected bool m_SourceOn;
    protected ref Effect m_SourceSmoke;

    void MyMod_SyncedFurnace()
    {
        m_SourceOn = false;
        RegisterNetSyncVariableBool("m_SourceOn");
    }

    void ~MyMod_SyncedFurnace()
    {
        SEffectManager.DestroyEffect(m_SourceSmoke);
    }

    // Server: call this from your own on and off logic.
    void MyMod_SetSourceOn(bool sourceOn)
    {
        if (!GetGame().IsServer())
            return;

        if (m_SourceOn != sourceOn)
        {
            m_SourceOn = sourceOn;
            SetSynchDirty();
        }
    }

    override void OnVariablesSynchronized()
    {
        super.OnVariablesSynchronized();

        if (GetGame().IsHeadlessOrDedicatedServer())
            return;

        if (m_SourceOn && !m_SourceSmoke)
        {
            m_SourceSmoke = new EffMyModSmoke();
            vector smokePos = "0.1 0.4 0.1";
            vector smokeOri = "0 0 0";
            SEffectManager.PlayOnObject(m_SourceSmoke, this, smokePos, smokeOri);
        }
        if (!m_SourceOn && m_SourceSmoke)
        {
            SEffectManager.DestroyEffect(m_SourceSmoke);
            m_SourceSmoke = null;
        }
    }
};
```

## Cleanup checklist (apply to every device with particles)

1. **OnVariablesSynchronized** (client): stop the particle when the synced state turns off.
2. **EEDelete**: stop the particle when the device leaves the world.
3. **OnWorkStop**: power is gone (switched off, wires cut, out of energy). The server clears the SyncVar (Pattern B), or the client destroys the effect directly (Pattern D).
4. **Destructor**: safety net for `SEffectManager` effects.
5. **One cleanup helper** when a device has several effects, like vanilla `StopAllParticlesAndSounds` (`P:\scripts\4_world\entities\itembase\fireplacebase.c:1039`).

### Template for multi-effect cleanup

Vanilla stops a looping sound with `StopSoundSet` (`P:\scripts\3_game\entities\object.c:1314`), as the fireplace does in `StopAllParticlesAndSounds`.

```c
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
