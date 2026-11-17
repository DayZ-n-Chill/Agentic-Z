# dayz-odol-strict

A strict, read-only adapter for inspecting ODOL v53, v54 and v55 anatomy.
It validates the container and complete parse around an external parser
backend and emits deterministic JSON suitable for parity checks.

This package does not write ODOL, convert ODOL to MLOD or accept partial
recovery as success.

## Why the backend is external

The compatible local backend is derived from `ScripyZz/BisDLL-Arma-3`, whose
pinned source revision does not publish a license or redistribution grant.
The MIT pack therefore contains no backend source. It contains only:

- this independently authored strict adapter;
- `backend/manifest-v1.json`, which pins the required external file closure;
- three user-authorized first-party binary fixtures.

The adapter verifies the manifest and every backend file by SHA-256 in the
parent process, launches an isolated subprocess, and verifies the same
identity again before the subprocess imports `odol_reader`.

## Install

```powershell
python -m pip install -e tools/dayz-odol-strict
```

Python 3.9 or newer is required. Before inspection, supply a local backend root
whose files exactly match `backend/manifest-v1.json`. The pinned manifest hash
is:

`485852927678f79d9d7660ae194db0096bb5ba70faf90ca8aea00559903bd09a`

## Inspect

```powershell
$env:DAYZ_ODOL_BACKEND_ROOT = 'D:\external\odol-backend\scripts'
python -m dayz_odol_strict inspect model.p3d
python -m dayz_odol_strict inspect model.p3d --json anatomy.json
```

The explicit `--backend-root ROOT` option overrides the environment variable.
`--backend-manifest FILE` may select a manifest path, but its bytes must still
match the adapter's pinned manifest identity.

Success returns exit `0` and a `dayz-odol-strict-v1` document containing input
and sliced-payload hashes, container offset, version, declared resolutions,
backend identity and per-LOD boundaries/hashes/anatomy counts. A strict error
returns exit `2` with stable `code`, `message` and optional byte `offset`.

## Diff

```powershell
python -m dayz_odol_strict diff reference.json candidate.json
python -m dayz_odol_strict diff reference.json candidate.json --json diff.json
```

Diff validates both summaries and compares every anatomy field recursively.
Findings use deterministic JSON-pointer-like paths.

| Exit | Meaning |
|---:|---|
| `0` | Summaries are equal. |
| `1` | Both summaries are valid and differ. |
| `2` | A summary or command input is invalid. |

## Strict boundary

- Accepted direct or embedded payload versions: v53, v54 and v55 only.
  The 1.30 vanilla models and the models binarized by DayZ Tools
  1.30.164.078 (2026-10-15) are v56, so the adapter refuses them with
  `ODOL_VERSION_UNSUPPORTED`. In one harness run on 2026-11-12, DayZ Tools
  1.30 (`BINARIZE 1.30.164289.70`) wrote v56 into three test `.p3d` files; no
  other DayZ Tools build was measured in that run.
- LOD count must be `1..64` before the external backend runs.
- A local census of 13,108 direct-signature v53-v55 files observed at most 15
  LODs; 64 is a conservative hostile-count guard, not a claim about the format
  maximum.
- More than one plausible supported embedded signature is ambiguous.
- Every declared interval must satisfy
  `0 <= declared_start < declared_end <= payload_size`.
- Actual and declared LOD ends must match exactly.
- LOD intervals must not overlap.
- Header fields, resolution count/order, anatomy fields and LOD count must
  agree between preflight and backend.
- Any backend `lod_errors`, missing LOD, incomplete field or partial result is
  a hard failure.

Recovery remains an explicit external workflow. A recovered or partially
converted model must not be represented as a strict inspection pass.

## Stable error codes

| Code | Meaning |
|---|---|
| `ODOL_SIGNATURE_MISSING` | No readable/plausible supported ODOL payload. |
| `ODOL_SIGNATURE_AMBIGUOUS` | Multiple plausible embedded payloads. |
| `ODOL_VERSION_UNSUPPORTED` | A direct ODOL header is not v53-v55. |
| `ODOL_HEADER_TRUNCATED` | Header or resolution table is incomplete. |
| `ODOL_LOD_COUNT_INVALID` | Signed LOD count is outside `1..64`. |
| `ODOL_BACKEND_MISSING` | Explicit root, manifest or pinned file is unavailable. |
| `ODOL_BACKEND_DRIFT` | Manifest identity, shape, path or file hash changed. |
| `ODOL_BACKEND_FAILURE` | Isolated worker did not return valid complete JSON. |
| `ODOL_PARTIAL_RESULT` | Backend/header/LOD anatomy is incomplete or inconsistent. |
| `ODOL_BOUNDARY_OOB` | A declared interval escapes the sliced payload. |
| `ODOL_BOUNDARY_INEXACT` | Actual LOD end differs from its declaration. |
| `ODOL_BOUNDARY_OVERLAP` | Declared LOD intervals overlap. |
| `ODOL_SUMMARY_INVALID` | A diff input is not a complete valid strict summary. |
| `ODOL_OUTPUT_UNWRITABLE` | Requested JSON output cannot be written atomically. |

## Authorized fixtures

| Fixture | Version / LODs | Size | SHA-256 |
|---|---:|---:|---|
| `odol-v53-ammo-box.p3d` | v53 / 1 | 462 | `c2ba93cc05d3d47df5400c6f5f68aef928687eef06ce38747340927cd39e96ba` |
| `odol-v54-rugermarkiv-optic.p3d` | v54 / 1 | 562 | `ccdb62e78661f2a0d98e5d5ca8844a8a7f0ae5242c2e1f403530d01d0ef037f9` |
| `odol-v55-lfquad-body.p3d` | v55 / 5 | 1,441,109 | `9dd2b16a70001b5e6513bf26da0b24db6c2a92c09f6fa09ae9aab20f77ef19d3` |

The user confirmed that all three are first-party assets authorized for public
redistribution. They contain no backend source.

## Test

Tests that do not need the external backend always run. Real fixture
integration is enabled only when `DAYZ_ODOL_BACKEND_ROOT` points to the exact
pinned closure.

```powershell
python -m pytest -q tools/dayz-odol-strict/tests

$env:DAYZ_ODOL_BACKEND_ROOT = 'D:\external\odol-backend\scripts'
python -m pytest -q tools/dayz-odol-strict/tests
```
