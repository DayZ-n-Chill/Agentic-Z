# Device Particle Integration Patterns

Complete code examples for integrating particles into modded devices.
All code follows Enforce Script hard rules (no ternary, no ++, no foreach,
no string literals as params, explicit typing, m_ prefix on members).

---

## Pattern A: FireplaceBase-style helpers (RECOMMENDED)

The vanilla FireplaceBase has the cleanest particle lifecycle pattern.
Adapt it as a pair of helper methods on your device class.

```
// ---- Particle helpers (add to any modded device) ----

// Returns true if particle started, false if already exists or on server
protected bool MyMod_PlayParticle(out Particle particle, int particleType, vector localPos)
{
    if (particle)
        return false;

    if (GetGame().IsDedicatedServer())
        return false;

    ParticleManager pm = ParticleManager.GetInstance();
    if (!pm)
        return false;

    particle = pm.PlayOnObject(particleType, this, localPos);
    return true;
}

// Returns true if particle stopped, false if nothing to stop
protected bool MyMod_StopParticle(out Particle particle)
{
    if (!particle)
        return false;

    if (GetGame().IsDedicatedServer())
        return false;

    particle.Stop();
    particle = null;
    return true;
}
```

**Why `out Particle particle`?** Setting it to null in the stop method prevents
double-stop bugs. The caller's reference is cleared automatically.

---

## Pattern B: SyncVar-driven toggle (Sprinkler example)

Server decides active state. Client reacts visually in OnVarSync.

```
class MyMod_Sprinkler : MyMod_DeviceBase
{
    // ---- SyncVars ----
    protected bool m_SprinklerActive = false;

    // ---- Client-only particle ----
    protected Particle m_SprayEffect;

    // ---- Particle position relative to device model ----
    protected vector MyMod_GetSprayPosition()
    {
        string pos = "0 0.15 0";
        return pos.ToVector();
    }

    // ---- VarSync: toggle particle on client ----
    override void MyMod_OnVarSync()
    {
        #ifndef SERVER
        if (m_SprinklerActive && !m_SprayEffect)
        {
            // Option A: Use vanilla water particle as placeholder
            int waterJet = ParticleList.WATER_JET_WEAK;
            vector sprayPos = MyMod_GetSprayPosition();
            MyMod_PlayParticle(m_SprayEffect, waterJet, sprayPos);
            
            // Option B: Use custom registered particle (when .ptc exists)
            // int sprayId = ParticleList.MYMOD_WATER_SPRAY;
            // MyMod_PlayParticle(m_SprayEffect, sprayId, sprayPos);
        }
        if (!m_SprinklerActive && m_SprayEffect)
        {
            MyMod_StopParticle(m_SprayEffect);
        }
        #endif
    }

    // ---- Cleanup: device removed ----
    override void EEDelete(EntityAI parent)
    {
        #ifndef SERVER
        MyMod_StopParticle(m_SprayEffect);
        #endif

        super.EEDelete(parent);
    }

    // ---- Cleanup: wires cut ----
    override void MyMod_OnPowerCut()
    {
        #ifdef SERVER
        if (m_SprinklerActive)
        {
            m_SprinklerActive = false;
            SetSynchDirty();
        }
        #endif
    }
};
```

---

## Pattern C: Overload sparks (one-shot on state change)

When a device enters overload, fire a brief spark effect. Sparks are
non-looping — they play once and auto-delete. No cleanup needed.

```
class MyMod_SomeDevice : MyMod_DeviceBase
{
    protected bool m_Overloaded = false;
    protected bool m_OverloadedPrev = false;

    override void MyMod_OnVarSync()
    {
        #ifndef SERVER
        // Detect transition to overloaded
        if (m_Overloaded && !m_OverloadedPrev)
        {
            // BARBED_WIRE_SPARKS is non-looping, auto-deletes
            int sparkId = ParticleList.BARBED_WIRE_SPARKS;
            vector sparkPos = "0 0.2 0";
            Particle.PlayOnObject(sparkId, this, sparkPos);
        }
        m_OverloadedPrev = m_Overloaded;
        #endif
    }
};
```

**Note**: For non-looping particles (sparks, explosions), you do NOT need to
store the reference or clean up. The Particle auto-deletes when finished.
Only looping particles require explicit Stop + null.

---

## Pattern D: Generator/Furnace smoke (SEffectManager approach)

This mirrors vanilla PowerGenerator exactly. Use when you want
the Effect wrapper (combines particle + future sound in one object).

