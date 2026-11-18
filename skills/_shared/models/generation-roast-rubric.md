# Roast rubric

The scored rubric for the Phase 4 adversarial review of the 3D generation harness: 8 categories, the evidence each one needs, the defect list format and the re-roast scope. It is a review method, not a statement about the game; the vanilla numbers it asks for are measured on the reference model at review time.

Objective: find what is wrong, with evidence. Each category scores 0 to 2:

- **0**: one or more defects with no mitigation, or the category cannot be verified from the evidence on file
- **1**: minor defects, or verified with partial evidence
- **2**: verified clean, evidence cited

A verdict without cited evidence (a render filename and an observation, or a measured number against a dossier number) scores at most 1, however good it looks. UNVERIFIED is not PASS.

Gate V: no category at 0, total at least 13 of 16, no open high-severity defect.

## Categories

### 1. Silhouette against the reference

Match the `vr_capture` angles against the dossier views. Compare named landmarks (roofline, wheel arch, muzzle, grip curve), not the overall impression. Evidence: a side by side observation per landmark, naming the render file and the dossier view.

### 2. Proportions and dimensions (numeric)

A table of measured dimensions (the numeric output of `vr_capture`, or `verify_bounds`) against the dossier table, with the percentage deviation per row. A deviation over 5% is a defect unless the plan declared a tolerance. Evidence: the table itself.

### 3. Orientation and scale

The forward axis is correct, nothing is mirrored or upside down, and the size is plausible against the 1 m scale cube (and, for DayZ, against the vanilla 1:1 reference). Evidence: a render with the scale reference in frame.

### 4. Detail density against the plan

Every feature in the detail list, one row each: PRESENT, MISSING or DEGRADED. A missing planned feature is automatically a defect. A hero object shows at least 3 feature types. Evidence: a close-up render per detail zone.

### 5. Mesh integrity

The `verify_mesh_integrity` output for every part, on the current geometry. Any FAIL scores the category 0. Evidence: the gate printouts in the ledger.

### 6. Shading and normals

A Face Orientation overlay screenshot (any red facing the camera is a defect), black facets, pinching, smooth shading bleeding across hard edges, ngons on curved areas. Evidence: a viewport screenshot and a render. For DayZ, absolute winding cannot be judged here, only winding relative to a vanilla reference; absolute winding belongs to `/dayz-p3d-audit` (the hard guardrail in `blender-visual-review.md`).

### 7. Assembly

Gaps, floating parts, z-fighting shimmer between angles, parts sunk into each other further than the plan says. Evidence: `verify_overlap` results and observations on the iso render.

### 8. Target parity (DayZ or another engine)

Triangle count inside the budget for each LOD; ride height and footprint against the vanilla reference, measured (for a ground item, `lowest_z` about 0); proxies and slots present. For a target other than DayZ: the requirements of its export format. Evidence: counts and measurements against the vanilla numbers.

## Defect list format

| # | Severity (H/M/L) | Category | Defect | Evidence | Proposed fix |
|---|------------------|----------|--------|----------|--------------|

Severity: **H** is visibly wrong or breaks the target use (wrong proportions, broken mesh, missing major part). **M** is noticeable in normal viewing (a gap, a missing planned detail, a shading artifact). **L** is polish (bevel width, a minor texture seam).

## Zero-defect rule

A first roast that returns zero defects is suspect, not a success. Roast again with new camera angles and tighter close-ups before accepting. Two clean passes are accepted.

## Re-roast scope after fixes

Fixes touching 1 or 2 components: score the affected categories again, plus mesh integrity on the touched parts, from the same camera angles as the original roast (keep the before and after pairs). Fixes touching 3 or more components: a full re-roast.
