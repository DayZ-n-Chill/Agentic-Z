# Part decay and item falling

How a built part loses health over time on 1.30, and what happens to the items, players, vehicles and buildable objects resting on a part when it is dismantled or destroyed. Both run in `ConstructionBase`, so they apply to player built objects and to rebuildable map buildings alike.

## Part decay

The economy tick drives it. `EntityAI.OnCEIterate` calls `ProcessConstructionDecay` when the entity has a construction component, the server allows decay and the entity allows damage (`P:\scripts\3_game\entities\entityai.c:3904` to `:3911`). The server switch is `disableBaseDecay` (`P:\scripts\3_game\systems\construction_basic.c:37` to `:40`).

`ConstructionBase.ProcessConstructionDecay` walks the built parts that may decay. A part needs a damage zone named after it; its health moves by `dTime * rate * coef` and stops at the threshold (`P:\scripts\4_world\classes\constructionbase.c:365` to `:390`).

| Value | Default | Source |
|---|---|---|
| `part_decay_rate` | `-1.0` health per second (`DEFAULT_DECAY_RATE`) | `constructionbase.c:36`; read at `P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:203` to `:206` |
| `part_decay_threshold` | `0.3` of the zone's max health (`DEFAULT_DECAY_THRESHOLD`), clamped to 0 to 1 | `constructionbase.c:37`; `constructionparttyped.c:196` to `:200` |
| Coefficient | `1.5` during a sandstorm, else `1.0` | `constructionbase.c:38`, `:39`, `:392` to `:398` |
| `can_part_decay` | off when the key is missing | `constructionparttyped.c:21`, `:191` to `:193` |

`can_decay_general` on the `Construction` class is applied after each part's own data, so when it is present it overrides every part's `can_part_decay` (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttypedholder.c:51` to `:55`). A part with `can_part_decay=0` under `can_decay_general=1` still decays, as in `Land_House_1M2_Dam2` (`P:\DZ\structures_takistan\Residential\config.cpp:7913` and `:7951`). To keep one part from decaying, leave `can_decay_general` out and set `can_part_decay` on each part.

The vanilla Fence, Watchtower and territory flag set no decay key (a search of `P:\DZ\gear\camping\config.cpp` finds none), so their parts do not decay this way; they go when their economy lifetime runs out (`lifetime-and-storage.md`).

## What triggers a fall check

Dismantling or destroying a part runs `HandleEntityFalling` unless the server set `disableItemFalling` (`constructionbase.c:239` and `:254`). It returns without a check when:

- the part has no two point `collision_data` box, since the fall box is that box plus a top margin of 0.5 m (`GetItemFallDetectionBoxData` and `GetItemFallBoxMargins`, `constructionbase.c:1722` to `:1763`; the margins at `:41` to `:45`);
- the part sets `item_fall_trigger=0` (`constructionbase.c:282` to `:286`; read at `constructionparttyped.c:256` to `:262`);
- the part still holds up another built part (`PartSupportsOtherParts`, `constructionbase.c:288` to `:293` and `:891` to `:894`).

Otherwise it queues `ItemFall` on the system call queue, so materials and physics settle first (`constructionbase.c:297`).

## What falls

`ItemFall` queries the box for dynamic objects only and handles each by kind (`constructionbase.c:301` to `:362`):

| Object | What happens |
|---|---|
| Less than 0.3 m above the building's origin | skipped, as standing on the same surface (`ITEM_FALL_HEIGHT_DIFF_TOLERANCE`, `:46`; check at `:325`) |
| No physics, or a physics state other than none or collision | skipped (`:330` to `:335`) |
| A vehicle | its body is woken so it drops by itself (`:337` to `:344`) |
| A player | a small downward impulse (`:347` to `:351`) |
| An item | `OnItemFallRebuilding()`, then `ThrowPhysically` if the item still exists (`:354` to `:359`) |

## A buildable object on a falling floor

`BaseBuildingBase.OnItemFallRebuilding` runs on the server only; vanilla marks it "subject to change" for modders (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:1180` to `:1204`):

1. It throws out all attachments and cargo, unless the server set `disableDropAttachmentsOnFall` (`:1186` and `:1187`, `:1206` to `:1213`).
2. If `DestroyOnFall()` is true and refunds are allowed, it destroys every built part that is not a utility part (`DestroyConstructedParts`, `:1146` to `:1161`).
3. If refunds are off (`disableRefundMaterialsOnFall`), it runs the fall check for its own parts and deletes itself 100 ms later (`:1195` to `:1202`).

`DestroyOnFall` returns `false` on `EntityAI` (`P:\scripts\3_game\entities\entityai.c:4821` to `:4824`). `Fence`, `Watchtower`, `ShelterSite` and `TerritoryFlag` return `true` (`P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:901`, `watchtower.c:575`, `sheltersite.c:167`, `totem.c:581`). A mod's own buildable object that should break when its floor goes overrides `DestroyOnFall`; an item with state of its own overrides `OnItemFallRebuilding` and calls `super`, keeping in mind that the item may be deleted inside the call (`constructionbase.c:357`).

## Server switches

The three keys, `disableItemFalling`, `disableDropAttachmentsOnFall` and `disableRefundMaterialsOnFall`, sit in `cfggameplay.json` under `BaseBuildingData`, `ConstructionData` (`P:\scripts\3_game\cfggameplaydatajson.c:276` to `:281`), read by `CfgGameplayHandler` (`P:\scripts\3_game\cfggameplayhandler.c:352` to `:365`):

| Key | Effect |
|---|---|
| `disableItemFalling` | no fall check after a dismantle or destroy |
| `disableDropAttachmentsOnFall` | a falling buildable object keeps its attachments and cargo |
| `disableRefundMaterialsOnFall` | a falling buildable object is deleted instead of having its parts destroyed |

On a console server the last two start as `true` (`cfggameplaydatajson.c:261` to `:266`). Test a mod's buildable objects with the switches the target servers use.