```
// Need a simple Effect subclass (can be shared across devices)
class EffMyModSmoke : EffectParticle
{
    void EffMyModSmoke()
    {
        SetParticleID(ParticleList.POWER_GENERATOR_SMOKE);
    }
};

class MyMod_Furnace : MyMod_DeviceBase
{
    protected bool m_SourceOn = false;
    protected ref Effect m_SmokeEffect;

    // Smoke position relative to model
    protected vector MyMod_GetSmokePosition()
    {
        string pos = "0.1 0.4 0.1";
        return pos.ToVector();
    }

    protected vector MyMod_GetSmokeOrientation()
    {
        string ori = "0 0 0";
        return ori.ToVector();
    }

    override void MyMod_OnVarSync()
    {
        #ifndef SERVER
        if (m_SourceOn && !m_SmokeEffect)
        {
            m_SmokeEffect = new EffMyModSmoke();
            vector smokePos = MyMod_GetSmokePosition();
            vector smokeOri = MyMod_GetSmokeOrientation();
            SEffectManager.PlayOnObject(m_SmokeEffect, this, smokePos, smokeOri);
        }
        if (!m_SourceOn && m_SmokeEffect)
        {
            SEffectManager.DestroyEffect(m_SmokeEffect);
        }
        #endif
    }

    void ~MyMod_Furnace()
    {
        SEffectManager.DestroyEffect(m_SmokeEffect);
    }
};
```

**IMPORTANT**: Use `SEffectManager.DestroyEffect()` for cleanup, NOT
`delete m_SmokeEffect`. The manager handles cleanup order correctly.

---

## Pattern E: Parameter tuning at runtime

Adjust particle properties after creation (e.g. smoke height based on
room ceiling, or spark intensity based on overload severity).

```
// After creating smoke, adjust air resistance based on ceiling
MyMod_PlayParticle(m_SmokeEffect, ParticleList.CAMP_SMALL_SMOKE, smokePos);
if (m_SmokeEffect)
{
    // -1 = all emitters, higher value = more air resistance = shorter smoke column
    float airRes = 3.0;
    int emitterAll = -1;
    m_SmokeEffect.SetParameter(emitterAll, EmitorParam.AIR_RESISTANCE, airRes);
}

// Scale particle size (relative to original .ptc values)
if (m_SmokeEffect)
{
    float sizeScale = 0.5;  // half size
    m_SmokeEffect.ScaleParticleParamFromOriginal(EmitorParam.SIZE, sizeScale);
}
```

---

## Cleanup Checklist (apply to EVERY device with particles)

1. **MyMod_OnVarSync** — stop particle when powered off
2. **EEDelete** — stop particle when device removed from world
3. **MyMod_OnPowerCut** — server sets state to off, triggering VarSync cleanup
4. **Destructor** — safety net (SEffectManager pattern) or null check
5. **StopAllParticlesAndSounds** equivalent — if device has multiple effects,
   create a helper that stops all of them (see FireplaceBase.StopAllParticlesAndSounds)

### Template for multi-effect cleanup
```
protected void MyMod_CleanupClientFX()
{
    #ifndef SERVER
    MyMod_StopParticle(m_EffectA);
    MyMod_StopParticle(m_EffectB);
    // SEffectManager effects:
    SEffectManager.DestroyEffect(m_EffectC);
    // Sound:
    if (m_LoopSound)
    {
        m_LoopSound.SoundStop();
        m_LoopSound = null;
    }
    #endif
}
```

---

## Vanilla Particles Recommended for a placed-device mod Devices

| Device | Recommended particle | Constant | Looping? |
|---|---|---|---|
| Sprinkler | Water jet (weak) | `WATER_JET_WEAK` | Yes — must stop |
| Sprinkler alt | Water spilling | `WATER_SPILLING` | Yes — must stop |
| Furnace | Generator smoke | `POWER_GENERATOR_SMOKE` | Yes — must stop |
| Furnace alt | Small camp smoke | `CAMP_SMALL_SMOKE` | Yes — must stop |
| Overload | Barbed wire sparks | `BARBED_WIRE_SPARKS` | No — auto-deletes |
| Overload alt | Easter egg activate | `EASTER_EGG_ACTIVATE` | No — auto-deletes |
| Stove burner | Small stove fire | `CAMP_STOVE_FIRE` | Yes — must stop |
| Steam vent | Steam extinguish | `CAMP_STEAM_EXTINGUISH_START` | TBD — test |
| Hot spring | Water vapor | `HOTPSRING_WATERVAPOR` | Yes — must stop |
| Geyser | Geyser normal | `GEYSER_NORMAL` | Yes — must stop |
| Searchlight dust | Evaporation | `EVAPORATION` | Yes — must stop |
