# /dayz-gate behavior: the checks file

The checks file lists what `/dayz-gate behavior` tests. Its default place is `output/<ModName>-plan/behavior-checks.json`, or pass `--checks FILE`.

`dayz-mod-architect` writes one check per feature:

```json
{
  "mod": "MyVest",
  "checks": [
    {"id": "vest-spawns", "feature": "The vest exists in the world", "item": "MyVest_Carrier", "action": "spawn"},
    {"id": "vest-wear", "feature": "A player can wear the vest", "item": "MyVest_Carrier", "action": "wear"},
    {"id": "vest-pouch", "feature": "The pouch attaches to the vest", "item": "MyVest_Carrier", "action": "attach", "with": "MyVest_Pouch"}
  ]
}
```

| Action | What the test mission does | Passes when |
|---|---|---|
| `spawn` | Creates `item` on the ground next to the player. | the object is created |
| `hands` | Creates `item` in the player's hands. | the item is in hands |
| `wear` | Finds a slot of `item` that the player has and creates `item` in it. | the player wears it |
| `attach` | Spawns `item`, then creates `with` as its attachment. | the attachment is created |
| `cargo` | Spawns `item`, then creates `with` in its cargo. | `with` fits in the cargo |

Every check first needs `item` (and `with`) to exist in `CfgVehicles`, `CfgWeapons` or `CfgMagazines`. Each check deletes what it created. An `id` is letters, digits, `_`, `.` or `-` with no spaces; `item` and `with` are config class names. `feature` says in words what the check proves.
