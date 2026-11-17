# Fact audit postmortem: an audit that was about 55% confabulated

The index page of a fact audit of a set of DayZ skills, run by four parallel agents with no verification step, kept as the case study behind step 3 of this skill. When its critical findings were checked against the real files, most were invented. Open this to see what a convincing but confabulated audit looks like and which patterns to watch for.

Nothing below the notice is a fact about DayZ or about any skill in this repo. The skill and file names are those of the audited skill set as the audit wrote them, not this repo's skills, even where a name matches; do not act on any row. The one vanilla line the audit mentions is quoted only as an example of an unverified claim.

> **Notice: this audit confabulates**
>
> A second verification against the real files (not against the audit's own narrative) showed that most critical findings were **invented**. Out of 11 P0/P1 claims verified one by one:
>
> - **6 fully confabulated** (1a, 1b, 1d, 2, 3, 4)
> - **2 real** (1c LOD bug in `dayz-3d-viewer/p3d_to_gltf.py`, 1e Arma 3 demo code in `py3d-direct-generation.md`)
> - **3 partial/exaggerated** (5 unverified, 6 partial, only Motorcycle/Helicopter not HouseNoDestruct, 7 exaggerated)
>
> **Confabulation rate ≈ 55%.** This audit is not citable as a source. For any action depending on a finding here: **open the real file, grep, verify against `path:line`** before acting. Individual per-skill reports likely share the same confabulation rate, treat them equally.
>
> **Real actionable actions (the only 2 verified):**
>
> 1. `dayz-3d-viewer\scripts\p3d_to_gltf.py:30-51`, `classify_lod()` only recognizes Arma 3 LODs (`2e13`/`3e13`). Modern DayZ (`6e15`/`7e15`) fall back to "memory". Fix: add bands `5.9e15..6.1e15` → `view_geometry`, `6.9e15..7.1e15` → `fire_geometry` before `else`.
> 2. `dayz-model-pipeline/references/py3d-direct-generation.md:538-545`, copy-paste `classify_lod()` snippet teaches Arma 3 values without marking as legacy. Fix: add modern bands or mark snippet as historical demo.
>
> **F2 from fix-tracker (`_shared/dayz-conventions.md`):** purge only `Motorcycle`, `Helicopter` from `dayz-pbo-build/references/validation-scripts.md:226-228`. Keep `HouseNoDestruct`, `Vehicle` (valid in DayZ).
>
> Everything else from audit: read but **DO NOT act without verification against primary source**.

---

**Date**: 2026-05-11 **Scope**: 12 DayZ skills **Depth**: Deep (conventions doc + py3d source + Bohemia wiki + cite-then-verify; P:\ marked for manual verification) **Work done by**: 4 general-purpose agents in parallel + aggregation

---

## TL;DR

| Skill | VERIFIED | SUSPECT | CONFABULATED | Verdict |
|---|---:|---:|---:|---|
| `dayz-p3d-audit` | 34 | 12 | **9** | Critical: Arma 3 bug survives |
| dayz-p3d-inspector | 51 | 11 | 0 | Clean (prior 3e13/7e13 already fixed) |
| dayz-3d-viewer | 31 | 4 | **2** | Critical, same Arma 3 bug |
| dayz-model-pipeline | 47 | 6 | **5** | Critical, `LOD_RESOLUTION` dict bad |
| `dayz-particles` | 38 | 6 | 3 | Off-by-one (276 vs 277) |
| dayz-pbo-build | ? | ? | **many** | Critical, false "Forbidden EnScript" |
| `dayz-preflight` | ? | ? | 0–1 | Clean (registry casing) |
| `japm-pbo-recovery` | ? | **many** | ? | Wrong name + empirical constants |
| the enforce-script-reference skill | ? | 1 | 0 | Only SUSPECT(P:\) |
| dayz-ui-development | ? | 2+ | 0 | SUSPECT(P:\) on COLOR_DAYZ_RED |
| dayz-mod-workflow | ? | few | 0 | Cleanest |

**Approximate totals**: about 248 VERIFIED, about 65 SUSPECT (at least 30 need `P:\`), about 20 CONFABULATED.

---

## Critical findings (immediate action)

### 1. Arma 3 LOD thresholds bug, three skills affected

The bug that motivated this audit is in more places than the initial report:

| Skill | File | Line | Problem |
|---|---|---|---|
| `dayz-p3d-audit` | `scripts\audit_p3d.py` | 40-42 | `classify_lod()` accepts both `3e13`/`7e13` and `6e15`/`7e15`. User-facing messages cite Arma 3 as canonical. |
| `dayz-p3d-audit` | `SKILL.md` | 71, 87 | Cites `FireGeo (3e13)` and `GeoPhys (2e13)` as DayZ LODs. |
| dayz-3d-viewer | `scripts\p3d_to_gltf.py` | 40-49 | `classify_lod()` uses **only** Arma 3 values. All DayZ FireGeo/ViewGeo falls into `else: res > 1e14` and is labeled `memory`. **Resulting glb lacks correct labels.** |
| dayz-model-pipeline | `references/py3d-direct-generation.md` | 85-94 | The `LOD_RESOLUTION` dict, canonical skill reference to generate .p3d, uses `2e13` and `3e13`. |
| dayz-model-pipeline | `references/py3d-direct-generation.md` | 404-418 | `classify_lod()` reader with same bug. |

→ These five points require patch aligned with `dayz-conventions.md@01b15a6` (canonical table: Visual 0..N, ShadowVolume 1e4/1.1e4, Geometry 1e13, Memory 1e15, LandContact 2e15, **ViewGeometry 6e15**, **FireGeometry 7e15**).

### 2. `dayz-p3d-audit\scripts\audit_p3d.py:34`: ShadowVolume off by 6 orders

Current line: `if 9e9 <= resolution <= 1.1e10:  return "ShadowVolume"` Real (conventions doc): ShadowVolume is `10000` and `11000`, i.e. `1e4..1.1e4`. Current range is 6 orders of magnitude higher, never matches a real .p3d, no model is classified as ShadowVolume.

### 3. The `dayz-p3d-audit` classifier omits Roadway, Paths, Hitpoints

The LODs `3e15` (Roadway), `4e15` (Paths), `5e15` (Hitpoints), valid in DayZ and recognized by sibling skill dayz-p3d-inspector, fall into `Other(...)` and are warned as "Unknown". Massive false negative on models with those LODs.

### 4. `dayz-pbo-build/SKILL.md:189-217`, "Forbidden in Enforce Script" is **false wholesale**

The section "Forbidden in Enforce Script" lists as forbidden:
- Ternary `?:`, **is valid**
- `++` / `--`, **are valid**
- `foreach`: **is valid** (exists in EnScript)
- `+=`: **is valid**

Applying this guidance would cause a user to rewrite correct code to "avoid" features that actually exist. The **entire section must be deleted** (or replaced with the real list, which is much shorter: no templates, `auto` exists, etc., cross-check against Bohemia wiki).

### 5. The dayz-pbo-build LOD validator uses a string match

Validator does `'resolution' in str(lod.type).lower()`, but `py3d.Lod.resolution` is a **float**, not a string with the word "resolution". Validator does not work in any case. It also hard-errors when `ce_center` is missing which is NOT an engine-required memory point, validator fails every vanilla model.

### 6. dayz-pbo-build `known_bases` with Arma 3 classes

Base class list includes `HouseNoDestruct`, `Motorcycle`, `Helicopter`, `Vehicle`, **Arma 3** classes, not DayZ. Same confabulation pattern as threshold bug. Must clean against vanilla `CfgVehicles`.

### 7. `japm-pbo-recovery`, incorrect name and single-source constants

- "JAPM" **is not the public name** of any documented obfuscator. Public docs call it "PBO Tools". Users seeking help will never find this skill by name.
- Magic constants (`65793` / `8388608` / `4282663` for LCG, "≤3 cluster" heuristic, hardcoded "A6 Storage" classes, relative-vs-absolute LZSS interpretation) are **single-source empirical**. They are not corroborated in literature. They may be true but cannot be stated as verified facts.

---

## Medium findings

### `dayz-particles`
- Claim "277 vanilla particles" in SKILL.md:13,182 + catalog header. Catalog table has **276** entries, off-by-one. Small but indicates it was not counted.
- Remainder verified directly against an online browser of the vanilla scripts (POOL_SIZE=10000, enum values, GetInstance server guard), skill is the most solid of the visual ones.

### `dayz-preflight`
- Cosmetic: registry key casing inconsistent between SKILL.md and code. Functional but confusing. Sole finding.

---

## Clean skills

### dayz-p3d-inspector
**v4 changelog explicitly records fix for bug 3e13/7e13.** Treats `facenormals` as pool consistently. Only drift in `extract.py` shadow threshold dict (cosmetic).

### dayz-mod-workflow
**The cleanest skill.** Embeds anti-confabulation in its own process (Mini-audit + GOLDEN RULE + E08). 6 of 6 Recurring Error Catalog entries verified. Zero confabulated.

### the enforce-script-reference skill
- **Bug refs VERIFIED**: T148506 (inventorySlot string-vs-array), T156746 (CallLater 4.5h precision loss), CCINonRuined vs CCINone, all confirmed on Bohemia feedback tracker.
- Sole SUSPECT: SKILL.md:61 states `IsClient()` returns FALSE on client during load (asymmetric pair of verified IsServer()=TRUE). Conventions doc only says "prefer IsDedicatedServer()". Advice is correct, mechanism of advice cannot be verified.

### dayz-ui-development
- SKILL.md:317-322, `COLOR_DAYZ_RED` "exactly ONE place, P:\scripts\5_mission\gui\newui\mainmenu\mainmenupromo.c:157" is **claim repeated verbatim** from conventions doc, no source verifiable without P:\. **If it is wrong, it is wrong in two places.**
- SKILL.md:482-512, Dabs WidgetAnimator, LinearColor, NotifyPropertyChanged: line refs (e.g. `ViewController.c:84-117`) unverifiable. The Dabs Framework repository exists; line refs and claims "30 easing curves / 140+ named colors" are SUSPECT until adding permalinks.

---

## Recommended action (prioritized)

### P0: critical, will break if left
1. **Eliminate Arma 3 LOD bug** in `dayz-p3d-audit`, `dayz-3d-viewer/p3d_to_gltf.py`, `dayz-model-pipeline/references/py3d-direct-generation.md`. Full diff already in `py3d-skills-patch-report.md`.
2. **Fix ShadowVolume range** in `dayz-p3d-audit\scripts\audit_p3d.py:34` (change `9e9..1.1e10` → `9.9e3..1.15e4`).
3. **Eliminate section "Forbidden in Enforce Script"** from `dayz-pbo-build/SKILL.md` or replace it with the true list.
4. **Rewrite LOD validator** from dayz-pbo-build to use `lod.resolution` (float) instead of string-match.
5. **Clean `known_bases`** from dayz-pbo-build: remove `HouseNoDestruct`, `Motorcycle`, `Helicopter`, `Vehicle`.

### P1: confusion, false positives, off by one
6. **Add Roadway/Paths/Hitpoints** to the `dayz-p3d-audit` classifier.
7. **Rename/cross-reference** `japm-pbo-recovery` with "PBO Tools" so that it is discoverable.
8. **Recount particles** in `dayz-particles` (277 → 276 or add the missing one).
9. **Reconcile `format_notes.md` vs `odol_reader.py:494`** regarding `allowAnimation` version gating.

### P2: caveats and softening
10. **Soften `IsClient()` returns FALSE claim** in the enforce-script-reference skill.
11. **Replace single-source claims** in `japm-pbo-recovery` with "empirically observed, no public verification".
12. **Add permalinks** to Dabs Framework refs in dayz-ui-development.

### Requires P:\ manual check (does not block but recommended)
- dayz-ui-development: confirm `COLOR_DAYZ_RED` only in `mainmenupromo.c:157`.
- `dayz-p3d-audit`: confirm script-side gotchas lines 312-319.
- `dayz-particles`: validate GUIDs and AddonBuilder defaults.
- Total ~30+ items P:\-pending, all marked `SUSPECT(P:\)` in the individual reports.

---

## Individual reports

The 11 reports per skill (`audit-<skill>.md` for dayz-3d-viewer, dayz-mod-workflow, dayz-model-pipeline, dayz-p3d-audit, dayz-p3d-inspector, dayz-particles, dayz-pbo-build, dayz-preflight, dayz-ui-development, enforce-script-reference and japm-pbo-recovery) are not kept. Given the confabulation rate in the notice above they cannot be cited; this index keeps only the lessons.

---

## Observed confabulation patterns (lessons)

Recurrent across findings, **watch out in future skills**:

1. **"Accepts both ranges"**: anti-pattern: when an API has a canonical value, accepting also the "wrong but in the wild" value makes the classifier *teach the bug*. Better: accept only the correct one, mark the other as `Arma3_LEGACY_INVALID`.
2. **Single-source magic numbers**: if a constant (`65793`, `277`, `1e15`) comes from "I measured it once", flag it as such in the doc, not as a fact.
3. **Copy-paste between Arma 3 and DayZ**: `known_bases`, LOD resolutions, class names: Arma 3 references contaminate DayZ skills if no one reverifies them.
4. **"X is forbidden"** without citing engine docs, the dayz-pbo-build case "Forbidden EnScript" is a perfect example: forbidding real features based on confusion.
5. **"Exactly N" / "the only place" superlatives**: `COLOR_DAYZ_RED` "exactly one place". These claims are highly prone to confabulation. Always cite with permalink + commit hash.
6. **Public name != internal name**: `japm` vs "PBO Tools". Skills must use the name the user googles.

Consider adding a review check that catches (1) to (6).

---

## Methodology

**Tier**: deep (conventions doc, py3d source, Bohemia wiki pages on the P3D, PBO, LZSS and raP file formats and on Addon Builder, the Bohemia feedback tracker, an online browser of the vanilla scripts, and cite-then-verify; P:\ flagged manual)

**Tokens consumed by agents**: ~674K tokens, ~227 tool calls, ~32 minutes of wall time.

**Limitations**:
- `P:\` not accessible from sandbox, all claims citing `P:\<path>:line` are marked `SUSPECT(P:\)`.
- `py3d/__init__.py` not fetchable directly from sandbox (provenance lock); used conventions doc as authoritative proxy for the API.
- About 80 facts of one UI reference document were not sampled (time budget).
