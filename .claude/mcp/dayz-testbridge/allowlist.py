"""The commands the dayz-testbridge may send to the AZ_TestBridge mod, with their peer, argument bounds and outputs.

This is half of the tool's safety (the other half is the mod's fixed `switch`;
test_mod_matches_allowlist.py checks the two agree). Every command is checked
here before any file is written. One command runs arbitrary script: `exec`,
allowed but off by default and enabled per session only (owner decision 3,
revised): the host refuses it unless session_start had allow_exec, and the mod
refuses it unless the launch passed -azBridgeExec=1. No command reads or writes
arbitrary files, and action_use names only classes that inherit ActionBase.

`wire_args(cmd, args)` turns the caller's arguments into the full AZB_Args
object the mod reads: every field present, defaults filled, so the mod never
has to tell a missing field from a zero.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

SERVER, CLIENT, BOTH = "server", "client", "both"

# Vanilla spawn flags, P:\scripts\3_game\ce\centraleconomy.c:31 and :38.
ECE_NOPERSISTENCY_WORLD = 8388608
ECE_PLACE_ON_SURFACE = 1060
DEFAULT_SPAWN_FLAGS = ECE_NOPERSISTENCY_WORLD | ECE_PLACE_ON_SURFACE  # 8389668
DEFAULT_PLACEMENT = 512  # ECE_ROTATIONFLAGS, centraleconomy.c:15

WORLD_MAX_XZ = 20480.0   # larger than every vanilla map (Chernarus 15360); a test position past it is a mistake
MAX_Y = 2000.0           # a y above this is almost always a swapped [x, z, y] triplet (spawning-and-placement.md)
MIN_Y = -100.0
MAX_RADIUS = 200.0
MAX_DRIVE_S = 60.0
MAX_SPAWNS = 50          # per session; counted by bridge.Bridge

CLASS_RE = re.compile(r"^[A-Za-z_]\w{0,127}$")
LABEL_RE = re.compile(r"^[\w.-]{1,64}$")
NET_ID_RE = re.compile(r"^-?\d{1,10},-?\d{1,10}$")


class AllowlistError(ValueError):
    """A command or argument the allowlist refuses; nothing was written."""


@dataclass(frozen=True)
class Arg:
    kind: str                      # str, int, float, bool, pos, enum
    default: Any = None
    lo: Optional[float] = None
    hi: Optional[float] = None
    pattern: Optional[re.Pattern] = None
    choices: tuple = ()
    required: bool = False
    wire: str = ""                 # the AZB_Args field name when it differs from the argument name


@dataclass(frozen=True)
class Command:
    peer: str
    args: dict = field(default_factory=dict)
    outputs: tuple = ()
    timeout: Callable[[dict], float] = lambda a: 15.0
    doc: str = ""
    opt_in: bool = False           # refused unless the session opted in (exec)


def _pos(required: bool = True, wire: str = "") -> Arg:
    return Arg("pos", default=[0.0, 0.0, 0.0], required=required, wire=wire)


_NET_ID = Arg("str", default="", pattern=NET_ID_RE, required=True)
_CLASS = Arg("str", default="", pattern=CLASS_RE, required=True)
_UNIT = dict(lo=0.0, hi=1.0)

COMMANDS: dict[str, Command] = {
    "ping": Command(BOTH, {}, ("version", "token", "player_loaded", "player_count"), doc="Is the peer alive and is a player loaded."),
    "mark": Command(BOTH, {"label": Arg("str", pattern=LABEL_RE, required=True)}, ("label",),
                    doc="Print [AZ-BRIDGE] MARK <label> in the peer's script log."),
    "spawn": Command(SERVER, {
        "cls": _CLASS, "pos": _pos(), "ground": Arg("bool", default=True),
        "flags": Arg("int", default=DEFAULT_SPAWN_FLAGS, lo=0, hi=2**31 - 1),
        "placement": Arg("int", default=DEFAULT_PLACEMENT, lo=0, hi=1023),
    }, ("net_id", "type", "class_name", "pos"), doc="CreateObjectEx; position read back 1 s later."),
    "spawn_in_inventory": Command(SERVER, {
        "cls": _CLASS, "where": Arg("enum", default="hands", choices=("hands", "cargo", "attachment")),
    }, ("net_id", "quantity", "reason"), doc="Create an item on the only player."),
    "delete": Command(SERVER, {"net_id": _NET_ID}, ("removed",), doc="Delete an object; refused while a car has crew."),
    "find_objects": Command(SERVER, {
        "pos": _pos(), "radius": Arg("float", default=10.0, lo=0.0, hi=MAX_RADIUS),
        "cls": Arg("str", default="", pattern=re.compile(r"^(|[A-Za-z_]\w{0,127})$")),
    }, ("objects",), doc="Up to 100 objects near a point."),
    "object_state": Command(SERVER, {"net_id": _NET_ID}, ("net_id", "type", "class_name", "pos", "ori", "health",
                                                         "parent_net_id", "slots", "attachments")),
    "teleport": Command(SERVER, {"pos": _pos(), "ground": Arg("bool", default=True)}, ("pos",),
                        doc="Move the only player; server position read back 1 s later."),
    "player_state": Command(SERVER, {}, ("pos", "health", "in_vehicle", "seat", "vehicle_net_id", "hands")),
    "set_time": Command(SERVER, {
        "year": Arg("int", default=2026, lo=1900, hi=2100), "month": Arg("int", default=6, lo=1, hi=12),
        "day": Arg("int", default=21, lo=1, hi=31), "hour": Arg("int", default=12, lo=0, hi=23),
        "minute": Arg("int", default=0, lo=0, hi=59),
    }, ("year", "month", "day", "hour", "minute")),
    "set_weather": Command(SERVER, {
        "overcast": Arg("float", default=0.0, **_UNIT), "fog": Arg("float", default=0.0, **_UNIT),
        "rain": Arg("float", default=0.0, **_UNIT), "wind": Arg("float", default=0.0, **_UNIT),
        "freeze": Arg("bool", default=True),
    }, ("overcast", "fog", "rain", "wind", "frozen")),
    "vehicle_prepare": Command(SERVER, {"net_id": _NET_ID, "engine_on": Arg("bool", default=True),
                                       "open_driver_door": Arg("bool", default=True)},
                               ("wheels_declared", "wheels_present", "fuel", "engine_on", "door_open", "entry_pos"),
                               doc="Server-side OnDebugSpawn (wheels, parts, fluids), then engine start and driver door"
                                   " open a tick later (as the vanilla door action does), read back later still."),
    "vehicle_state": Command(BOTH, {"net_id": _NET_ID},
                             ("speed", "rpm", "gear", "engine_on", "wheels_declared", "wheels_present",
                              "wheel_contact", "fuel", "crew_seats", "pos")),
    "raycast": Command(SERVER, {
        "from": _pos(wire="from_pos"), "to": _pos(wire="to_pos"),
        "mode": Arg("enum", default="view", choices=("view", "geom", "fire", "bullet")),
        "layer_mask": Arg("int", default=0, lo=0, hi=2**31 - 1),
    }, ("hits",)),
    "surface": Command(SERVER, {
        "x": Arg("float", lo=0.0, hi=WORLD_MAX_XZ, required=True), "z": Arg("float", lo=0.0, hi=WORLD_MAX_XZ, required=True),
        "y": Arg("float", default=0.0, lo=MIN_Y, hi=MAX_Y),
    }, ("ground_y", "road_y", "surface")),
    "get_in": Command(CLIENT, {"net_id": _NET_ID, "seat": Arg("int", default=0, lo=0, hi=31)}, ("seated", "tries", "reason"),
                      timeout=lambda a: 45.0, doc="The real get-in action on the client; seat confirmed on a later tick."),
    "get_out": Command(CLIENT, {}, ("on_foot",), timeout=lambda a: 30.0),
    "drive": Command(CLIENT, {
        "throttle": Arg("float", default=0.0, **_UNIT), "steer": Arg("float", default=0.0, lo=-1.0, hi=1.0),
        "brake": Arg("float", default=0.0, **_UNIT),
        "seconds": Arg("float", default=5.0, lo=0.1, hi=MAX_DRIVE_S),
        "sample_hz": Arg("float", default=5.0, lo=0.5, hi=20.0),
    }, ("samples", "distance", "top_speed"), timeout=lambda a: a["seconds"] + 20.0,
        doc="Drive the car the player is driving; samples speed, rpm, gear and position."),
    "camera_set": Command(CLIENT, {"pos": _pos(), "look_at": _pos()}, ("camera_pos",)),
    "camera_reset": Command(CLIENT, {}, ("player_view",)),
    "hud": Command(CLIENT, {"show": Arg("bool", default=True)}, ("hud",)),
    "resume": Command(CLIENT, {}, ("paused",), doc="Close the pause menu the client opens when its window is not active."),
    # --- added after v1 (feature-gaps.md, item 24) ---------------------------------------
    "shutdown": Command(SERVER, {}, (), doc="Orderly server exit (RequestExit): the world is saved. session_restart uses it."),
    "clear_spawns": Command(SERVER, {}, ("count", "kept"), doc="Delete every object `spawn` made this boot; a car with crew is kept."),
    "animate": Command(SERVER, {
        "net_id": _NET_ID, "source": Arg("str", pattern=re.compile(r"^\w{1,64}$"), required=True),
        "phase": Arg("float", default=1.0, lo=0.0, hi=1.0), "seconds": Arg("float", default=1.5, lo=0.0, hi=30.0),
    }, ("phase",), timeout=lambda a: a["seconds"] + 15.0, doc="SetAnimationPhase on a model.cfg source; phase read back after `seconds`."),
    "attach": Command(SERVER, {
        "net_id": _NET_ID, "cls": _CLASS, "slot": Arg("str", default="", pattern=re.compile(r"^(|\w{1,64})$")),
    }, ("net_id", "parent_net_id", "reason"), doc="Create an item in a slot of any object (a car part, a survivor's clothes)."),
    "god": Command(SERVER, {"on": Arg("bool", default=True)}, ("god",), doc="The only player takes no damage while on."),
    "engine": Command(SERVER, {"net_id": _NET_ID, "on": Arg("bool", default=False)}, ("engine_on",),
                      doc="Start or stop a car's engine on the server; read back a second later."),
    "walk": Command(SERVER, {
        "seconds": Arg("float", default=3.0, lo=0.1, hi=30.0), "speed": Arg("float", default=1.0, lo=0.0, hi=3.0),
        "angle": Arg("float", default=0.0, lo=-180.0, hi=180.0),
    }, ("pos", "distance"), timeout=lambda a: a["seconds"] + 15.0,
        doc="Walk the player through its input controller on the server (as vanilla's debug walk does): speed 1 walk, 2 jog, 3 sprint; angle in degrees from its heading."),
    "look_at": Command(CLIENT, {"pos": _pos(wire="look_at")}, ("aligned", "yaw_error", "pitch_error"),
                       timeout=lambda a: 20.0, doc="Turn the player's view to a point through its own aim input."),
    "inventory_move": Command(CLIENT, {
        "net_id": _NET_ID, "dest": Arg("enum", default="hands", choices=("hands", "cargo", "attachment", "ground")),
        "target_net_id": Arg("str", default="", pattern=re.compile(r"^(|-?\d{1,10},-?\d{1,10})$")),
    }, ("parent_net_id", "pos"), timeout=lambda a: 20.0,
        doc="A real inventory move by the player (vanilla Predictive* calls); read the result on the server with object_state."),
    "action_use": Command(CLIENT, {
        "action": _CLASS, "net_id": Arg("str", default="", pattern=re.compile(r"^(|-?\d{1,10},-?\d{1,10})$")),
        "component": Arg("int", default=-1, lo=-1, hi=1000),
    }, ("can", "started", "running", "reason"), timeout=lambda a: 20.0,
        doc="Start a player action (a class inheriting ActionBase only) on a target, or on the cursor's target."),
    "action_cursor": Command(CLIENT, {}, ("offered", "target_net_id", "target_type"),
                             doc="The actions the player's cursor offers now, as the vanilla action HUD reads them."),
    "ui_tree": Command(CLIENT, {}, ("menu", "widgets"), doc="The open menu's widgets: name, type, screen box, visibility."),
    "ui_click": Command(CLIENT, {"widget": Arg("str", pattern=re.compile(r"^[\w.-]{1,64}$"), required=True)},
                        ("menu", "clicked"), doc="Press a widget of the open menu through the menu's own OnClick."),
    "ui_set_text": Command(CLIENT, {
        "widget": Arg("str", pattern=re.compile(r"^[\w.-]{1,64}$"), required=True),
        "text": Arg("str", default="", pattern=re.compile(r"^[^\x00]{0,1000}$")),
    }, ("menu", "text"), doc="Type into an edit box of the open menu."),
    "ui_open": Command(CLIENT, {"menu": Arg("enum", default="ingame", choices=("ingame", "chat", "close"), wire="widget")},
                       ("menu",), doc="Open a vanilla menu (the pause menu or the chat input) for the UI commands, or close the open one."),
    "exec": Command(BOTH, {"code": Arg("str", pattern=re.compile(r"^[^\x00]{1,16000}$", re.S), required=True)},
                    ("executed",), opt_in=True,
                    doc="Run any Enforce Script (ExecuteEnforceScript). OFF unless session_start had allow_exec=true; "
                        "every code string is written to the session's exec log."),
}

# Every AZB_Args field the mod declares, with the default the host writes when a command does not use it.
WIRE_DEFAULTS: dict[str, Any] = {
    "label": "", "cls": "", "pos": [0.0, 0.0, 0.0], "flags": 0, "placement": 0, "where": "", "net_id": "",
    "radius": 0.0, "ground": False, "year": 0, "month": 0, "day": 0, "hour": 0, "minute": 0,
    "overcast": 0.0, "fog": 0.0, "rain": 0.0, "wind": 0.0, "freeze": False, "engine_on": False, "open_driver_door": False,
    "from_pos": [0.0, 0.0, 0.0], "to_pos": [0.0, 0.0, 0.0], "mode": "", "layer_mask": 0,
    "x": 0.0, "z": 0.0, "y": 0.0, "has_y": False, "seat": 0, "throttle": 0.0, "steer": 0.0, "brake": 0.0,
    "seconds": 0.0, "sample_hz": 0.0, "look_at": [0.0, 0.0, 0.0], "show": False,
    "code": "", "source": "", "phase": 0.0, "slot": "", "on": False, "speed": 0.0, "angle": 0.0, "target_net_id": "",
    "dest": "", "widget": "", "text": "", "action": "", "component": 0,
}


def peers(cmd: str) -> tuple[str, ...]:
    """The peers a command may go to: ("server",), ("client",) or both."""
    peer = command(cmd).peer
    return (SERVER, CLIENT) if peer == BOTH else (peer,)


def command(cmd: str) -> Command:
    if cmd not in COMMANDS:
        raise AllowlistError(f"unknown command {cmd!r}; allowed: {', '.join(sorted(COMMANDS))}")
    return COMMANDS[cmd]


def _number(name: str, value: Any, spec: Arg, integer: bool) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or (integer and not isinstance(value, int)):
        raise AllowlistError(f"{name} must be {'a whole number' if integer else 'a number'}, got {value!r}")
    if not math.isfinite(value):
        raise AllowlistError(f"{name} must be finite")
    if spec.lo is not None and value < spec.lo or spec.hi is not None and value > spec.hi:
        raise AllowlistError(f"{name}={value} is outside {spec.lo:g} to {spec.hi:g}")
    return int(value) if integer else float(value)


def check_pos(name: str, value: Any) -> list[float]:
    """[x, y_up, z] inside the world: 0 <= x, z <= WORLD_MAX_XZ and MIN_Y <= y <= MAX_Y."""
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise AllowlistError(f"{name} must be [x, y, z] (engine order, y is up)")
    x, y, z = (_number(f"{name}[{i}]", v, Arg("float"), False) for i, v in enumerate(value))
    if not (0 <= x <= WORLD_MAX_XZ and 0 <= z <= WORLD_MAX_XZ):
        raise AllowlistError(f"{name}: x and z must be inside the world, 0 to {WORLD_MAX_XZ:g}")
    if not MIN_Y <= y <= MAX_Y:
        raise AllowlistError(f"{name}: y={y:g} is outside {MIN_Y:g} to {MAX_Y:g}; positions are [x, y_up, z], "
                             "so a large y usually means x, z, y were swapped")
    return [x, y, z]


def check_arg(cmd: str, name: str, spec: Arg, value: Any) -> Any:
    where = f"{cmd}.{name}"
    if spec.kind == "pos":
        return check_pos(where, value)
    if spec.kind in ("int", "float"):
        return _number(where, value, spec, spec.kind == "int")
    if spec.kind == "bool":
        if not isinstance(value, bool):
            raise AllowlistError(f"{where} must be true or false")
        return value
    if spec.kind == "enum":
        if value not in spec.choices:
            raise AllowlistError(f"{where} must be one of {', '.join(spec.choices)}")
        return value
    if not isinstance(value, str) or (spec.pattern is not None and not spec.pattern.match(value)):
        raise AllowlistError(f"{where}={value!r} is not allowed" + (f" (must match {spec.pattern.pattern})" if spec.pattern else ""))
    return value


def validate(cmd: str, args: Optional[dict] = None) -> dict:
    """The command's own arguments, checked and with defaults: {name: value}. Raises AllowlistError."""
    spec = command(cmd)
    args = dict(args or {})
    unknown = sorted(set(args) - set(spec.args))
    if unknown:
        raise AllowlistError(f"{cmd}: unknown arguments {unknown}; allowed: {sorted(spec.args)}")
    out = {}
    for name, arg in spec.args.items():
        if name not in args or args[name] is None:
            if arg.required:
                raise AllowlistError(f"{cmd}: {name} is required")
            out[name] = arg.default
        else:
            out[name] = check_arg(cmd, name, arg, args[name])
    if cmd == "spawn" and not out["flags"] & ECE_NOPERSISTENCY_WORLD:
        raise AllowlistError(f"spawn.flags must include ECE_NOPERSISTENCY_WORLD ({ECE_NOPERSISTENCY_WORLD}) so test objects never persist")
    return out


def wire_args(cmd: str, args: Optional[dict] = None) -> dict:
    """The full AZB_Args object for the mod: every field, defaults filled, names as the mod declares them."""
    checked = validate(cmd, args)
    spec = COMMANDS[cmd]
    wire = {k: (list(v) if isinstance(v, list) else v) for k, v in WIRE_DEFAULTS.items()}
    for name, value in checked.items():
        wire[spec.args[name].wire or name] = value
    if cmd == "surface":
        wire["has_y"] = args is not None and args.get("y") is not None
    return wire


def timeout(cmd: str, checked: dict) -> float:
    return COMMANDS[cmd].timeout(checked)
