# Bone mapping for a retarget

How the retarget modules match Mixamo bone names to a target rig, how to read the quality rating, the bone names of the common rig families, and how to fix a bad map. Running the retarget is in `mixamo-retarget.md`.

Experimental, like the retarget itself: the matching engine in `bone_matching.py` has unit tests, but no map built with it has been tried in Blender or in game. Every step is a Python call through the Blender MCP; there is no panel, so you review the map by printing and editing a dict. Scores given below were produced with the shipped `bone_matching.py`.

## Why the map matters

Mixamo names its bones in one fixed style (`mixamorig:Hips`, `mixamorig:LeftArm`); other rigs use `LeftArm`, `left_arm`, `arm.L` and more. A wrong entry gives twisted limbs, flipped rotations or a limb driven by the wrong bone.

The DayZ survivor skeleton uses the same PascalCase style as Mixamo (`Pelvis` at `P:\DZ\anims\cfg\skeletons.anim.xml:120`, `LeftArm` at `:130`, `LeftForeArm` at `:141`), but its root is `Pelvis`, not `Hips`, and it has a twist bone at every limb joint (`LeftArmRoll` at `:140`). Mixamo has no twist bones, so those stay unmapped; see `player-skeleton.md` for what that does to the hands.

## Three ways to get a map

| Way | Call | Use it for |
|---|---|---|
| Fuzzy match | `bm = auto_map_bones("Armature", "MyMod_Rig")` | An unknown or non-standard rig. Prints a quality rating and returns the dict for review. |
| Preset | `bm = get_preset_bone_mapping("mixamo_to_rigify")` | A start for a Rigify rig, after you fix it against that rig's bones. |
| Your own dict | `retarget_animation("Armature", "MyMod_Rig", bone_map={"Hips": "Root", "Spine": "Torso_01"})` | A rig you already know. Reusable across clips; a reviewed dict needs no second review. |

The shipped preset matches neither Rigify rig. It holds ten bones, hips to left hand, and mixes names from the generated control rig (`torso`, `neck`, `head`, `shoulder.L`) with names that exist only on the metarig (`spine`, `spine.001`, `spine.002`, `upper_arm.L`, `forearm.L`, `hand.L`). Entries that name no bone are skipped by `retarget_animation` without a warning. Print the target's bone names and correct every entry; add the right arm, legs and fingers, which the preset lacks.

## How the fuzzy match scores names

Names are normalized first: lower case, every character other than a letter, digit or dot becomes `_`, repeated underscores collapse, and leading and trailing ones are stripped. So `Left_Arm`, `left-arm` and `Left Arm` all become `left_arm`, `LeftArm` becomes `leftarm`, and `left.arm` keeps its dot. The dot is kept so the `.l` and `.r` suffix bonus works.

The score is `SequenceMatcher` on the two normalized names plus bonuses, capped at 1.0:

| Bonus | Amount |
|---|---|
| One name contains the other | +0.15 |
| Shared side or position prefix (left, right, upper, lower) | +0.1 |
| Shared side suffix (`.L`, `.R`, `_l`, `_r`) | +0.1 |
| Same number (`Spine1`, `Spine2`) | +0.1 |
| Shared limb keyword (arm, leg, hand, foot) | +0.05 |

Scores for `LeftArm` against other names:

| Target | Score | Why |
|---|---|---|
| `left_arm` | 1.000 | prefix and keyword, capped |
| `L_Arm` | 0.717 | keyword |
| `LeftLeg` | 0.671 | prefix only |
| `RightArm` | 0.583 | keyword only |
| `Head` | 0.364 | no bonus |

The threshold is 0.6. A shared side prefix counts for more than a shared limb keyword, so when the target lacks an arm bone, a leg bone of the same side can land in the map. This is the main reason every fuzzy map is reviewed.

`find_best_match` keeps the highest score at or above the threshold and returns `None` when nothing qualifies. `fuzzy_match_bones` takes exact alias matches first and fills the rest with the fuzzy pass; each target bone is used once.

## The quality rating

