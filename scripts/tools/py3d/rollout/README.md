# py3d rollout — wheel restock + pinned preimage

> Status: py3d 1.4.0 patch intake is CLOSED (2026-09-02); what is active
> is restocking of vendored wheel.
> Preimage: `live-snapshot-2026-09-02`, re-read against live skills root.
> Distribution: vendored wheel per skill; this decision is not modified here.

## Restock the wheel (the command)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File tools\py3d\rollout\apply-s2-rollout.ps1 `
  -TargetSkillRoot <raíz de skills> `
  -BackupRoot <raíz de backup externa> `
  -WheelOnly
```

`-WheelOnly` does not read the preimage manifest. The wheel fix depends
only on `wheel-manifest.json` and on `tools/py3d/dist`; tying it to a prose hash
made any edit of a skill abort the replacement. Add
`-NoWrite` to see the plan without writing.

This directory contains a fail-closed operation. There are no full projections nor a route copying knowledge files on top of live skills. Every text change is made with a unified patch, preceded by `git apply --check`; idempotence is recognized with `git apply --reverse --check`.

## Artefactos vigentes

- `apply-s2-rollout.ps1`: preflight, external backup, patch application and pinned wheel copy.
- `preimage-manifest.json`: 6 paths with SHA-256 of live preimage, all `not_applicable`. Only detect drift; none are written.
- `patches/`: the four py3d 1.4.0 patches, kept as record. None remain live (see "Closed patch intake"); applicator patch engine remains active and covered by `tests/py3d_rollout/test_apply_rollout.py`.
- `wheel-manifest.json`: v2 identity of wheel, including its version and SHA-256.
- `patched/`: deliberately removed. Restoring it would reopen the full replacement route that caused BUG-018/BUG-019.

## Classification by target

| Target | Status | Evidence / preserved delta |
|---|---|---|
| `dayz-model-pipeline/SKILL.md` | `retirado` | Patch raised minimum to 1.4.0 and live already declares `>= 1.6.0` (`SKILL.md:113,119,122`): applying it would be a regression. |
| `dayz-model-pipeline/references/py3d-direct-generation.md` | `not_applicable` | Projection contains no new 1.4.0 delta; replacing it would remove conditional winding and DayZ-canonical LOD resolutions. |
| `dayz-3d-viewer/SKILL.md` | `not_applicable` | Contains no new 1.4.0 API; its differences are destructive divergence from live. |
| `dayz-p3d-inspector/SKILL.md` | `not_applicable` | No separable delta from 1.4.0; SP-028 is preserved. |
| `dayz-p3d-audit/SKILL.md` | `not_applicable` | Does not provide 1.4.0; SP-017, SP-051 and the 13 Silent Killers are preserved. |
| `dayz-p3d-audit/scripts/audit_p3d.py` | `not_applicable` | Projection is a strict subset of live: 7 of 15 functions; all 15 are preserved, including `check_wheel_slot_firegeo`. |
| `dayz-pbo-build/references/validation-scripts.md` | `not_applicable` | Contains no 1.4.0 delta; projected changes belong to another scope. |
| `dayz-proxy-align/SKILL.md` | `retirado` | Live declares `>= 1.6.0` (`SKILL.md:37,40`), already has `add / inspect / align / remove` cycle (`SKILL.md:49`) and preserves **on purpose** patch delta under "py3d 1.4.0 lifecycle (plugin projection, historical)" (`SKILL.md:92`). Not lost: relabeled. |
| `dayz-animation-pipeline/references/py3d-1.0.0-quirks.md` | `retirado` | Already applied in live: `git apply --reverse --check` exits 0. |
| `dayz-animation-pipeline/SKILL.md` | `retirado` | Already applied in live (`git apply --reverse --check` exits 0) and live minimum is `>= 1.6.0` (`SKILL.md:16`). |

The six `not_applicable` remain in manifest: although not written, their hash is checked to detect preimage drift. No empty patch is fabricated.

## Closed patch intake (2026-09-02)

The four patches were left with no live delta: two were already applied and two were superseded by newer content (1.6.0 > 1.4.0). Their entries were removed from manifest — a `not_applicable` entry compares hash against live prose and that breaks any synthetic fixture, including `verify-wheel-restock.ps1` —, and their reason was recorded in table above. The `.patch` files remain in `patches/` as record.

Before declaring a patch dead, the opposite of the obvious was verified: that target skill did not contain a fix contradicting it. In `dayz-proxy-align` the check returned positive signal — 1.4.0 content remains there, named as historical —, so absence was deliberate, not a loss.

## Preflight and application

Both root parameters are mandatory. `-BackupRoot` must remain outside `-TargetSkillRoot`; both an identical path and one contained in destination are rejected.

Test permitted in this phase, only against a temporary snapshot copy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\apply-s2-rollout.ps1 `
  -TargetSkillRoot <temporary-snapshot-copy> `
  -BackupRoot <external-temporary-backup-root> `
  -NoWrite
```

A write execution uses the same parameters without `-NoWrite`, but requires explicit user authorization and an approved root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\apply-s2-rollout.ps1 `
  -TargetSkillRoot <authorized-skill-root> `
  -BackupRoot <external-backup-root>
```

For each textual target, preflight produces one of these decisions:

- `[PLAN] patch`: exact preimage hash and green `git apply --check`.
- `[OK] already applied`: green `git apply --reverse --check`; nothing is written.
- `[OK] not applicable`: exact live hash and no writes planned.
- `[FAIL] preimage mismatch`: includes path, expected and observed SHA-256; entire operation aborts.

