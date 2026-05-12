# Reference: eRPCs and Vanilla RPC IDs

DayZ uses integer IDs to identify RPCs. Vanilla occupies the lower ID range; mods must use high custom ranges to avoid collisions.

---

## Vanilla eRPCs Enum (commonly referenced)

The engine exposes these in `ERPCs` (scripts/3_game/syncevents.c and related files). Partial listing of the most-referenced ones:

| Constant | Value | Direction | Description |
|---|---|---|---|
| `ERPCs.RPC_USER_ACTION_MESSAGE` | 13 | S→C | Display action result text |
| `ERPCs.RPC_SOUND_WAVE_EFFECT` | 35 | S→C | Play sound at position |
| `ERPCs.RPC_USER_REMOVE_FROM_BLACK_LIST` | 45 | S→C | Whitelist notification |
| `ERPCs.RPC_UPPER_ITEM_PRESENCE` | 117 | S→C | Item presence on body |
| `ERPCs.RPC_INVENTORY` | 120 | both | Inventory sync events |
| `ERPCs.RPC_CHAT` | 144 | S→C | Chat message delivery |
| `ERPCs.RPC_UPDATE_ITEM_POSITION` | 147 | S→C | Force-set item's world pos |
| `ERPCs.RPC_DAMAGE_VALUE_SYNC` | 150 | S→C | Damage zone sync |
| `ERPCs.RPC_SCRIPT_REMOTE_CALLABLE` | 20000+ | both | Community convention start |

> Full list: search your `scripts/3_Game/syncevents.c` and global `enum ERPCs` declarations.

---

## Agent IDs (eAgents)

Used with `player.GetAgents().AddAgent(eAgents.X, amount)`:

| Constant | Description |
|---|---|
| `eAgents.SALMONELLA_BACTERIA` | Salmonella food poisoning |
| `eAgents.CHOLERA_BACTERIA` | Cholera (dirty water) |
| `eAgents.BRAIN_DISEASE` | Kuru prion disease |
| `eAgents.WOUND_AGENT` | Generic wound infection |
| `eAgents.INFLUENZA_AGENT` | Common cold / flu |
| `eAgents.CHEMICAL_POISON` | Chemical poisoning |
| `eAgents.GASVIRUS` | Gas area contamination |

---

## Modifier IDs (eModifiers)

Used with `player.GetSymptomsManager().AddModifier(eModifiers.X)`:

| Constant | Description |
|---|---|
| `eModifiers.MDF_POISONED` | Poisoned status |
| `eModifiers.MDF_FOODPOISONING` | Food poisoning symptoms |
| `eModifiers.MDF_BLEEDING_SOURCE_LIGHT` | Light bleed |
| `eModifiers.MDF_BLEEDING_SOURCE_MEDIUM` | Medium bleed |
| `eModifiers.MDF_BLEEDING_SOURCE_HEAVY` | Heavy bleed |
| `eModifiers.MDF_BRAIN_DISEASE` | Kuru tremors |
| `eModifiers.MDF_COMA` | Unconscious / coma |
| `eModifiers.MDF_FRACTURE` | Broken bone |
| `eModifiers.MDF_HEAT_BUFFER` | Heat buffer active |
| `eModifiers.MDF_TUNNELVISION` | Tunnel vision PP effect |

---

## Custom RPC ID Range Convention

| Range | Owner |
|---|---|
| 0–999 | Vanilla / Engine |
| 1000–1999 | Community Framework (CF) |
| 5000–9999 | Common modding territory (widely used) |
| **10000–29999** | Safest range for new private mods |
| 30000+ | Avoid — some engine-internal ranges here |

**Always document your claimed range in your README.** Conflicts silently route the message to the wrong handler.

```c
// Example safe claim
enum MyMod_ERPCs
{
    // MyMod owns 21000–21099
    RPC_NOTIFY_PLAYER  = 21000,
    RPC_SYNC_STATS     = 21001,
    RPC_ADMIN_COMMAND  = 21002,
}
```

---

## RPC Direction Best Practice

| Pattern | Guaranteed | Notes |
|---|---|---|
| Server → specific client | `true` | Game logic always reliable |
| Server → all clients (broadcast) | `true` for logic, `false` for cosmetics | |
| Client → server | `true` | Always validate server-side |
| High-frequency cosmetics | `false` | Footstep sounds, position hints |
