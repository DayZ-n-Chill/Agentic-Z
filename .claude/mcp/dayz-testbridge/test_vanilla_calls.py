"""Every engine name the AZ_TestBridge mod calls, pinned to the line on P:\\scripts that declares it.

The set test runs everywhere and fails when the mod calls a name nobody checked
here. The line test runs only with P:\\ mounted and fails when a pinned line no
longer declares the name (a new DayZ version moved it or removed it).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD_SCRIPTS = HERE.parents[2] / "skills" / "dayz-launch-test" / "assets" / "testbridge-mod" / "src" / "AZ_TestBridge" / "scripts"
P_SCRIPTS = Path("P:\\scripts")

VANILLA_CALLS = {
    "AbsFloat": r"1_core\proto\enmath.c:225",
    "ActionPossibilityCheck": r"4_world\classes\useractionscomponent\actionmanagerbase.c:262",
    "ActionTarget": r"4_world\classes\useractionscomponent\actiontargets.c:125",
    "Can": r"4_world\classes\useractionscomponent\actionbase.c:968",
    "CanReachSeatFromDoors": r"3_game\vehicles\transport.c:745",
    "CrewCanGetThrough": r"3_game\vehicles\transport.c:727",
    "GetActionComponentNameList": r"3_game\entities\object.c:192",
    "GetAnimSourceFromSelection": r"3_game\vehicles\transport.c:845",
    "GetComponentIndex": r"4_world\classes\useractionscomponent\actiontargets.c:159",
    "GetDoorSelectionNameFromSeatPos": r"4_world\entities\vehicles\carscript.c:2162",
    "GetObject": r"4_world\classes\useractionscomponent\actiontargets.c:142",
    "IsAreaAtDoorFreeDiag": r"3_game\vehicles\transport.c:918",
    "SetAnimationPhase": r"3_game\entities\entity.c:15",
    "GetCurrentCommandID": r"3_game\human.c:1473",
    "GetCursorHitPos": r"4_world\classes\useractionscomponent\actiontargets.c:169",
    "Cast": r"1_core\proto\enscript.c:94",
    "CastTo": r"1_core\proto\enscript.c:110",
    "ClassName": r"1_core\proto\enscript.c:37",
    "CommandlineGetParam": r"3_game\global\game.c:661",
    "Count": r"1_core\proto\enscript.c:380",
    "CreateAttachment": r"3_game\systems\inventory\inventory.c:209",
    "CreateInHands": r"3_game\systems\inventory\humaninventory.c:44",
    "CreateInInventory": r"3_game\systems\inventory\inventory.c:876",
    "CreateObject": r"3_game\global\game.c:691",
    "CreateObjectEx": r"3_game\global\game.c:703",
    "CrewDriver": r"3_game\vehicles\transport.c:194",
    "CrewEntryWS": r"3_game\vehicles\transport.c:200",
    "CrewMember": r"3_game\vehicles\transport.c:190",
    "CrewMemberIndex": r"3_game\vehicles\transport.c:186",
    "CrewPositionIndex": r"3_game\vehicles\transport.c:182",
    "CrewSize": r"3_game\vehicles\transport.c:178",
    "DeleteFile": r"1_core\proto\ensystem.c:528",
    "Distance": r"1_core\proto\enconvert.c:196",
    "EngineGetRPM": r"3_game\vehicles\car.c:227",
    "EngineGetRPMRedline": r"3_game\vehicles\car.c:224",
    "EngineIsOn": r"3_game\vehicles\car.c:230",
    "EngineStart": r"3_game\vehicles\car.c:233",
    "FileExist": r"1_core\proto\ensystem.c:397",
    "GearboxGetType": r"3_game\vehicles\car.c:266",
    "GetAction": r"4_world\classes\useractionscomponent\actionmanagerbase.c:214",
    "GetActionManager": r"4_world\entities\manbase\playerbase.c:1887",
    "GetActual": r"3_game\weather.c:38",
    "GetCommand_Vehicle": r"3_game\human.c:1528",
    "GetDate": r"3_game\global\world.c:28",
    "GetEntityInHands": r"3_game\systems\inventory\humaninventory.c:16",
    "GetFluidFraction": r"3_game\vehicles\car.c:363",
    "GetFog": r"3_game\weather.c:186",
    "GetGear": r"3_game\vehicles\car.c:248",
    "GetHealth": r"3_game\entities\object.c:994",
    "GetHierarchyRoot": r"3_game\entities\entityai.c:879",
    "GetHud": r"3_game\gameplay.c:720",
    "GetHumanInventory": r"3_game\entities\man.c:81",
    "GetInventory": r"3_game\entities\entityai.c:1884",
    "GetMission": r"3_game\global\game.c:1093",
    "GetNetworkID": r"3_game\entities\object.c:819",
    "GetObjectByNetworkId": r"3_game\global\game.c:356",
    "GetObjectsAtPosition": r"3_game\global\game.c:923",
    "GetOrientation": r"3_game\entities\object.c:305",
    "GetOvercast": r"3_game\weather.c:183",
    "GetPlayer": r"3_game\global\game.c:944",
    "GetPlayers": r"3_game\global\game.c:945",
    "GetPosition": r"3_game\entities\object.c:287",
    "GetQuantity": r"3_game\entities\entityai.c:2229",
    "GetRain": r"3_game\weather.c:189",
    "GetSpeedometer": r"3_game\vehicles\car.c:102",
    "GetTime": r"3_game\global\game.c:1535",
    "GetTransport": r"3_game\human.c:716",
    "GetType": r"3_game\entities\object.c:467",
    "GetVersion": r"3_game\global\game.c:942",
    "GetWeather": r"3_game\global\game.c:1371",
    "GetWeatherUpdateFrozen": r"3_game\weather.c:402",
    "GetWindMagnitude": r"3_game\weather.c:205",
    "GetWindMaximumSpeed": r"3_game\weather.c:263",
    "GetWindSpeed": r"3_game\weather.c:248",
    "GetWorld": r"3_game\global\game.c:931",
    "HasCrew": r"3_game\vehicles\transport.c:175",
    "Insert": r"1_core\proto\enscript.c:407",
    "IsKindOf": r"3_game\entities\object.c:511",
    "IsPaused": r"5_mission\mission\missiongameplay.c:1294",
    "IsPlayerLoaded": r"4_world\entities\manbase\playerbase.c:8967",
    "Length": r"1_core\proto\enstring.c:199",
    "LoadFile": r"3_game\tools\jsonfileloader.c:7",
    "LookAt": r"3_game\entities\camera.c:80",
    "MakeDirectory": r"1_core\proto\ensystem.c:525",
    "ObjectDelete": r"3_game\global\game.c:705",
    "OnDebugSpawn": r"3_game\entities\entityai.c:3955",
    "PerformActionStart": r"4_world\classes\useractionscomponent\actionmanagerclient.c:804",
    "Print": r"1_core\proto\endebug.c:96",
    "RayCastBullet": r"3_game\global\dayzphysics.c:211",
    "RaycastRVParams": r"3_game\global\dayzphysics.c:78",
    "RaycastRVProxy": r"3_game\global\dayzphysics.c:208",
    "SaveFile": r"3_game\tools\jsonfileloader.c:42",
    "Set": r"3_game\weather.c:49",
    "SetActive": r"3_game\entities\camera.c:45",
    "SetBrake": r"3_game\vehicles\car.c:203",
    "SetDate": r"3_game\global\world.c:46",
    "SetHandbrake": r"3_game\vehicles\car.c:209",
    "SetPosition": r"3_game\entities\object.c:294",
    "SetSteering": r"3_game\vehicles\car.c:185",
    "SetThrottle": r"3_game\vehicles\car.c:191",
    "SetWeatherUpdateFreeze": r"3_game\weather.c:397",
    "ShiftTo": r"3_game\vehicles\car.c:260",
    "ShiftUp": r"3_game\vehicles\car.c:257",
    "ShowHud": r"3_game\gameplay.c:672",
    "ShowQuickBar": r"3_game\gameplay.c:670",
    "Split": r"1_core\proto\enstring.c:396",
    "SurfaceGetType": r"3_game\global\game.c:1180",
    "SurfaceGetType3D": r"3_game\global\game.c:1183",
    "SurfaceRoadY": r"3_game\global\game.c:1177",
    "SurfaceY": r"3_game\global\game.c:1176",
    "ToInt": r"1_core\proto\enstring.c:20",
    "ToString": r"1_core\proto\enconvert.c:30",
    "WheelCount": r"3_game\vehicles\car.c:345",
    "WheelCountPresent": r"3_game\vehicles\car.c:348",
    "WheelHasContact": r"3_game\vehicles\car.c:286",
}

# Names the mod declares itself that are also vanilla names it calls: Continue is
# MissionGameplay.Continue (missiongameplay.c:1334), called in AZB_Resume, and
# IsActive is Camera.IsActive (camera.c:61), called in KeepView.
OWN_AND_VANILLA = {"Continue": r"5_mission\mission\missiongameplay.c:1334", "IsActive": r"3_game\entities\camera.c:61"}

KEYWORDS = {"if", "for", "while", "switch", "foreach", "return"}


def _mask(text: str) -> str:
    text = re.sub(r"//[^\n]*", "", text)
    return re.sub(r'"[^"\n]*"', '""', text)


def mod_source() -> str:
    return "\n".join(_mask(p.read_text(encoding="utf-8")) for p in sorted(MOD_SCRIPTS.rglob("*.c")))


def engine_calls() -> set[str]:
    src = mod_source()
    called = set(re.findall(r"\b([A-Za-z_]\w*)\s*\(", src))
    declared = set(re.findall(r"^\s*(?:static\s+|override\s+)*[\w<>]+(?:<[^>]*>)?\s+(\w+)\s*\(", src, re.M))
    classes = set(re.findall(r"\bclass\s+(\w+)", src))
    return called - declared - classes - KEYWORDS


def test_every_engine_call_of_the_mod_is_pinned():
    called = engine_calls()
    assert called == set(VANILLA_CALLS), (
        f"unchecked engine calls {sorted(called - set(VANILLA_CALLS))}; "
        f"no longer used {sorted(set(VANILLA_CALLS) - called)}"
    )


@pytest.mark.skipif(not P_SCRIPTS.is_dir(), reason="P:\\ is not mounted")
@pytest.mark.parametrize("name, where", sorted({**VANILLA_CALLS, **OWN_AND_VANILLA}.items()))
def test_each_pinned_line_still_declares_the_name(name, where):
    path, line = where.rsplit(":", 1)
    lines = (P_SCRIPTS / path).read_text(encoding="utf-8", errors="replace").splitlines()
    assert re.search(rf"\b{name}\s*\(", lines[int(line) - 1]), f"P:\\scripts\\{where} no longer declares {name}"


def test_every_script_file_is_diag_only():
    for p in sorted(MOD_SCRIPTS.rglob("*.c")):
        text = p.read_text(encoding="utf-8").strip()
        assert text.startswith("#ifdef DIAG_DEVELOPER") and text.endswith("#endif"), p.name
