# Getting in from either side of a seat

How to keep a player from spinning more than half a turn when they board a vehicle from the "wrong" side: the native directional get in that 1.30 added, and the scripted snap used before it. Both are script, with no clip and no Workbench.

**Choose in this order.** On 1.30 use the native directional hooks first. The rule for a vehicle boarded from both sides is to not add a scripted snap or extra `pos_*_L` and `pos_*_R` points, and instead to copy the vanilla structure (crew proxies, and seat selections and components that exist in the View Geometry and Fire Geometry) and keep the vanilla action. Keep the scripted snap below as a fallback for a case the native route cannot cover; it is a workaround measured on one quad mod, not checked on `P:\`.

## What goes wrong

A vanilla crew seat names one get in position and one direction: `getInPos = "pos_driver"` and `getInDir = "pos_driver_dir"` (`P:\DZ\vehicles\wheeled\config.cpp:271`, `:272`). Observed in game on a quad mod: the player's heading is forced along that one direction when the get in starts, so a player coming from the opposite side is turned through more than 180 degrees just before the climb on animation. Cars hide this by putting the points on the side the door is on; a quad or bike is boarded from both sides.

## Native directional get in (1.30)

`ActionGetInTransport.Start` asks the vehicle whether it has directional boarding and, if so, works out which side the player is on with a dot product and passes it on (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:81` to `:102`):

```c
if (transport.HasDirectionalInOutAction())
{
    vector fwd = transport.GetDirection();
    fwd[1] = 0;
    fwd.Normalize();

    vector playerPosition = action_data.m_Player.GetPosition();
    vector toTarget = transport.GetPosition() - playerPosition;
    toTarget[1] = 0;
    toTarget.Normalize();

    vector right = Vector(fwd[2], 0.0, -fwd[0]);

    float side = vector.Dot(toTarget, right);

    if (side < 0.0)
        direction = 1;

    seat = transport.GetSeatAnimationTypeDirectional(crewIndex, direction);
}
else
    seat = transport.GetSeatAnimationType(crewIndex);
```

The two hooks are on `Transport` and do nothing by default: `HasDirectionalInOutAction()` returns false (`P:\scripts\3_game\vehicles\transport.c:677`) and `GetSeatAnimationTypeDirectional(int posIdx, int directionIndex)` raises "not implemented" (`:690`). The vanilla motorbike overrides both: it returns true, and for the driver seat returns 0 for direction 0 and 1 for direction 1 (`P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:53`, `:58`). The graph then picks the left or right clip from that number: `GetIn_L` starts on `GetCommandI(CMD_Vehicle_GetIn) == 0` and `GetIn_R` on `== 1` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1618`, `:1598`).

For a mod vehicle, override both hooks the same way. Not tested: whether that alone removes the need for the snap on a vehicle that is not a `Motorbike`.

Single track vehicles also get their own third person camera, `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:20`, registered at `:63`).

## The scripted snap (pre 1.30)

### Four memory points per seat

```
pos_driver_L      pos_driver_dir_L
pos_driver_R      pos_driver_dir_R
```

and the same for the passenger seat with its role name. The `_L` and `_R` points mirror each other across the vehicle's X axis, so the seat does not move; only the snap point and the facing change. An example layout:

```
pos_driver_L      = (+0.65, 0.05, -0.58)
pos_driver_dir_L  = (+0.65, 0.05, +0.42)   // 1.0 m forward of _L
pos_driver_R      = (-0.65, 0.05, -0.58)   // mirror in X
pos_driver_dir_R  = (-0.65, 0.05, +0.42)
```

Mirror in X only: `(-x, y, z)`. On a vehicle that is not symmetric, measure both sides instead of mirroring. Treat the four points as one decision; changing `_L` without `_R` makes one side feel different.

### The modded action

`ActionGetInTransport` is modded so the vanilla path runs first and a helper then moves the player. `OnStartServer` and `OnStartClient` are the action hooks on `ActionBase` (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:1391`, `:1388`).

