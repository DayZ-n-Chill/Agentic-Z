# State machine table

How to find illegal transitions, state counted twice, and "should never happen" branches that can happen, by laying every transition out in one table. Run it in step 1 of `deep-audit.md` for any mod that keeps a state per container or per entity, and again after every change to that state machine.

The state names and functions come from a third-party virtual storage mod; put the audited mod's own in their place. The search lines are patterns for the agent's own search tool.

## Build the table

1. Read the state enum or constant table. These become the columns, for example `IDLE`, `VIRTUALIZING`, `VIRTUALIZED`, `RESTORING`, `RESTORED`, `QUARANTINE`, `QUARANTINE_ORPHANED`.
2. Find every place that changes the state, and record the state before, the state after, the function and its conditions:

```text
Grep "SetState|TransitionTo|m_State\s*=" --type c --output_mode content -n true
```

3. Fill the table: one row per state before, one column per state after, and the functions that make that change in the cell. `QO` stands for `QUARANTINE_ORPHANED`.

| From \ To | IDLE | VIRTUALIZING | VIRTUALIZED | RESTORING | RESTORED | QUARANTINE | QO |
|---|---|---|---|---|---|---|---|
| IDLE | - | StartVirt | - | - | - | OnLoadCorrupt | OnLoadOrphan |
| VIRTUALIZING | OnVirtCancel | - | OnVirtComplete | - | - | OnVirtFail | - |
| VIRTUALIZED | - | - | - | StartRestore | - | OnVerifyFail | - |
| RESTORING | - | - | - | - | OnRestoreComplete | OnRestoreFail | - |
| RESTORED | OnRestoredAck | - | - | - | - | - | - |
| QUARANTINE | OnAdminRecover | - | - | - | - | - | - |
| QO | OnAdminRecover | - | - | - | - | - | - |

## Read each cell

- **Empty.** The change must never happen. Confirm no code makes it: search for `m_State = <target>` and check that every hit belongs to a function in the table.
- **Several functions.** Audit each one. Several functions making the same change should become one.
- **One function.** The normal case. Confirm its conditions match the spec.

The diagonal (a state to itself) stays empty unless the spec allows it; entering the same state again means two jobs overlap. A state with no way in is never reached, and a state with no way out traps whatever enters it. Both are findings.

## Branches that "should never happen"

```text
Grep "should not happen|should never|impossible|unreachable|TODO.*remove" --type c --output_mode content -n true
```

For each comment that says a branch cannot run, name the condition that stops it. When there is none and the comment only reassures, treat the branch as a finding: it can run.

## Common findings

- A state reached only from a failure, with no way out.
- Two functions making the same change under different conditions, so both can fire in the same window.
- An engine hook that writes `m_State` without going through a transition function. The hooks are the `EntityAI` events, for example `EEDelete` (`P:\scripts\3_game\entities\entityai.c:946`) and `EEItemAttached` (`entityai.c:1159`).
- An admin command that sets `m_State` directly.

Allow about 10 minutes for a machine of seven states, and run it again after each change to the machine.
