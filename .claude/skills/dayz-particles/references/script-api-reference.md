# Script API Reference — Particle System

All signatures verified from vanilla source (Particle.c, ParticleSource.c,
ParticleManager.c, ParticleBase.c). Inheritance: ParticleBase → Particle → ParticleSource.

---

## CLASS HIERARCHY

```
Entity
 └─ ParticleBase          (abstract base, events, IsParticle)
     └─ Particle           (legacy, EOnFrame lifetime, #particlesourceenf child)
         └─ ParticleSource  (native C++ backed, no EOnFrame, proto methods)

ParticleManager (Managed)  — pool of ParticleSource, singleton
SEffectManager (static)    — wraps Effect objects (particle+sound combos)
```

---

## Particle (legacy) — Static Factory Methods

```
// Create without playing
static Particle CreateOnObject(int particle_id, Object parent_obj,
    vector local_pos = "0 0 0", vector local_ori = "0 0 0",
    bool force_world_rotation = false);

static Particle CreateInWorld(int particle_id, vector global_pos,
    vector global_ori = "0 0 0", bool force_world_rotation = false);

// Create AND play immediately
static Particle PlayOnObject(int particle_id, Object parent_obj,
    vector local_pos = "0 0 0", vector local_ori = "0 0 0",
    bool force_world_rotation = false);

static Particle PlayInWorld(int particle_id, vector global_pos);

// Legacy aliases (backwards compat)
static Particle Play(int particle_id, Object parent_obj, vector local_pos, vector local_ori);
static Particle Play(int particle_id, vector global_pos, vector global_ori);
static Particle Create(int particle_id, Object parent_obj, vector local_pos, vector local_ori);
static Particle Create(int particle_id, vector global_pos, vector global_ori);
```

## Particle — Instance Methods

```
// Playback
void PlayParticle(int particle_id = -1);
bool PlayParticleEx(int particle_id = -1, int flags = 0);
bool StopParticle(int flags = 0);
void Stop();                              // legacy alias
void Play(int particle_id = -1);          // legacy alias

// State
bool IsParticlePlaying();                 // from ParticleBase
bool HasActiveParticle();
int GetParticleCount();
bool IsRepeat();
float GetMaxLifetime();

// Properties
void SetSource(int particle_id);          // set ID (does NOT change live particle)
int GetParticleID();
Object GetDirectParticleEffect();         // child #particlesourceenf entity
Object GetParticleParent();

// Parenting
void AddAsChild(Object parent, vector local_pos = "0 0 0",
    vector local_ori = "0 0 0", bool force_rotation_to_world = false);

// Parameter tuning
void SetParticleParam(int parameter_id, float value);             // all emitters
void SetParameter(int emitter, int parameter, float value);       // -1=all
void GetParameter(int emitter, int parameter, out float value);
float GetParameterEx(int emitter, int parameter);
float GetParameterOriginal(int emitter, int parameter);
void ScaleParticleParamFromOriginal(int parameter_id, float coef);
void ScaleParticleParam(int parameter_id, float coef);
void IncrementParticleParamFromOriginal(int parameter_id, float value);
void IncrementParticleParam(int parameter_id, float value);

// Wiggle API
void SetWiggle(float random_angle, float random_interval);
void StopWiggle();
bool IsWiggling();
```

---

## ParticleSource — Additional/Override Methods

```
// Static factory (preferred over Particle statics for new code)
static ParticleSource CreateParticle(int id, vector pos,
    bool playOnCreation = false, Object parent = null,
    vector ori = vector.Zero, bool forceWorldRotation = false,
    Class owner = null);

static ParticleSource CreateParticleEx(int id, vector pos,
    int flags = ParticlePropertiesFlags.NONE, Object parent = null,
    vector ori = vector.Zero, Class owner = null);

// Playback (native C++ backed — faster than Particle)
override bool PlayParticleEx(int particle_id = -1, int flags = 0);
override bool StopParticle(int flags = 0);   // flags: StopParticleFlags enum
override bool ResetParticle();
override bool RestartParticle();              // reset + play
override bool IsParticlePlaying();

// Auto-destroy control
void SetParticleAutoDestroyFlags(ParticleAutoDestroyFlags flags);
void DisableAutoDestroy();                    // alias for flags=NONE
int GetParticleAutoDestroyFlags();

// Particle assignment
bool SetParticleByID(int id);
override void SetSource(int particle_id);     // calls SetParticleByID
bool GetParticle(out string path, EGetParticleMode mode);
override int GetParticleID();
```

## ParticleSource Enums

