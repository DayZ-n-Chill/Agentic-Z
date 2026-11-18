# Research dossier template

The Phase 1 dossier of the 3D generation harness: copy this file to `output/harness-<item>/dossier.md` and fill every section before any geometry is built. It is a working template, not a statement about the game; the numbers you enter come from your own sources.

---

# Research dossier: <ITEM NAME>

Date: <YYYY-MM-DD> · Target: <DayZ mod / generic asset / render only> · Route: <parametric / AI generation>

## 1. Identity

- Exact item: <make, pattern, variant, condition, for example "AKM-pattern rifle, wooden furniture, weathered">
- Intended role in game (if DayZ): <slot, behavior, vanilla equivalent for parity>

## 2. References from several viewpoints (at least 4 viewpoints, plus detail close-ups)

| # | View | Source (URL or file) | Notes |
|---|------|----------------------|-------|
| 1 | front |  |  |
| 2 | side (left or right) |  |  |
| 3 | top |  |  |
| 4 | three-quarter |  |  |
| 5 | close-up: <detail zone> |  |  |
| 6 | close-up: <detail zone> |  |  |

Rule: every detail zone in the part inventory (section 4) needs at least one close-up. If a view cannot be found, record the gap in section 6. Do not invent the hidden side by symmetry without saying so.

## 3. Dimension table

Overall dimensions need two independent sources. Each landmark needs one source, or an explicit `ESTIMATE ±X%`.

| Measurement | Value | Source A | Source B / ESTIMATE |
|-------------|-------|----------|---------------------|
| Overall length |  |  |  |
| Overall width |  |  |  |
| Overall height |  |  |  |
| Landmark 1: <for example barrel length> |  |  |  |
| Landmark 2: <for example grip height> |  |  |  |
| Landmark 3 |  |  |  |
| Landmark 4 |  |  |  |
| Landmark 5 |  |  |  |

These numbers are the contract: the Phase 4 dimension audit measures the model against this table.

## 4. Part inventory

| Part | Visible features (these feed the detail list) | Build technique (`blender-assembly.md` rule) |
|------|-----------------------------------------------|-------------------------------------------|
|  |  |  |

## 5. Materials and finishes

| Part | Material | Finish and wear | Texture route (notes for `_co`, `_nohq`, `_smdi`) |
|------|----------|-----------------|---------------------------------------------------|
|  |  |  |  |

## 6. Unknowns (mandatory; an empty list on a non-trivial item is a red flag)

| Unknown | Decision: resolve / accept ±tolerance / ask user | Resolution |
|---------|--------------------------------------------------|------------|
|  |  |  |

## Gate R checklist

- [ ] At least 4 distinct viewpoints on file
- [ ] A close-up per detail zone
- [ ] Overall dimensions from 2 independent sources (or declared estimates)
- [ ] At least 5 landmark measurements
- [ ] Part inventory complete
- [ ] Unknowns explicit, each with a decision
