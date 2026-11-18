# State machine matrix: structural check

Catches illegal transitions, state that is counted twice, and "should never happen" branches that can in fact happen. Open this in step 1 for any mod that keeps a state per container or per entity, and again after every change to that state machine.

The state names and transition functions are from the virtual storage example (third-party mod); replace them with the audited mod's own. The search lines in the code blocks are recipes for the agent's search tool.

## Procedure

### Step 1: list every state

Read the state enum or constant table. Build the column headers:

```
states = [IDLE, VIRTUALIZING, VIRTUALIZED, RESTORING, RESTORED, QUARANTINE, QUARANTINE_ORPHANED]
```

Adapt to your project's actual state names.

### Step 2: list every transition function

```text
Grep "SetState|TransitionTo|m_State\s*=" --type c --output_mode content -n true
```

For each call site, record (from_state, to_state, function, conditions).

### Step 3: build the matrix

Rows are the from_state, columns the to_state, cells the list of functions that perform that transition. `QO` is `QUARANTINE_ORPHANED`.

|  | IDLE | VIRTUALIZING | VIRTUALIZED | RESTORING | RESTORED | QUARANTINE | QO |
|---|---|---|---|---|---|---|---|
| IDLE | - | StartVirt | - | - | - | OnLoadCorrupt | OnLoadOrphan |
| VIRTUALIZING | OnVirtCancel | - | OnVirtComplete | - | - | OnVirtFail | - |
| VIRTUALIZED | - | - | - | StartRestore | - | OnVerifyFail | - |
| RESTORING | - | - | - | - | OnRestoreComplete | OnRestoreFail | - |
| RESTORED | OnRestoredAck | - | - | - | - | - | - |
| QUARANTINE | OnAdminRecover | - | - | - | - | - | - |
| QO | OnAdminRecover | - | - | - | - | - | - |

### Step 4: validate

For each cell:

- **Empty**: the transition should not happen. Confirm no code path performs it. Search for `m_State = TARGET` and verify that every site is covered by a transition function in the matrix.
- **Multiple functions**: audit each individually. Several functions performing the same transition is a smell; they should converge to one.
- **One function**: the canonical case. Confirm the function's preconditions match the spec.

### Step 5: identify illegal transitions

Diagonal cells (state X to state X) should be empty unless the spec explicitly allows self-transitions. Re-entry on the same state means work overlap.

Disconnected cells: if a state has no incoming transitions, no entity ever reaches it. If it has no outgoing transitions, entities are stuck.

Both are findings.

### Step 6: validate "should never happen" branches

Search:

```text
Grep "should not happen|should never|impossible|unreachable|TODO.*remove" --type c --output_mode content -n true
```

For each comment claiming impossibility: identify the precondition that makes it impossible. If you cannot identify a precondition (and the comment is just self-assurance), treat the branch as a finding: it can happen.

## Common findings

- A state reachable only by a fail path with no recovery transition out
- Two functions performing the same transition with different preconditions (a race window where both fire)
- An EE hook that writes `m_State` without going through a transition function (bypasses validation). The EE hooks are the `EntityAI` events, for example `EEDelete` (`P:\scripts\3_game\entities\entityai.c:946`) and `EEItemAttached` (`entityai.c:1159`).
- An admin command that sets `m_State` directly, bypassing the transition functions

## Time budget

About 10 minutes for a machine of 7 states. Run it again after each state machine change.