```c
modded class ActionGetInTransport
{
    override void OnStartServer(ActionData action_data)
    {
        super.OnStartServer(action_data);
        TryRealignForMyQuad(action_data);
    }

    override void OnStartClient(ActionData action_data)
    {
        super.OnStartClient(action_data);
        TryRealignForMyQuad(action_data);
    }

    // Returns early for every vehicle that is not ours, so vanilla vehicles are untouched.
    protected void TryRealignForMyQuad(ActionData action_data)
    {
        if (!action_data || !action_data.m_Player)
            return;

        PlayerBase player = PlayerBase.Cast(action_data.m_Player);
        if (!player)
            return;

        Object target = action_data.m_Target.GetObject();
        if (!target)
            return;

        MyQuad_base quad;
        if (!Class.CastTo(quad, target))
            return;

        vector worldP = player.GetPosition();
        vector localP = quad.WorldToModel(worldP);

        // 1) Which seat is closer? Use the crew proxy points, not the action's slot.
        bool isDriver = true;
        if (quad.MemoryPointExists("crewdriver") && quad.MemoryPointExists("crewcodriver"))
        {
            vector mpD  = quad.GetMemoryPointPos("crewdriver");
            vector mpCo = quad.GetMemoryPointPos("crewcodriver");
            isDriver = vector.Distance(localP, mpD) <= vector.Distance(localP, mpCo);
        }

        // 2) Which side? +X is left in the model frame; exactly x = 0 goes to _L.
        string role = "codriver";
        if (isDriver)
            role = "driver";

        string suffix = "_R";
        if (localP[0] >= 0)
            suffix = "_L";

        string memPos = "pos_" + role + suffix;
        string memDir = "pos_" + role + "_dir" + suffix;

        // 3) Missing points: leave it to vanilla.
        if (!quad.MemoryPointExists(memPos) || !quad.MemoryPointExists(memDir))
            return;

        // 4) Snap position and yaw. Keep the player's height so terrain is not fought.
        vector worldPos = quad.ModelToWorld(quad.GetMemoryPointPos(memPos));
        vector worldDir = quad.ModelToWorld(quad.GetMemoryPointPos(memDir));
        vector look = worldDir - worldPos;
        look[1] = 0;
        if (look.LengthSq() < 0.0001)
            return;

        look.Normalize();
        float yaw = look.VectorToAngles()[0];

        vector newPos = worldPos;
        newPos[1] = worldP[1];
        player.SetPosition(newPos);
        player.SetOrientation(Vector(yaw, player.GetOrientation()[1], player.GetOrientation()[2]));
    }
}
```

Enforce Script has no ternary operator, so step 2 is written out with `if`.

### Why `super` runs first

The vanilla path has to accept the action before the player moves. Snapping before `super` takes the player out of the action's reach and the climb animation does not start. Snapping after leaves the engine's own forced turn a small residue, under 30 degrees, that reads as a step into the seat.

### Keep the vanilla keys in `config.cpp`

```cpp
class Crew
{
    class Driver
    {
        actionSel = "seat_driver";
        proxyPos  = "crewDriver";
        getInPos  = "pos_driver";
        getInDir  = "pos_driver_dir";
        isDriver  = 1;
    };
    class CoDriver
    {
        actionSel = "seat_coDriver";
        proxyPos  = "crewCoDriver";
        getInPos  = "pos_coDriver";
        getInDir  = "pos_coDriver_dir";
    };
};
```

Those are the vanilla key names (`P:\DZ\vehicles\wheeled\config.cpp:265` to `:282`). `pos_driver` without a suffix stays in the `.p3d`, at the centre or on the `_L` point. It is what any code path that bypasses the modded action falls back to.

### Leave other vehicles alone

The helper must return before doing anything for a vehicle that is not the mod's. The cast to the mod's base class does that for the base and every subclass (paint variants, special editions). Do not whitelist by class name string.

### The seat selection must be reachable from both sides

The action only starts when the player can aim at the seat's action selection (`actionSel`). A `seat_driver` selection that covers only the top of the seat is missed from the side, so the player cannot even start the action from there. Make the selection cover every visible face of the seat, including the side panels a player outside can aim at. `selection-painter-for-actions.md` is the practical way to do it.

### Player exactly on the centre line

`localP[0] >= 0` sends a player exactly on the centre line to `_L`. On a symmetric vehicle both sides are mirrors and it does not matter. On an asymmetric one the bias may be wrong; note the choice in the mod's notes. Flipping it is a one character change (`> 0`).

### The crew points must be the ones you wrote

The seat test reads `crewdriver` and `crewcodriver`. If the model was extended from a vanilla one and those points were appended instead of overwritten, the action reads the old positions and the left and right choice degrades (`py3d-1.0.0-quirks.md`, quirk 4).

### In-game check

1. Board from the left: the player lands on the seat with under 30 degrees of turn and the climb animation plays.
2. Board from the right: the same, mirrored, with no half turn in the air.
3. Repeat for the passenger seat.
4. Board a vanilla car: behaviour is unchanged. If it is not, the early return is wrong; fix it before shipping, because breaking vanilla vehicles is a regression every player sees.
