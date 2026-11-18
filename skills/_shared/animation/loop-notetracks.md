# Loop notetracks for actions a timer ends

How a clip for a hold action that a script timer ends, such as unjamming a weapon, must carry `LoopStart` and `LoopEnd`, how long the loop must last, and how to leave it without a jerk. The export route is in `blender-txa-export.md`; the bone rules are in `txa-bones-and-axes.md`.

## How vanilla times an unjam

All in `P:\scripts\4_world\entities\firearms\fsm\states\weaponunjamming.c` unless noted:

1. Entering the unjam sub-machine sets `m_jamTime = 5.0` (`:218`).
2. Each update of `WeaponUnjamming_Start` adds `dt` to `m_dtAccumulator` (`:29`), and only when `m_dtAccumulator >= m_jamTime` (`:38`) does it start the `UNJAMMING_END` action and post `WeaponEventUnjammingTimeout` (`:41` and `:42`).
3. That event moves the machine from `m_start` to `m_eject` (`:199`), and entering `m_eject` calls `SetJammed(false)` (`:87`).
4. On PC, letting go of the key before the timer ends starts `UNJAMMING_INTERRUPT`, and the weapon stays jammed (`:56`).

Meanwhile, on every update the player's inventory asks the weapon command `IsActionFinished()` (`HandleWeaponEvents`, `P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:396`). When the action is finished it checks `IsWaitingForActionFinish()` on the weapon (`:398`) and, when the current state is not waiting, sends `WeaponEventHumanCommandActionAborted` (`:414`). `WeaponUnjamming_Start` does not override `IsWaitingForActionFinish`, and the base answer for a state with no sub-machine is false (`P:\scripts\4_world\entities\firearms\fsm\states\weaponstatebase.c:152`).

The notetracks involved:

| Notetrack | Where it is defined | What it does in the unjam |
|---|---|---|
| `LoopEnd`, `LoopStart` | Player event table, `P:\DZ\anims\workspaces\player\player_eventtable.ae:35` and `:36` | Keep the command looping. |
| `Weapon_Unjammed` | Weapon event, `P:\scripts\3_game\human.c:1096`, becomes `WeaponEventAnimUnjammed` (`P:\scripts\4_world\entities\firearms\fsm\events.c:272`) | Moves `m_eject` on to `m_chamber` when the weapon has ammo (`weaponunjamming.c:201`). |
| `Weapon_CanUnjam_End`, `Weapon_CanUnjam_Start` | `human.c:1088` and `:1089`, become `WeaponEventAnimCanUnjamEnd` and `WeaponEventAnimCanUnjamStart` (`events.c:264` and `:265`) | Nothing: no unjam transition uses them (`weaponunjamming.c:199` to `:207`). |

## Why a clip without a loop never unjams

The unjam is driven by the timer, not by a notetrack. A clip with no loop section ends at its last frame, about 1.7 s for 51 frames. `IsActionFinished()` turns true, the start state is not waiting for that, so the machine gets the abort event and goes back to jammed. The continuous action fires again, and the 5 s timer never fills, because the clip never stays in progress long enough.

Vanilla avoids this: the PM73 jam clip has `LoopStart` at frame 22 and `LoopEnd` at frame 200 (read from a DayZATool extract), so the command loops and `IsActionFinished()` stays false until the timer ends it. Measured in game: a custom unjam clip with no loop notetracks aborts halfway and the weapon never unjams, and adding only `Weapon_CanUnjam_Start`, `Weapon_CanUnjam_End` and `Weapon_Unjammed` does not change that, as the table above predicts.

## Building the loop

- Write the notetracks as `LoopStart||-1` and `LoopEnd||-1`, the same form a DayZATool extract of the vanilla clip shows.
- Make the loop last at least as long as the timer, 5 s for an unjam; about 6 s is safe. The timer then fires before one cycle ends and the wrap is never seen, so the loop need not close perfectly. Vanilla loops run 5.9 to 6.9 s. A shorter closed loop also works but is harder to make clean.
- Put the notetrack that settles the state, such as `Weapon_Unjammed`, in the part after `LoopEnd`, near its end. Vanilla's closing part runs about 2.5 to 3.2 s.
- The engine leaves the loop from whatever pose is current when the timer fires, not from the pose keyed at `LoopEnd`. If that differs from the first pose after the loop, the clip snaps. From a frame well before `LoopEnd` (about frame 140 in a loop of about 195 frames), settle the moving part into its ready pose and hold it through `LoopEnd`, so it matches wherever the timer fires.
- Count loop frames at 30 fps, the engine default.

The same applies to any continuous action that plays until script stops it.