```
enum ParticleAutoDestroyFlags {
    NONE,       // no auto destroy — must ObjectDelete manually
    ON_END,     // destroy when particle ends (looping=never)
    ON_STOP,    // destroy when stopped
    ALL         // ON_END | ON_STOP (DEFAULT)
};

enum StopParticleFlags {
    NONE,       // = 0; no-op flag value. The default StopParticle() behavior
                // (called with no flags or NONE) IS gradual fade — but that's
                // the default mode, not something the NONE flag activates.
    RESET,      // reset state after stopping
    IMMEDIATE,  // stop NOW, clear VISIBLE flag
    VISIBLE,    // keep visible (use with IMMEDIATE for PAUSE)
    PAUSE       // IMMEDIATE|VISIBLE — freeze visible
};

enum ParticlePropertiesFlags {
    NONE,
    PLAY_ON_CREATION,    // auto-play after create
    FORCE_WORLD_ROT,     // orientation in world space not parent
    KEEP_PARENT_ON_END   // don't unparent when particle ends
};

enum EGetParticleMode {
    FULL,    // "graphics/particles/name.ptc"
    NO_EXT,  // "graphics/particles/name"
    FILE     // "name"
};
```

---

## ParticleManager — Pool Management

```
// Singleton access (returns null on dedicated server!)
static ParticleManager GetInstance();
static void CleanupInstance();

// Create (mirrors Particle/ParticleSource statics)
ParticleSource CreateParticle(int id, vector pos,
    bool playOnCreation = false, Object parent = null,
    vector ori = vector.Zero, bool forceWorldRotation = false,
    Class owner = null);

ParticleSource CreateOnObject(int particle_id, Object parent_obj,
    vector local_pos = "0 0 0", vector local_ori = "0 0 0",
    bool force_world_rotation = false);

ParticleSource CreateInWorld(int particle_id, vector global_pos,
    vector global_ori = "0 0 0", bool force_world_rotation = false);

// Play (create+play in one call)
ParticleSource PlayOnObject(int particle_id, Object parent_obj,
    vector local_pos = "0 0 0", vector local_ori = "0 0 0",
    bool force_world_rotation = false);

ParticleSource PlayInWorld(int particle_id, vector global_pos);

// Batch operations (native)
proto native int CreateParticles(out array<ParticleSource> particles,
    string path, notnull array<ref ParticleProperties> properties, int count);
proto native int PlayParticles(out array<ParticleSource> particles,
    string path, notnull array<vector> positions, int count);

// Pool info
proto native int GetPoolSize();
proto native int GetAllocatedCount();
proto native int GetVirtualCount();
proto native int GetPlayingCount();
proto native bool IsFinishedAllocating();

// Direct access
proto native ParticleSource GetParticle(int index);
proto native int GetParticles(out array<ParticleSource> outArray, int startIndex, int count);
```

---

## ParticleList — Registration & Lookup

```
// Register from mod (3_Game layer)
// modded class ParticleList { static const int MY_ID = RegisterParticle("path/", "name"); }
static int RegisterParticle(string file_name);                    // uses default path
static int RegisterParticle(string root_path, string file_name);  // custom path

// Lookup
static string GetParticlePath(int particle_id);       // without .ptc suffix
static string GetParticleFullPath(int particle_id);    // with .ptc suffix
static int GetParticleID(string particle_file);        // by path (without .ptc)
static int GetParticleIDByName(string name);           // by filename only
static bool IsValidId(int id);                         // != NONE && != INVALID
static string GetPathToParticles();                    // "graphics/particles/"
static void PreloadParticles();                        // client-side preload

// Constants
static const int INVALID = -1;
static const int NONE = 0;
```

---

## ParticleEvents — Event System

```
class ParticleEvents {
    ref ScriptInvoker Event_OnParticleStart;     // particle begins playing
    ref ScriptInvoker Event_OnParticleStop;      // particle stops (or lifetime over)
    ref ScriptInvoker Event_OnParticleReset;     // particle reset (ParticleSource only)
    ref ScriptInvoker Event_OnParticleEnd;       // particle fully ended (no active emitters)
    ref ScriptInvoker Event_OnParticleParented;  // received parent (ParticleSource only)
    ref ScriptInvoker Event_OnParticleUnParented; // lost parent (ParticleSource only)
};

// Usage:
ParticleSource ps = ...;
ps.GetEvents().Event_OnParticleEnd.Insert(MyCallback);
// void MyCallback(ParticleBase psrc) { ... }
```

---

## FireplaceBase Pattern (recommended for placed devices)

Vanilla FireplaceBase helper methods — the gold standard for particle lifecycle:

```
// Play: creates particle if not already playing, returns success
protected bool PlayParticle(out Particle particle, int particle_type, vector pos, bool worldpos = false)
{
    if (!particle && GetGame() && (!GetGame().IsDedicatedServer()))
    {
        if (!worldpos)
            particle = ParticleManager.GetInstance().PlayOnObject(particle_type, this, pos);
        else
            particle = ParticleManager.GetInstance().PlayInWorld(particle_type, pos);
        return true;
    }
    return false;
}

// Stop: stops and nulls reference, returns success
protected bool StopParticle(out Particle particle)
{
    if (particle && GetGame() && (!GetGame().IsDedicatedServer()))
    {
        particle.Stop();
        particle = NULL;
        return true;
    }
    return false;
}
```

Key insight: `out Particle particle` ensures the caller's reference is nulled,
preventing double-stop bugs.
