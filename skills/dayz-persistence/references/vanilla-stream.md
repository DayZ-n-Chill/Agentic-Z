# Vanilla entity stream contract

The rules for data saved in an entity's own `OnStoreSave` stream: write and read order, the version argument, the variable width of the base class data, and what fails. Open this when a mod saves fields on its own entity.

Line numbers are from the vanilla scripts on `P:\` (game storage version 144). A citation marked `1.29` points at the 1.29 scripts, which are not on `P:\` and were not checked there. The same holds for every statement of what 1.29 did, cited or not: not yet checked on `P:\`.

## Scope

Use this contract only when the mod owns both the data and the entity, the data is naturally part of that entity's save stream, uninstall survival is not required, and outside-game inspection is not required. Otherwise go back to the router in this skill's `SKILL.md`.

The engine hooks are `EntityAI.OnStoreSave(ParamsWriteContext)` and `EntityAI.OnStoreLoad(ParamsReadContext, int)` returning `bool` (`P:\scripts\3_game\entities\entityai.c:2910`; `entityai.c:2978`). The stream has no field names or random access: correctness is the exact sequence of typed writes and reads.

## Normative write/load order

A subclass writes in this order:

1. Call `super.OnStoreSave(ctx)` so the base class owns the prefix.
2. Write every subclass field in one declared order and with one declared type.
3. If the subclass has an independent mod schema, write its own header inside its portion of the stream; do not reinterpret the hook's storage version.

A subclass loads in this order:

1. Call `super.OnStoreLoad(ctx, version)` and return `false` if it returns `false`.
2. Read subclass fields sequentially in the exact save order and types.
3. Check the boolean result of every `ctx.Read` and return `false` on the first failure.
4. Stage values separately. Commit them to entity state only after every read and validation succeeds.

This propagation and fail-closed read behavior follows the vanilla contract at `entityai.c:2958-2974`. A load that consumed some bytes before failure is still a failed load; byte consumption does not authorize partial state.

## Version unit

The `version` argument is the game's storage version produced by `g_Game.SaveVersion()` (`P:\scripts\3_game\global\game.c:435`), which the game sets from `GAME_STORAGE_VERSION` through `StorageVersion(GAME_STORAGE_VERSION)` (`game.c:50`); it is not the game build number. Vanilla subsystems declare their own storage versions through `GetStorageVersion()` (`P:\scripts\4_world\classes\playerstomach.c:255` and `P:\scripts\4_world\classes\playermodifiers\modifiersmanager.c:178`). These build checks describe engine compatibility; they do not version a mod release. Until 1.29 `GAME_STORAGE_VERSION` was 142 (1.29 `3_game\global\game.c:5`). Since 1.30: `GAME_STORAGE_VERSION` is 144 at `game.c:5`; `SaveVersion()` is at `:435`. `PlayerStomach.OnStoreLoad` is at `playerstomach.c:471` with a `version >= 140` temperature read at `:492`. `ModifiersManager.OnStoreLoad` is at `modifiersmanager.c:273`.

## Variable-width super trap

`EntityAI.OnStoreSave` conditionally writes eight energy-component fields when `m_EM` exists and writes none when it does not (`entityai.c:2917-2948`). Therefore the base prefix width is a runtime property.

A reader that seeks to a remembered offset, skips a fixed number of fields, or assumes that `super` always consumed the energy fields is wrong. With the component absent it reads the subclass's first value as a base value and then fails or misinterprets later bytes. Let the real `super.OnStoreLoad` advance the context by the width that the matching base save wrote; begin subclass reads at the resulting sequential position.

This trap applies even when a fixture with the component present passes. Test both component-present and component-absent streams against the same reader.

Since 1.30 energy is no longer the only optional prefix. `EntityAI.OnStoreSave` calls `GetConstructionBasic().HandleStoreSave` **before** the `m_EM` block (`entityai.c:2910-2914`); `OnStoreLoad` consumes it only when `version >= 143` (`:2978-2984`). `ConstructionBasic` writes nothing (`HandleStorageEvents` returns `false` at `P:\scripts\3_game\systems\construction_basic.c:29-35`). `Rebuilding` writes eleven ints when present. `PlayerBase` then appends `ThermalBiasHandler` after the arrow manager with no version gate, a second width that 1.29 did not have. The vanilla bodies are in `dayz-1-30-persistence.md`.

## Failure and ownership boundaries

- A wrong type, truncated field, failed base load, failed subclass `ctx.Read`, or trailing-layout mismatch rejects the load and preserves the pre-load state.
- Never convert a failed read into defaults and then report success. Defaults are valid only for an explicitly classified fresh or legacy case.
- Saving and loading must call `super` in the same relative position. Reordering the subclass prefix changes the wire contract.
- The stream belongs to the entity. If the mod that appended bytes disappears, no remaining handler understands or re-emits those bytes. Use CF ModStorage when uninstall/reinstall survival is a requirement.

## Verification checklist

- Save and load order and types are identical.
- `super` is propagated before subclass fields.
- Every `ctx.Read` result is checked.
- State mutation happens only after the complete read succeeds.
- Both optional-component widths are exercised.
- The hook storage version is not presented as the mod's format version.
- Uninstall behavior is declared rather than implied.
- (since 1.30) Construction-present and construction-absent EntityAI prefixes are both exercised; PlayerBase thermal float is present on 1.30 MP saves; CombinationLock `version >= 143` is exercised against a 142 fixture.

## Vanilla stream version gates that 1.30 added

1.30 adds these engine `version` cuts (the hook argument from `g_Game.SaveVersion()`, not a mod `storageVersion`):

| Engine `version` | Writer | Extra field | Load gate |
|---|---|---|---|
| `< 105` (legacy remnant) | `CombinationLock` (until removed) | attached-bool | still skipped when `version < 105` (`P:\scripts\4_world\entities\itembase\combinationlock.c:160-167`) |
| `>= 140` | `EntityAI` variables / `PlayerStomach` temperature | existing 1.29 gates | `entityai.c:3053-3058`; `playerstomach.c:492` |
| `>= 143` | `CombinationLock` | `int m_CombinationInside` | `combinationlock.c:169-177` |
| `>= 143` | `EntityAI` construction handle | `Rebuilding` payload or nothing | `entityai.c:2981-2984` |
| (ungated on 1.30 MP load) | `PlayerBase` | `float m_TemporaryResistanceTime` | `P:\scripts\4_world\entities\manbase\playerbase.c:7520-7524`; `P:\scripts\4_world\classes\thermalbiashandler.c:72-77` |

`BaseBuildingBase` subclass suffix is unchanged: `super`, three sync ints, `m_HasBase` (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:420-430`).

New 1.30 entity (no 1.29 fixture): `DigitalCodeLock` writes `m_LockPIN` (string), `m_IsLocked` (bool), `m_DoorIndex` (int) after `super` (`P:\scripts\4_world\entities\itembase\codelock.c:484-500`; `P:\scripts\4_world\classes\codelockcomponent.c:257-277`).

The vanilla bodies are copied in `dayz-1-30-persistence.md`.
