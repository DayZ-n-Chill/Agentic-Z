# Reference: eRPCs, eAgents and eModifiers

The three vanilla enums mods reference most, read from the vanilla scripts. Use every value **by name**: the numbers belong to the game and can move between builds.

| Enum | File |
|---|---|
| `ERPCs` | `P:\scripts\3_game\enums\erpcs.c` |
| `eAgents` | `P:\scripts\3_game\enums\eagents.c` |
| `eModifiers` | `P:\scripts\4_world\classes\playermodifiers\emodifiers.c` |

## Contents

- [ERPCs: vanilla RPC IDs](#erpcs-vanilla-rpc-ids)
- [eAgents: disease agents](#eagents-disease-agents)
- [eModifiers: player modifiers](#emodifiers-player-modifiers)
- [Custom RPC ID ranges (community convention)](#custom-rpc-id-ranges-community-convention)
- [RPC Direction Best Practice](#rpc-direction-best-practice)

---

## ERPCs: vanilla RPC IDs

`enum ERPCs` starts with four negative markers (`PB_START = -1` to `PB_SINGLEUSE_END = -4`, `erpcs.c:3-6`), then counts up from `RPC_SYNC_ITEM_VAR = 0` (:7) to `RPC_END` (:225), which the file marks "DO NOT USE OR APPEND AFTER". Some entries sit inside `#ifdef` blocks (for example `#ifdef DIAG_DEVELOPER` at :121), so the number behind a name can differ between a retail and a diag build. That is one more reason to use names only.

A few entries, with their line in `erpcs.c`:

| Constant | Line |
|---|---|
| `ERPCs.RPC_SYNC_ITEM_VAR` | :7 |
| `ERPCs.RPC_SYNC_DISPLAY_STATUS` | :11 |
| `ERPCs.RPC_USER_ACTION_MESSAGE` | :15 |
| `ERPCs.RPC_ITEM_REPAIR` | :17 |
| `ERPCs.RPC_STAMINA` | :24 |
| `ERPCs.RPC_DAMAGE_VALUE_SYNC` | :25 |
| `ERPCs.RPC_EXPLODE_EVENT` | :33 |
| `ERPCs.RPC_CHECK_PULSE` | :35 |
| `ERPCs.RPC_SEND_NOTIFICATION` | :74 |
| `ERPCs.RPC_SOUND_HELICRASH` | :85 |
| `ERPCs.RPC_CFG_GAMEPLAY_SYNC` | :98 |
| `ERPCs.RPC_CODE_LOCK_REQUEST` | :116 |

Watch out for a second set of names: `P:\scripts\3_game\constants.c` also declares global `const int` RPC IDs with fixed values, some with the same names as `ERPCs` members, for example `const int RPC_USER_ACTION_MESSAGE = 12;` (:276) and `const int RPC_DAMAGE_VALUE_SYNC = 26;` (:289). `RPC_USER_ACTION_MESSAGE` and `ERPCs.RPC_USER_ACTION_MESSAGE` are different constants, so a sender and a receiver must use the same one.

---

## eAgents: disease agents

The full enum (`eagents.c:2-15`). Each value is one bit, and the file warns they "MUST MATCH CONFIG-SIDE AGENT CONFIGURATION" (:1).

| Constant | Value |
|---|---|
| `eAgents.CHOLERA` | 1 |
| `eAgents.INFLUENZA` | 2 |
| `eAgents.SALMONELLA` | 4 |
| `eAgents.BRAIN` | 8 |
| `eAgents.FOOD_POISON` | 16 |
| `eAgents.CHEMICAL_POISON` | 32 |
| `eAgents.WOUND_AGENT` | 64 |
| `eAgents.NERVE_AGENT` | 128 |
| `eAgents.HEAVYMETAL` | 256 |
| `eAgents.SILICOSIS` | 512 |
| `eAgents.EYES_IRRITATION` | 1024 |

Give or remove an agent with `PlayerBase.InsertAgent(int agent, float count = 1)` and `RemoveAgent(int agent_id)` (`P:\scripts\4_world\entities\manbase\playerbase.c:8115` and `:8102`); `GetAgents()` returns the bit mask the player carries (:8096).

```c
player.InsertAgent(eAgents.SALMONELLA, 100);
```

---

## eModifiers: player modifiers

`MDF_TEMPERATURE = 1` ("must start at 1"), then each entry counts up by one, ending with `COUNT` (`emodifiers.c:1-71`). The full list, in order:

`MDF_TEMPERATURE`, `MDF_BLOOD_REGEN`, `MDF_BURNING`, `MDF_HEALTH_REGEN`, `MDF_TREMOR`, `MDF_HUNGER`, `MDF_FEVER`, `MDF_COMMON_COLD`, `MDF_THIRST`, `MDF_BLEEDING`, `MDF_BLINDED`, `MDF_HEART_ATTACK`, `MDF_STUFFED`, `MDF_BONE_REGEN`, `MDF_HEALTH`, `MDF_POISONING`, `MDF_HEMOLYTIC_REACTION`, `MDF_STOMACH`, `MDF_STAMINACALC`, `MDF_IMMUNE_SYSTEM`, `MDF_INFLUENZA`, `MDF_SHOCK`, `MDF_BROKEN_LEGS`, `MDF_BROKEN_ARMS`, `MDF_CHOLERA`, `MDF_TESTING`, `MDF_SALMONELLA`, `MDF_BRAIN`, `MDF_VOMITSTUFFED`, `MDF_SALINE`, `MDF_SHOCK_DAMAGE`, `MDF_UNCONSCIOUSNESS`, `MDF_WETNESS`, `MDF_IMMUNITYBOOST`, `MDF_ANTIBIOTICS`, `MDF_TOXICITY`, `MDF_BREATH_VAPOUR`, `MDF_WOUND_INFECTION`, `MDF_WOUND_INFECTION1`, `MDF_WOUND_INFECTION2`, `MDF_DISINFECTION`, `MDF_CHARCOAL`, `MDF_MORPHINE`, `MDF_PAINKILLERS`, `MDF_EPINEPHRINE`, `MDF_HEATBUFFER`, `MDF_FATIGUE`, `MDF_CONTAMINATION1`, `MDF_CONTAMINATION2`, `MDF_CONTAMINATION3`, `MDF_AREAEXPOSURE`, `MDF_MASK`, `MDF_FLIES`, `MDF_DROWNING`, `MDF_HEAVYMETAL1`, `MDF_HEAVYMETAL2`, `MDF_HEAVYMETAL3`, `MDF_PNEUMONIA`, `MDF_CHELATION`, `MDF_SANDSTORM_EXPOSURE_STATIC`, `MDF_SANDSTORM_EXPOSURE_DYNAMIC`, `MDF_PARTICLES_BREATH`, `MDF_PARTICLES_EYES`, `MDF_HEAT_STROKE1`, `MDF_HEAT_STROKE2`, `MDF_HEAT_STROKE3`, `MDF_HEAT_STROKE4`.

Food poisoning is `MDF_POISONING` (there is no `MDF_FOODPOISONING`), the brain disease is `MDF_BRAIN`, and bleeding is a single `MDF_BLEEDING`.

Turn a modifier on and off through the player's modifiers manager, as vanilla does for broken legs (`P:\scripts\4_world\classes\playermodifiers\modifiers\conditions\brokenlegs.c:81`):

```c
player.GetModifiersManager().ActivateModifier(eModifiers.MDF_BROKEN_LEGS);
player.GetModifiersManager().DeactivateModifier(eModifiers.MDF_BROKEN_LEGS);
bool on = player.GetModifiersManager().IsModifierActive(eModifiers.MDF_BROKEN_LEGS);
```

`ActivateModifier(int modifier_id, bool triggerEvent = ...)`, `DeactivateModifier(int modifier_id, bool triggerEvent = true)` and `IsModifierActive(eModifiers modifier_id)` are at `P:\scripts\4_world\classes\playermodifiers\modifiersmanager.c:227`, `:232` and `:207`. To add a modifier of your own, see `../examples/07_agent_modifier.c`.

---

## Custom RPC ID ranges (community convention)

Vanilla does not reserve any range for mods; this table is a community convention with no vanilla source. Vanilla `ERPCs` ends a little under 200 on this build (see above). CF sends all its RPCs on one ID, `FRAMEWORK_RPC_ID = 10042` (`3_Game\CommunityFramework\RPC\RPCManager.c:47` inside `P:\Mods\@CF\Addons\scripts.pbo`).

| Range | Typical use |
|---|---|
| 0 to about 250 | Vanilla `ERPCs` and the `constants.c` RPC IDs |
| 10000 to 29999 | A common choice for new private mods |
| A large random base (for example 25416533) | Strongest isolation from other mods |

**Always document your claimed range in your README.** Conflicts silently route the message to the wrong handler.

```c
// Example claim
enum MyMod_ERPCs
{
    // MyMod owns 21000 to 21099
    RPC_NOTIFY_PLAYER  = 21000,
    RPC_SYNC_STATS     = 21001,
    RPC_ADMIN_COMMAND  = 21002,
}
```

Avoid 10042 if CF is loaded.

---

## RPC Direction Best Practice

| Pattern | Guaranteed | Notes |
|---|---|---|
| Server → specific client | `true` | Game logic always reliable |
| Server → all clients (broadcast) | `true` for logic, `false` for cosmetics | |
| Client → server | `true` | Always validate server-side |
| High-frequency cosmetics | `false` | Footstep sounds, position hints |

The `guaranteed` flag is the fourth parameter of `RPCSingleParam` and `RPC` (`P:\scripts\3_game\global\game.c:1013` and `:1011`) and the third of `ScriptRPC.Send` (`P:\scripts\3_game\gameplay.c:117`).
