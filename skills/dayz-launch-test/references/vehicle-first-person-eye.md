# The vehicle first-person eye

Where the first-person camera sits in a vehicle, why its position is not a constant of the character class, and how to log it in every run before you judge first-person frames or check first-person geometry offline.

The camera binding is read in the vanilla scripts. The eye positions were measured in game on DayZDiag 1.30 during a motorbike import and are not checked on `P:\`. Where a 1.29 line is given, it was read from a 1.29 extract and is not checked on `P:\`.

## How the camera is placed

The vehicle first-person camera, `DayZPlayerCamera1stPersonVehicle` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:4`), keeps its parent's placement: its `OnUpdate` calls `super`, then only sets `m_fUseHeading` to 0 and updates every frame when physics extrapolation is on (`:8` to `:11`). It is bound by position to the character's `Head` bone (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercamera1stperson.c:15`) with an offset of `"0.04 0.04 0"` (`:21`, bound at `:53` and `:54`). The binding fields `m_iDirectBone` and `m_iDirectBoneMode` are at `P:\scripts\3_game\dayzplayer.c:23` and `:24`. The vehicle import notes rely on this (`skills/_shared/vehicles/rip-wheels-and-doors.md`).

## The eye moves with the head

Logged in the bike's model space at seven fixed looks per run with the bike stopped, over 11 runs, the eye sat 5.4 to 6.1 cm from the `Head` bone at every look (the offset is 5.7 cm long), and that bone moved while the rest held still. The pelvis stayed within 0.6 mm, with the handlebars at rest and the same rider animations swapped in, while the head ranged over 7.6 cm.

- Between runs of one class and one command line: four runs pinned to `SurvivorM_Lewis` put the eye at 1.479 to 1.493 m, one of them 8.5 to 9.4 cm to one side at yaw 0.
- Between looks: `SurvivorF_Keiko` held 1.401 m for six of seven looks in one run, with black clipped shards where the handlebar and top clamp should be, and 1.474 m on the seventh, handlebar back. Two later runs pinned to Keiko read 1.42 to 1.51 m, changing from look to look. In 5 of the 11 runs, though, the eye held within 1 mm over all seven looks, yaw of 45 degrees either way included.
- Across classes: `SurvivorF_Judy` matched Lewis's eye to 0.2 mm in one run and read 3.7 cm lower in another.

Why the head moves, and what held Keiko at 1.401 m (not reproduced), is not known. It is not a missing mod (`test-cell-evidence.md`, "An observation is worth its `-mod=` line"): the mod set and the animation swap were the same in every run. Window focus, which changed client readings in `test-cell-evidence.md`, "An unfocused client runs at about 20 fps", was not logged in these runs either.

## Log the eye in every run

- Log it at every look of every run: `GetCurrentCameraTransform` (`P:\scripts\3_game\dayzplayer.c:1237`) through the vehicle's `WorldToModel` (`P:\scripts\3_game\entities\object.c:874`). Compare first-person frames only between runs whose eyes match, and check offline first-person geometry (`skills/_shared/vehicles/`) against the eyes the runs logged, not against one eye per class.
- Pin the character class anyway, to remove one variable; whether the class moves the eye is not known. In a `modded class MissionServer`, override `PlayerBase CreateCharacter(PlayerIdentity identity, vector pos, ParamsReadContext ctx, string characterName)` (`P:\scripts\5_mission\mission\missionserver.c:499`, 1.29 `:486`; both spawn paths of `OnClientNewEvent` call it, `:573` and `:589`), set `characterName` from `CommandlineGetParam` (`P:\scripts\3_game\global\game.c:661`, 1.29 `:660`) behind a test launch parameter (`automated-cells.md`, "What a test mission `init.c` may do"), and call `super`. All 7 runs that passed a class spawned it; 17 runs without it drew 14 different classes.