Any preflight failure prevents creating backups or modifying targets. Before the first change, all files to be patched are copied to the external backup and reread by SHA-256. After that I/O, the preimage check is repeated to close the concurrent change window.
## Wheel vendorizado

The mechanism remains a vendored copy in `wheels/` across consuming skills. `$WheelSkillNames` is the CANDIDATE set (seven); a skill is restocked only where its `wheels/` directory ALREADY exists, and the applicator prints `[SKIP] not vendored: <skill>` where it does not. The script restocks, never deciding that a skill should start vendoring: as of 2026-09-02 four vendor (`dayz-3d-viewer`, `dayz-animation-pipeline`, `dayz-p3d-inspector`, `dayz-proxy-align`) and the other three declare `pip install -e tools/py3d` in their own dependency block. The applicator hardens three properties:

1. wheel backups reside under `-BackupRoot`, outside skills;
2. each copy with pinned name must match `wheel-manifest.json` SHA-256, or it aborts without overwriting it;
3. no obsolete wheel is deleted until its backup exists and its hash has been verified. Obsolete means a `py3d-*.whl`, or a `py3d_dayz-*.whl` other than the pinned one: the skills' `install_py3d.py` refuses a `wheels/` directory with more than one `py3d_dayz-*-py3-none-any.whl`. Up to the 1.9.0 pin an earlier `py3d_dayz` wheel was left in place and the readback still passed (test E of `verify-wheel-restock.ps1` and `test_earlier_py3d_dayz_wheel_next_to_the_pinned_one_is_replaced` fail on that applicator).

If installing or replacing a wheel is needed, `../dist/<pinned filename>` is also required to exist and match the manifest hash. There is no fallback to `pip`, venv, or centralized installation.

### Identity gate

`tools/py3d/dist/` is gitignored: the pinned wheel lives on the machine that built it, and `wheel-manifest.json` is its tracked identity. Current pin: `py3d_dayz-1.10.1-py3-none-any.whl` (`c9f000a5...`), sealed on 2026-10-03 at the owner's explicit request ("seal 1.10.1 and port it to the fork") from the source on main at `ea7b396`, where `tools/py3d` is as #78 left it (`9c89864`). Since the 1.9.0 pin, that source adds `ERR_COMPONENT_COVERAGE` (#72, 1.10.0) and the winding messages' part-by-part normals step (#78, 1.10.1); the CHANGELOG has the details. Before resealing, the same script rebuilt the 1.9.0 pin (`33d8b5ba...`) byte for byte from the commit that sealed it (`4626f4b`), so the toolchain (Python 3.14.3, setuptools 83.0.0) is the one that sealed it; then `-UpdateManifest` built 1.10.1 twice to the same hash, and check runs without it, one before and one after, built it four more times to that hash. The wheel's `py3d/` files and `LICENSE` are byte-identical to the source; its long description is `README.md` with CRLF line endings, as setuptools writes METADATA on Windows. `verify-wheel-restock.ps1` passed against it (tests A-C and E on synthetic skill roots; the negative control D needs `-BaselineScript` and did not run). Nothing was restocked: checked the same day, no installed skill tree vendors a `wheels/` directory. The applicator, dry-run (`-WheelOnly -NoWrite`) on temporary copies of every skill root on the build machine that holds a candidate skill, planned 46 replacements, all in trees this rollout does not manage (the desktop app's own plugin copies, at 1.2.0 and 1.4.0, and the skill copies another local agent imported, at 1.7.0), and wrote nothing. The user site-packages install follows the merge, at the owner's request. The previous pin, 1.9.0 (`33d8b5ba...`), was sealed on 2026-10-02 from the source on main at `62c3dcc` (#37, #40, #46 and #54 since the 1.8.0 pin), after rebuilding the 1.8.0 pin (`e7184429...`) byte for byte; its wheel stays on the build machine as the rollback. The pin before it, 1.8.0 (`e7184429...`), was sealed on 2026-10-01 for the Blender -> DayZ change and resealed on 2026-10-02 after a docstring fix, after rebuilding the 1.7.0 pin (`96bb546b...`) byte for byte.

Do not run `-UpdateManifest` or edit `wheel-manifest.json` to bypass a mismatch. Resealing identity is an explicit user decision. If source wheel is missing or hash does not match, applicator aborts without overwriting any vendored copy.

What the 1.10.1 seal did NOT check: that another machine reproduces the hash, or a restock of an installed tree (none vendors the wheel; the trees the dry-run planned are not managed here and were not written). The 1.9.0 seal did not check those either. The 1.8.0 reseals were not checked on another machine either, and their applicator was only dry-run (`-WheelOnly -NoWrite`) against a temporary root holding one skill that vendors 1.7.0: it planned that one replacement and wrote nothing.

## Maintenance checks

From the repository root:

```powershell
python -m pytest -q
python -m pytest -q tests\py3d_rollout\test_apply_rollout.py
python -m packctl validate --root . --report .\reports\validate-sesion2.json
```

To inspect the reproducible gate without resealing:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File tools\py3d\rollout\build-wheel.ps1 `
  -Python <python-3.10-or-newer>
```

Expected failure must display `expected=<pinned sha256>` and `actual=<reproducible sha256>`, leave `dist/` empty, and not modify the manifest.

## Restricciones operativas

- Never run this package against a live root without explicit authorization.
- Never use the snapshot as target; always copy it to temporary location.
- Never locate backup inside skills root.
- Preimage or wheel drift is a blocker, not an invitation to overwrite.
- `packctl` and any installation redesign remain outside this rollout.