The rating counts how many of nine source bones have an entry: `Hips`, `Spine`, `Head`, `LeftArm`, `RightArm`, `LeftLeg`, `RightLeg`, `LeftHand`, `RightHand`. It does not check that the entry is the right bone.

| Rating | Critical bones | Review |
|---|---|---|
| excellent | 8 or 9 | Still review; the rating cannot see a wrong entry. |
| good | 6 or 7 | Quick review. |
| fair | 4 or 5 | Full review. |
| poor | 0 to 3 | Build the map by hand. |

`get_match_quality_report(bm)` returns `total_mappings`, `critical_bones_mapped` (as `"8/9"`), `quality` and a one line `summary`. `auto_map_bones` prints the same as three lines: `Auto-mapped 47 bones`, `Quality: EXCELLENT`, `Critical bones: 8/9`. Use the rating to set how deep the review goes, never to skip it; only a stored map already reviewed for the same pair of rigs is reused as is.

## Reviewing and fixing the map

1. Print every entry and the target's bones (`get_bones("MyMod_Rig")`).
2. Check the critical bones first, in this order: hips, spine chain, shoulders, arms and legs, hands and feet, then fingers and toes.
3. Edit the dict: `bm["LeftArm"] = "upper_arm.L"` replaces an entry, `del bm["LeftToeBase"]` drops one with no counterpart. Call `auto_map_bones` again to start over.
4. Bake with `retarget_animation("Armature", "MyMod_Rig", bone_map=bm)`. The bake adds keys only and leaves the rig's bones alone; the temporary constraints go with the bake. Call `add_to_nla` yourself if you want the result stacked.
5. Save the reviewed dict as JSON next to the `.blend` and load it for every later clip on the same pair of rigs. Test the map on one simple clip (idle or walk) before you run a batch.

## Bone names of common rig families

| Mixamo | Rigify FK controls | Unreal (UE4 and UE5 mannequin) | Unity humanoid |
|---|---|---|---|
| `Hips` | `hips` | `pelvis` | `Hips` |
| `Spine` | `spine_fk` | `spine_01` | `Spine` |
| `Spine1` | `spine_fk.001` | `spine_02` | `Chest` |
| `Spine2` | `spine_fk.002` | `spine_03` | `UpperChest` |
| `Neck` | `neck` | `neck_01` | `Neck` |
| `Head` | `head` | `head` | `Head` |
| `LeftShoulder` | `shoulder.L` | `clavicle_l` | `LeftShoulder` |
| `LeftArm` | `upper_arm_fk.L` | `upperarm_l` | `LeftUpperArm` |
| `LeftForeArm` | `forearm_fk.L` | `lowerarm_l` | `LeftLowerArm` |
| `LeftHand` | `hand_fk.L` | `hand_l` | `LeftHand` |
| `LeftUpLeg` | `thigh_fk.L` | | |
| `LeftLeg` | `shin_fk.L` | | |
| `LeftFoot` | `foot_fk.L` | | |

The right side mirrors the left (`shoulder.R`, `clavicle_r`, `RightShoulder` and so on). Pick the column that matches the bones your rig really has; the shipped preset uses metarig names, this table uses control names.

## Symptom to cause

| Symptom | Likely cause | Fix |
|---|---|---|
| Rating poor, or `KeyError: 'critical_bones_mapped'` | Source bones still carry `mixamorig:`, or the target has no armature hierarchy | Strip the prefix (`mixamo-retarget.md`, "Running it"); check the target's bones; write the map by hand. |
| Left arm drives the right arm | Mixed side suffix styles on the target | Use one style (`.L`/`.R` or `_l`/`_r`) through the whole rig, or swap the pairs in the dict. |
| Hips or spine not mapped | Names too far apart for 0.6 | Call `fuzzy_match_bones(source_bones, target_bones, threshold=0.5)`, or map the critical bones by hand and let the match fill fingers and toes. |
| Arms twist, legs bend backwards | Bone roll differs between the rigs, or constraint axes do not line up | Compare the rolls in Edit Mode and fix them, or lower the constraint influence and key corrections. |
| Every frame off by the same angle | Rest poses differ | Match the rest poses first (`mixamo-retarget.md`). |
